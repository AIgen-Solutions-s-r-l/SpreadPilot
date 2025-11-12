import os
from functools import lru_cache

from pydantic import BaseModel

from spreadpilot_core.utils.secret_manager import SecretType, get_secret_manager


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

    # Redis configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Dry-run mode
    dry_run_mode: bool = os.getenv("DRY_RUN_MODE", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached instance of the settings.
    This avoids re-reading the environment variables on each call.
    Uses the secret manager for sensitive values with fallback to env vars.
    """
    secret_manager = get_secret_manager()

    # Get secrets with fallback to environment variables
    mongo_uri = secret_manager.get_secret(SecretType.MONGO_URI) or os.getenv("MONGO_URI", "")
    admin_username = secret_manager.get_secret(SecretType.ADMIN_USERNAME) or os.getenv(
        "ADMIN_USERNAME", ""
    )
    admin_password_hash = secret_manager.get_secret(SecretType.ADMIN_PASSWORD_HASH) or os.getenv(
        "ADMIN_PASSWORD_HASH", ""
    )
    jwt_secret = secret_manager.get_secret(SecretType.JWT_SECRET) or os.getenv("JWT_SECRET", "")

    return Settings(
        mongo_uri=mongo_uri,
        admin_username=admin_username,
        admin_password_hash=admin_password_hash,
        jwt_secret=jwt_secret,
    )
