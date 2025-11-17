import os
from functools import lru_cache
from typing import List, Tuple

from pydantic import BaseModel
from spreadpilot_core.logging.logger import get_logger
from spreadpilot_core.utils.secret_manager import SecretType, get_secret_manager

logger = get_logger(__name__)


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

    def validate_required_secrets(self) -> Tuple[bool, List[str]]:
        """
        Validate that all required secrets are configured.

        Returns:
            Tuple of (is_valid, list of missing secrets)
        """
        missing_secrets = []

        # Required secrets for Admin API
        if not self.mongo_uri:
            missing_secrets.append("MONGO_URI")

        if not self.admin_username:
            missing_secrets.append("ADMIN_USERNAME")

        if not self.admin_password_hash:
            missing_secrets.append("ADMIN_PASSWORD_HASH")

        if not self.jwt_secret:
            missing_secrets.append("JWT_SECRET")

        # Validate JWT secret strength (minimum 32 characters for HS256)
        if self.jwt_secret and len(self.jwt_secret) < 32:
            missing_secrets.append("JWT_SECRET (too short - minimum 32 characters required)")

        # Validate CORS is not wildcard
        if self.cors_origins == "*":
            missing_secrets.append("CORS_ORIGINS (wildcard not allowed)")

        # Validate Redis URL
        if not self.redis_url or self.redis_url == "redis://localhost:6379":
            # localhost is acceptable for development but log a warning
            if os.getenv("ENV") == "production":
                missing_secrets.append("REDIS_URL (localhost not allowed in production)")

        return (len(missing_secrets) == 0, missing_secrets)


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

    # Get CORS origins from environment
    cors_origins = os.getenv("CORS_ORIGINS", "")

    settings = Settings(
        mongo_uri=mongo_uri,
        admin_username=admin_username,
        admin_password_hash=admin_password_hash,
        jwt_secret=jwt_secret,
        cors_origins=cors_origins,
    )

    # Validate required secrets at startup
    is_valid, missing_secrets = settings.validate_required_secrets()

    if not is_valid:
        error_msg = (
            "CRITICAL: Required secrets are missing or invalid!\n"
            f"Missing/Invalid: {', '.join(missing_secrets)}\n\n"
            "The service will not start until all required secrets are configured.\n"
            "Please set the following environment variables or configure them in Vault:\n"
        )
        for secret in missing_secrets:
            error_msg += f"  - {secret}\n"

        error_msg += "\nFor development, you can set these in your .env file.\n"
        error_msg += "For production, use HashiCorp Vault or GCP Secret Manager.\n"

        logger.error(error_msg)
        raise ValueError(f"Missing required secrets: {', '.join(missing_secrets)}")

    logger.info("✅ All required secrets validated successfully")
    return settings
