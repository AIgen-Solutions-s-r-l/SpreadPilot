from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # GCP Project ID
    # Default is 'spreadpilot', override with GCP_PROJECT_ID env var
    gcp_project_id: str = "spreadpilot"

    # Trading Bot Service URL
    # Needs to be set via environment variable, e.g., http://trading-bot:8000
    # Defaulting to a placeholder to avoid startup errors if not set.
    trading_bot_base_url: str = "http://localhost:8000" # Placeholder, MUST be set in deployment

    # Firestore Emulator Host (Optional)
    # If set, the Firestore client will connect to the emulator
    firestore_emulator_host: Optional[str] = None

    # MongoDB Settings
    # Read from MONGO_URI and MONGO_DB_NAME env vars
    mongo_uri: str = "mongodb://mongodb:27017" # Default for Docker service
    mongo_db_name: str = "spreadpilot_admin"   # Default database name

    # API V1 Prefix
    api_v1_prefix: str = "/api/v1"

    # CORS Origins (comma-separated string or list)
    # Example: "http://localhost:3000,http://localhost:3001"
    cors_origins: str = "*" # Default to allow all for development

    # Define model_config to load from .env file if present
    model_config = SettingsConfigDict(
        env_file=".env",          # Load .env file if it exists
        env_file_encoding='utf-8',
        extra='ignore'            # Ignore extra fields from env vars/file
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns the application settings instance.

    Uses LRU cache to ensure settings are loaded only once.
    """
    return Settings()

# Example usage (optional)
if __name__ == "__main__":
    settings = get_settings()
    print("Loaded Settings:")
    print(f"  GCP Project ID: {settings.gcp_project_id}")
    print(f"  Trading Bot URL: {settings.trading_bot_base_url}")
    print(f"  Firestore Emulator: {settings.firestore_emulator_host}")
    print(f"  Mongo URI: {settings.mongo_uri}")
    print(f"  Mongo DB Name: {settings.mongo_db_name}")
    print(f"  CORS Origins: {settings.cors_origins}")