"""SpreadPilot Trading Bot.

This is the main entry point for the trading bot service, which:
1. Connects to IBKR
2. Polls Google Sheets for signals
3. Executes orders
4. Monitors positions for assignments
5. Calculates P&L
"""

import asyncio
import logging  # Import logging for preload logger
import os
import signal
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient  # Import motor
from pydantic import BaseModel
from spreadpilot_core.dry_run import DryRunConfig
from spreadpilot_core.logging import get_logger, setup_logging
from spreadpilot_core.utils.secrets import get_secret_from_mongo  # Import secret getter

from .config import Settings, get_settings
from .service import TradingService

# --- Secret Pre-loading ---

# Initialize logger early for pre-loading
preload_logger = logging.getLogger(__name__ + ".preload")

# Define secrets needed by this specific service
SECRETS_TO_FETCH = [
    "TELEGRAM_BOT_TOKEN",
    "SENDGRID_API_KEY",
    "ADMIN_EMAIL",
    # Add IBKR credentials if they were ever planned to be stored here
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

    client: AsyncIOMotorClient | None = None
    try:
        preload_logger.info(f"Connecting to MongoDB at {mongo_uri} for secret loading...")
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
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


# --- Regular Application Setup ---

# Initialize logger (will be properly configured in startup_event)
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SpreadPilot Trading Bot",
    description="Trading bot for SpreadPilot platform",
    version="1.1.7.0",
)

# Add CORS middleware
# Load CORS origins from environment variable or use secure defaults
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    # Default to localhost for development only
    # In production, MUST set CORS_ORIGINS environment variable
    cors_origins = ["http://localhost:3000", "http://localhost:8080"]
    logger.warning(
        "CORS_ORIGINS not set - using development defaults. "
        "Set CORS_ORIGINS environment variable in production!"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
settings: Settings | None = None
trading_service: TradingService | None = None
shutdown_event: asyncio.Event | None = None


class TradeSignal(BaseModel):
    """Trade signal model."""

    strategy: str
    qty_per_leg: int
    strike_long: float
    strike_short: float
    follower_id: str | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global settings, trading_service, sheets_client, shutdown_event

    # --- Load Secrets FIRST ---
    # Skips if TESTING env var is set
    if not os.getenv("TESTING"):
        try:
            await load_secrets_into_env()
        except Exception as e:
            # Log error but allow startup to continue if possible
            preload_logger.error(
                f"Error during async secret loading in startup: {e}", exc_info=True
            )
    else:
        preload_logger.info(
            "TESTING environment detected, skipping MongoDB secret pre-loading in startup."
        )

    # --- Proceed with regular startup ---

    # Set up logging (Now uses the final logger instance)
    setup_logging(
        service_name="trading-bot",
        enable_gcp=True,  # Consider if GCP logging still needed
        enable_otlp=True,  # Consider if OTLP logging still needed
    )
    # Re-get logger instance after setup_logging might have reconfigured handlers
    logger = get_logger(__name__)

    # Load settings (AFTER environment variables are potentially populated)
    settings = get_settings()

    # Enable dry-run mode if configured
    if settings.dry_run_mode:
        DryRunConfig.enable()
        logger.warning("🔵 DRY-RUN MODE ENABLED - Operations will be simulated")

    # Create shutdown event
    shutdown_event = asyncio.Event()

    # Initialize trading service
    # Note: Signal generator will be initialized in the service after IBKR connection
    trading_service = TradingService(
        settings=settings,
    )

    # Start background tasks
    asyncio.create_task(trading_service.run(shutdown_event))

    logger.info("Trading bot started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down trading bot")

    # Signal shutdown to background tasks
    if shutdown_event:
        shutdown_event.set()

    # Wait for background tasks to complete
    if trading_service:
        await trading_service.shutdown()

    logger.info("Trading bot shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not trading_service or not trading_service.is_healthy():
        raise HTTPException(status_code=503, detail="Trading bot is not healthy")

    return {"status": "healthy"}


@app.get("/status")
async def get_status():
    """Get trading bot status."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")

    return {
        "status": trading_service.get_status(),
        "ibkr_connected": trading_service.is_ibkr_connected(),
        "signal_generator_enabled": trading_service.is_signal_generator_enabled(),
        "active_followers": trading_service.get_active_follower_count(),
    }


@app.post("/trade/signal")
async def process_trade_signal(signal: TradeSignal):
    """Process a trade signal manually."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")

    logger.info(
        "Received manual trade signal",
        strategy=signal.strategy,
        qty_per_leg=signal.qty_per_leg,
        strike_long=signal.strike_long,
        strike_short=signal.strike_short,
        follower_id=signal.follower_id,
    )

    # Process signal
    result = await trading_service.signal_processor.process_signal(
        strategy=signal.strategy,
        qty_per_leg=signal.qty_per_leg,
        strike_long=signal.strike_long,
        strike_short=signal.strike_short,
        follower_id=signal.follower_id,
    )

    return result


@app.post("/close/{follower_id}")
async def close_positions(follower_id: str):
    """Close all positions for a follower."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")

    logger.info("Closing positions for follower", follower_id=follower_id)

    # Close positions
    result = await trading_service.close_positions(follower_id)

    return result


@app.post("/close/all")
async def close_all_positions():
    """Close all positions for all followers."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading bot is not initialized")

    logger.info("Closing all positions for all followers")

    # Close all positions
    result = await trading_service.close_all_positions()

    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def handle_sigterm(signum, frame):
    """Handle SIGTERM signal."""
    logger.info("Received SIGTERM")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)

    # Run the application
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=os.environ.get("ENV", "production") == "development",
    )
