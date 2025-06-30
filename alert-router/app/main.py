import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

# Import from spreadpilot_core
try:
    from spreadpilot_core.logging.logger import get_logger, setup_logging
    from spreadpilot_core.models.alert import AlertEvent
    from spreadpilot_core.utils.secrets import get_secret_from_mongo
except ImportError:
    logging.error("Could not import from spreadpilot_core. Ensure it's installed.")
    # Define dummy classes/functions if needed for basic startup
    AlertEvent = None

    def setup_logging(*args, **kwargs):
        pass

    def get_logger(*args, **kwargs):
        return logging.getLogger(*args)

    async def get_secret_from_mongo(*args, **kwargs):
        return None


# Initialize logger early for pre-loading
preload_logger = logging.getLogger(__name__ + ".preload")

# Define secrets needed by this specific service
SECRETS_TO_FETCH = [
    "TELEGRAM_BOT_TOKEN",
    "SMTP_USER",
    "SMTP_PASSWORD",
]


async def load_secrets_into_env():
    """Fetches secrets from MongoDB and sets them as environment variables."""
    preload_logger.info("Attempting to load secrets from MongoDB into environment variables...")
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get(
        "MONGO_DB_NAME_SECRETS", os.environ.get("MONGO_DB_NAME", "spreadpilot_secrets")
    )

    if not mongo_uri:
        preload_logger.warning(
            "MONGO_URI environment variable not set. Skipping MongoDB secret loading."
        )
        return

    client = None
    try:
        preload_logger.info(f"Connecting to MongoDB at {mongo_uri} for secret loading...")
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Ping server to check connection early
        await client.admin.command("ping")
        db = client[mongo_db_name]
        preload_logger.info(f"Connected to MongoDB database '{mongo_db_name}'.")

        app_env = os.environ.get("APP_ENV", "development")

        for secret_name in SECRETS_TO_FETCH:
            preload_logger.debug(f"Fetching secret: {secret_name} for env: {app_env}")
            secret_value = await get_secret_from_mongo(db, secret_name, environment=app_env)
            if secret_value is not None:
                os.environ[secret_name] = secret_value
                preload_logger.info(f"Successfully loaded secret '{secret_name}' into environment.")
            else:
                preload_logger.info(
                    f"Secret '{secret_name}' not found in MongoDB for env '{app_env}'. Environment variable not set."
                )

        preload_logger.info("Finished loading secrets into environment.")

    except Exception as e:
        preload_logger.error(
            f"Failed to load secrets from MongoDB into environment: {e}", exc_info=True
        )
    finally:
        if client:
            client.close()
            preload_logger.info("MongoDB connection for secret loading closed.")


# Run secret loading BEFORE initializing settings
# Skips if TESTING env var is set
if __name__ != "__main__" and not os.getenv("TESTING"):
    try:
        asyncio.run(load_secrets_into_env())
    except RuntimeError as e:
        preload_logger.error(f"Could not run async secret loading: {e}")
elif os.getenv("TESTING"):
    preload_logger.info("TESTING environment detected, skipping MongoDB secret pre-loading.")

# Import settings and router after potential env var population
from .config import settings
from .service.redis_subscriber import RedisAlertSubscriber

# Setup Logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
setup_logging(service_name="alert-router", log_level=getattr(logging, log_level, logging.INFO))
logger = get_logger(__name__)

# Global subscriber instance
redis_subscriber = None
subscriber_task = None


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_subscriber, subscriber_task

    logger.info("Alert Router service starting...")

    # Start Redis subscriber
    redis_subscriber = RedisAlertSubscriber()
    subscriber_task = asyncio.create_task(redis_subscriber.run())
    logger.info("Started Redis alert subscriber")

    yield  # Application runs here

    # Application shutdown
    logger.info("Alert Router service shutting down...")

    # Stop Redis subscriber
    if redis_subscriber:
        await redis_subscriber.stop()
    if subscriber_task:
        try:
            await asyncio.wait_for(subscriber_task, timeout=5.0)
        except TimeoutError:
            logger.warning("Redis subscriber task did not complete within timeout")
            subscriber_task.cancel()
        except Exception as e:
            logger.error(f"Error stopping Redis subscriber: {e}")

    logger.info("Alert Router service shutdown complete")


app = FastAPI(
    title="SpreadPilot Alert Router",
    description="Service for routing alerts to various notification channels",
    version="1.0.0",
    lifespan=lifespan,
)

logger.info(f"Dashboard URL: {settings.DASHBOARD_BASE_URL}")
logger.info(f"Telegram Admins: {'Configured' if settings.TELEGRAM_ADMIN_IDS else 'Not Configured'}")
logger.info(
    f"Email Admins: {'Configured' if settings.EMAIL_ADMIN_RECIPIENTS else 'Not Configured'}"
)
logger.info(
    f"Redis URL: {settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else 'Using default'}"
)


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy"}


# For local development
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
