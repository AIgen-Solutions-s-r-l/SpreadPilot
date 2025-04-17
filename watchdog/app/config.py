# watchdog/app/config.py
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Settings(BaseSettings):
    """Watchdog service configuration settings."""

    # General
    PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "spreadpilot")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Watchdog specific
    CHECK_INTERVAL_SECONDS: int = 30
    HEARTBEAT_TIMEOUT_SECONDS: int = 75
    MAX_RESTART_ATTEMPTS: int = 3
    RESTART_BACKOFF_SECONDS: int = 120

    # Target components (adjust names/paths as needed)
    TRADING_BOT_NAME: str = "trading-bot"
    IB_GATEWAY_NAME: str = "ib-gateway"
    # TODO: Define how to check/restart these (e.g., API endpoint, Cloud Run service name)
    TRADING_BOT_HEALTH_ENDPOINT: str | None = os.getenv("TRADING_BOT_HEALTH_ENDPOINT")
    IB_GATEWAY_HEALTH_ENDPOINT: str | None = os.getenv("IB_GATEWAY_HEALTH_ENDPOINT")
    # TODO: Define restart mechanisms (e.g., Cloud Run API calls, kubectl commands)

    # Firestore
    FIRESTORE_STATUS_COLLECTION: str = "service_status"

    # Alerting (using spreadpilot-core)
    ALERT_SERVICE_NAME: str = "watchdog"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()