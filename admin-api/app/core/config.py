import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings."""

    # API configuration
    api_v1_prefix: str = "/api/v1"

    # CORS configuration
    cors_origins: str = "*"

    # MongoDB configuration
    mongo_uri: str = os.getenv("MONGO_URI", "")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "spreadpilot_admin")

    # Authentication configuration
    admin_username: str = os.getenv("ADMIN_USERNAME", "")
    admin_password_hash: str = os.getenv("ADMIN_PASSWORD_HASH", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours

    # WebSocket configuration
    websocket_ping_interval: int = 30  # seconds

    # Background task configuration
    follower_update_interval: int = 60  # seconds
    
    # PostgreSQL configuration for P&L data
    postgres_uri: str = os.getenv("POSTGRES_URI", "")
    
    # Manual operation PIN
    manual_operation_pin: str = os.getenv("MANUAL_OPERATION_PIN", "0312")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the settings.
    This avoids re-reading the environment variables on each call.
    """
    return Settings()
