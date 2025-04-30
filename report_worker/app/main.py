import base64
import json
import os
import datetime
import pytz # For timezone handling
import asyncio # Import asyncio
import logging # Import logging for preload logger
from motor.motor_asyncio import AsyncIOMotorClient # Import motor

from flask import Flask, request, Response
# Import logger and secret getter from core library
from spreadpilot_core.logging.logger import get_logger, setup_cloud_logging
from spreadpilot_core.utils.secrets import get_secret_from_mongo


# --- Secret Pre-loading ---

# Initialize logger early for pre-loading
preload_logger = logging.getLogger(__name__ + ".preload")

# Define secrets needed by this specific service
SECRETS_TO_FETCH = [
    "REPORT_SENDER_EMAIL",
    "ADMIN_EMAIL",
    # Add SMTP credentials here if needed in the future
]

async def load_secrets_into_env():
    """Fetches secrets from MongoDB and sets them as environment variables."""
    preload_logger.info("Attempting to load secrets from MongoDB into environment variables...")
    mongo_uri = os.environ.get("MONGO_URI")
    mongo_db_name = os.environ.get("MONGO_DB_NAME_SECRETS", os.environ.get("MONGO_DB_NAME", "spreadpilot_secrets"))

    if not mongo_uri:
        preload_logger.warning("MONGO_URI environment variable not set. Skipping MongoDB secret loading.")
        return

    client: AsyncIOMotorClient | None = None
    try:
        preload_logger.info(f"Connecting to MongoDB at {mongo_uri} for secret loading...")
        client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')
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
                preload_logger.info(f"Secret '{secret_name}' not found in MongoDB for env '{app_env}'. Environment variable not set.")

        preload_logger.info("Finished loading secrets into environment.")

    except Exception as e:
        preload_logger.error(f"Failed to load secrets from MongoDB into environment: {e}", exc_info=True)
    finally:
        if client:
            client.close()
            preload_logger.info("MongoDB connection for secret loading closed.")


# Run secret loading BEFORE importing the config module
# Skips if TESTING env var is set
if __name__ != "__main__" and not os.getenv("TESTING"):
    try:
        asyncio.run(load_secrets_into_env())
    except RuntimeError as e:
        preload_logger.error(f"Could not run async secret loading: {e}")
elif os.getenv("TESTING"):
     preload_logger.info("TESTING environment detected, skipping MongoDB secret pre-loading.")


# --- Regular Application Setup ---

from .service.report_service import ReportService
from . import config # Config module imported AFTER env vars are potentially populated

# --- Initialization --- (Original initialization resumes)
logger = get_logger(__name__) # Get the properly configured logger

# Setup Cloud Logging integration if running in GCP
if config.GCP_PROJECT_ID:
    try:
        setup_cloud_logging()
        logger.info("Cloud Logging handler added.")
    except Exception as e:
        logger.warning(f"Failed to setup Cloud Logging: {e}", exc_info=True)


app = Flask(__name__)
report_service = ReportService()

# --- Utility ---

def get_current_date_in_timezone(tz_name: str) -> datetime.date:
    """Gets the current date in the specified timezone."""
    try:
        timezone = pytz.timezone(tz_name)
        now_utc = datetime.datetime.now(pytz.utc)
        now_local = now_utc.astimezone(timezone)
        return now_local.date()
    except pytz.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone '{tz_name}'. Falling back to UTC date.")
        return datetime.datetime.now(pytz.utc).date()
    except Exception as e:
        logger.exception(f"Error getting current date in timezone {tz_name}", exc_info=e)
        # Fallback to UTC date on other errors
        return datetime.datetime.now(pytz.utc).date()


# --- Flask Routes ---

@app.route("/", methods=["POST"])
def handle_pubsub():
    """
    Handles incoming Pub/Sub push requests.
    Parses the message to determine the job type (daily P&L or monthly report)
    and triggers the corresponding service method.
    """
    envelope = request.get_json()
    if not envelope:
        msg = "No Pub/Sub message received"
        logger.error(f"Endpoint received non-JSON request: {msg}")
        return Response(msg, status=400)

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "Invalid Pub/Sub message format"
        logger.error(f"Endpoint received invalid Pub/Sub message: {envelope}")
        return Response(msg, status=400)

    pubsub_message = envelope["message"]
    message_data = {}
    job_type = "monthly" # Default to monthly report generation

    if isinstance(pubsub_message, dict) and "data" in pubsub_message:
        try:
            # Decode the base64-encoded data
            data_str = base64.b64decode(pubsub_message["data"]).decode("utf-8").strip()
            if data_str: # Check if data is not empty
                 message_data = json.loads(data_str)
                 job_type = message_data.get("job_type", "monthly").lower()
                 logger.info(f"Received Pub/Sub message data: {message_data}")
            else:
                logger.info("Received Pub/Sub message with empty data field. Assuming default job type.")

        except json.JSONDecodeError:
            logger.warning("Pub/Sub message data is not valid JSON. Assuming default job type.")
        except Exception as e:
            logger.exception("Error decoding/parsing Pub/Sub message data.", exc_info=e)
            # Proceed with default job type, but log the error

    logger.info(f"Processing job type: {job_type}")

    # Determine the relevant date based on the job type
    # For daily P&L, we use the date the job is triggered (market close day)
    # For monthly reports, we also use the trigger date to determine the *previous* month
    # Using NY timezone as reference for market close day determination
    trigger_date = get_current_date_in_timezone(config.MARKET_CLOSE_TIMEZONE)
    logger.info(f"Determined trigger date (in {config.MARKET_CLOSE_TIMEZONE}): {trigger_date.isoformat()}")


    try:
        if job_type == "daily":
            # Trigger daily P&L calculation for the determined date
            report_service.process_daily_pnl_calculation(calculation_date=trigger_date)
        elif job_type == "monthly":
            # Trigger monthly report generation (for the month *before* trigger_date)
            report_service.process_monthly_reports(trigger_date=trigger_date)
        else:
            logger.warning(f"Unknown job_type '{job_type}' received. No action taken.")
            # Return success to Pub/Sub so it doesn't retry
            return Response(f"Unknown job_type: {job_type}", status=200)

        # Acknowledge successful processing to Pub/Sub
        return Response(status=204) # 204 No Content is typical for successful processing

    except Exception as e:
        logger.exception(f"Error processing Pub/Sub message for job type '{job_type}'", exc_info=e)
        # Return an error status code to signal failure to Pub/Sub
        return Response("Internal Server Error", status=500)


# --- Main Execution ---

if __name__ == "__main__":
    # Get port from environment variable for Cloud Run compatibility
    port = int(os.environ.get("PORT", 8080))
    # Run the Flask app
    # Use host='0.0.0.0' to make it accessible externally (required for Cloud Run)
    logger.info(f"Starting Flask development server on port {port}...")
    app.run(debug=False, host="0.0.0.0", port=port) # Turn debug off for production-like env