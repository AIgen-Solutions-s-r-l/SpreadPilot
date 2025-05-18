import os
import logging
from dotenv import load_dotenv
from spreadpilot_core.logging.logger import get_logger

# Load environment variables from .env file if it exists (useful for local dev)
load_dotenv()

# Initialize logger early
logger = get_logger(__name__)

# --- Core Settings ---
GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID")
if not GCP_PROJECT_ID:
    logger.warning("GCP_PROJECT_ID environment variable not set.")

# MongoDB Settings
MONGO_URI: str = os.environ.get("MONGO_URI")
MONGO_DB_NAME: str = os.environ.get("MONGO_DB_NAME", "spreadpilot_admin")
MONGO_DB_NAME_SECRETS: str = os.environ.get("MONGO_DB_NAME_SECRETS", "spreadpilot_secrets")

# --- Report Settings ---
DEFAULT_COMMISSION_PERCENTAGE: float = float(os.environ.get("DEFAULT_COMMISSION_PERCENTAGE", "20.0"))  # Default to 20%
REPORT_SENDER_EMAIL: str = os.environ.get("REPORT_SENDER_EMAIL", "capital@tradeautomation.it")
ADMIN_EMAIL: str = os.environ.get("ADMIN_EMAIL")  # Admin email for CC
if not ADMIN_EMAIL:
    logger.warning("ADMIN_EMAIL environment variable not set. Reports will not be CC'd.")

# --- Timing Settings (for daily P&L calculation trigger reference) ---
# Although triggered by Cloud Scheduler, these might be useful for date calculations
MARKET_CLOSE_TIMEZONE: str = os.environ.get("MARKET_CLOSE_TIMEZONE", "America/New_York")
MARKET_CLOSE_HOUR: int = int(os.environ.get("MARKET_CLOSE_HOUR", "16"))
MARKET_CLOSE_MINUTE: int = int(os.environ.get("MARKET_CLOSE_MINUTE", "10"))

# --- Email Settings ---
SMTP_HOST: str = os.environ.get("SMTP_HOST")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER: str = os.environ.get("SMTP_USER")
SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD")
SMTP_TLS: bool = os.environ.get("SMTP_TLS", "true").lower() == "true"

# Log loaded configuration (optional, consider redacting sensitive info if any)
logger.info("Configuration loaded:")
logger.info(f"  GCP_PROJECT_ID: {GCP_PROJECT_ID}")
logger.info(f"  MONGO_URI: {'Set' if MONGO_URI else 'Not Set'}")
logger.info(f"  MONGO_DB_NAME: {MONGO_DB_NAME}")
logger.info(f"  DEFAULT_COMMISSION_PERCENTAGE: {DEFAULT_COMMISSION_PERCENTAGE}")
logger.info(f"  REPORT_SENDER_EMAIL: {REPORT_SENDER_EMAIL}")
logger.info(f"  ADMIN_EMAIL: {'Set' if ADMIN_EMAIL else 'Not Set'}")
logger.info(f"  MARKET_CLOSE_TIMEZONE: {MARKET_CLOSE_TIMEZONE}")
logger.info(f"  MARKET_CLOSE_HOUR: {MARKET_CLOSE_HOUR}")
logger.info(f"  MARKET_CLOSE_MINUTE: {MARKET_CLOSE_MINUTE}")
logger.info(f"  SMTP_HOST: {'Set' if SMTP_HOST else 'Not Set'}")