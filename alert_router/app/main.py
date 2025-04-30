import base64
import json
import logging
import os
import uvicorn
import asyncio # Import asyncio
from motor.motor_asyncio import AsyncIOMotorClient # Import motor

from fastapi import FastAPI, Request, HTTPException, status
from pydantic import ValidationError

# Assuming spreadpilot_core is installed or available in the Python path
# Adjust import if necessary based on project structure/installation
try:
    from spreadpilot_core.logging.logger import setup_logging, get_logger # Import get_logger
    from spreadpilot_core.models.alert import AlertEvent
    from spreadpilot_core.utils.secrets import get_secret_from_mongo # Import secret getter
except ImportError:
    # Handle case where core library might not be directly importable
    # This might happen during Docker build if not installed correctly
    logging.error(
        "Could not import from spreadpilot_core. Ensure it's installed."
    )
    # Define dummy classes/functions if needed for basic startup,
    # or raise error
    AlertEvent = None  # Placeholder

    def setup_logging(*args, **kwargs):
        pass


# --- Secret Pre-loading ---

# Initialize logger early for pre-loading
# Note: setup_logging is called later, but we need a logger instance now.
# This might log to stdout initially before file handlers are set up.
preload_logger = logging.getLogger(__name__ + ".preload") # Use a distinct name initially

# Define secrets needed by this specific service
SECRETS_TO_FETCH = [
    "TELEGRAM_BOT_TOKEN",
    "SMTP_USER",
    "SMTP_PASSWORD",
    # Add other secrets like API keys if they become necessary
]

async def load_secrets_into_env():
    """Fetches secrets from MongoDB and sets them as environment variables."""
    preload_logger.info("Attempting to load secrets from MongoDB into environment variables...")
    mongo_uri = os.environ.get("MONGO_URI")
    # Use a dedicated DB name for secrets or reuse admin one if appropriate
    mongo_db_name = os.environ.get("MONGO_DB_NAME_SECRETS", os.environ.get("MONGO_DB_NAME", "spreadpilot_secrets")) # Default to 'spreadpilot_secrets'

    if not mongo_uri:
        preload_logger.warning("MONGO_URI environment variable not set. Skipping MongoDB secret loading.")
        return

    client: AsyncIOMotorClient | None = None
    try:
        preload_logger.info(f"Connecting to MongoDB at {mongo_uri} for secret loading...")
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000) # Add timeout
        # Optionally ping server to check connection early
        await client.admin.command('ping')
        db = client[mongo_db_name]
        preload_logger.info(f"Connected to MongoDB database '{mongo_db_name}'.")

        app_env = os.environ.get("APP_ENV", "development") # Determine environment

        for secret_name in SECRETS_TO_FETCH:
            preload_logger.debug(f"Fetching secret: {secret_name} for env: {app_env}")
            secret_value = await get_secret_from_mongo(db, secret_name, environment=app_env)
            if secret_value is not None:
                os.environ[secret_name] = secret_value
                preload_logger.info(f"Successfully loaded secret '{secret_name}' into environment.")
            else:
                preload_logger.info(f"Secret '{secret_name}' not found in MongoDB for env '{app_env}'. Environment variable not set.")

        preload_logger.info("Finished loading secrets into environment.")

    except Exception as e:
        preload_logger.error(f"Failed to load secrets from MongoDB into environment: {e}", exc_info=True)
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


# --- Regular Application Setup ---

from .config import settings # Settings instance created AFTER env vars are potentially populated
from .service.router import route_alert

# Setup Logging (Now uses the final logger instance)
# Determine log level from environment or default
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
setup_logging(service_name="alert-router", level=log_level)
# Note: setup_logging might reconfigure the root logger. Get the specific logger after setup.
logger = get_logger(__name__) # Use get_logger from core library

app = FastAPI(title="SpreadPilot Alert Router")

logger.info("Alert Router service starting...") # This log now happens AFTER potential secret loading
logger.info(f"GCP Project ID: {settings.GCP_PROJECT_ID}")
logger.info(f"Dashboard URL: {settings.DASHBOARD_BASE_URL}")
logger.info(
    "Telegram Admins: "
    f"{'Configured' if settings.TELEGRAM_ADMIN_IDS else 'Not Configured'}"
)
logger.info(
    "Email Admins: "
    f"{'Configured' if settings.EMAIL_ADMIN_RECIPIENTS else 'Not Configured'}"
)


@app.post("/", status_code=status.HTTP_204_NO_CONTENT)
async def receive_pubsub_message(request: Request):
    """
    Receives Pub/Sub push messages, parses the alert event, and routes it.
    """
    envelope = await request.json()
    logger.debug(f"Received Pub/Sub envelope: {envelope}")

    if not isinstance(envelope, dict) or "message" not in envelope:
        logger.error(f"Invalid Pub/Sub message format received: {envelope}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Pub/Sub message format",
        )

    message = envelope["message"]
    if "data" not in message:
        logger.error(f"Pub/Sub message missing 'data' field: {message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Pub/Sub message format: 'data' field missing",
        )

    try:
        # Decode Base64 data
        data_bytes = base64.b64decode(message["data"])
        data_str = data_bytes.decode("utf-8")
        event_data = json.loads(data_str)
        logger.info(f"Decoded event data: {event_data}")

        # Validate data with Pydantic model
        if AlertEvent is None:
            logger.error(
                "AlertEvent model not loaded. Cannot process message."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Core library model not loaded.",
            )

        alert_event = AlertEvent(**event_data)
        logger.info(f"Parsed AlertEvent: {alert_event.event_type.value}")

    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(
            f"Error decoding Pub/Sub message data: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot decode message data",
        )
    except ValidationError as e:
        logger.error(f"Invalid alert event data format: {e}", exc_info=True)
        logger.error(f"Received data: {event_data}")
        # Don't raise 400 for validation errors, as Pub/Sub will retry.
        # Acknowledge the message (by returning 204) to prevent infinite
        # retries for malformed *valid* JSON. Log the error for investigation.
        logger.error(
            "Acknowledging message despite validation error to prevent "
            "retries."
        )
        return
    except Exception as e:
        logger.error(
            f"Unexpected error processing message: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing message",
        )

    try:
        # Route the validated alert
        await route_alert(alert_event)
        logger.info(
            "Successfully processed and routed alert: "
            f"{alert_event.event_type.value}"
        )
    except Exception as e:
        # Log error but return 2xx to acknowledge Pub/Sub message
        # and prevent retries if routing fails temporarily.
        # Persistent routing issues should be monitored via logs.
        logger.error(
            f"Error routing alert {alert_event.event_type.value}: {e}",
            exc_info=True,
        )
        # Optionally, raise 500 if retries are desired for routing errors
        # raise HTTPException(status_code=500, detail="Failed to route alert")

    # Return 204 No Content to acknowledge successful processing by Pub/Sub
    return


# For local development: uvicorn alert-router.app.main:app --reload --port 8080
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
