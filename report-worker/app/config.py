"""Configuration module for the report worker."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings
from spreadpilot_core.logging import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Application settings for the report worker.

    Loads settings from environment variables.
    """

    # Google Cloud Project
    project_id: str = Field(
        ...,
        env="GOOGLE_CLOUD_PROJECT",
        description="Google Cloud Project ID",
    )

    # MongoDB Settings
    mongo_uri: str | None = Field(
        None,
        env="MONGO_URI",
        description="MongoDB connection URI",
    )
    mongo_db_name: str = Field(
        default="spreadpilot_admin",
        env="MONGO_DB_NAME",
        description="MongoDB database name",
    )
    mongo_db_name_secrets: str = Field(
        default="spreadpilot_secrets",
        env="MONGO_DB_NAME_SECRETS",
        description="MongoDB secrets database name",
    )

    # PostgreSQL Settings for P&L data
    postgres_uri: str | None = Field(
        None,
        env="POSTGRES_URI",
        description="PostgreSQL connection URI for P&L data",
    )

    # Report Settings
    default_commission_percentage: float = Field(
        default=20.0,
        env="DEFAULT_COMMISSION_PERCENTAGE",
        description="Default commission percentage",
    )
    report_sender_email: str = Field(
        ...,
        env="REPORT_SENDER_EMAIL",
        description="Email address for sending reports",
    )
    admin_email: str | None = Field(
        None,
        env="ADMIN_EMAIL",
        description="Admin email address for CC",
    )

    # Timing Settings
    market_close_timezone: str = Field(
        default="America/New_York",
        env="MARKET_CLOSE_TIMEZONE",
        description="Market close timezone",
    )
    market_close_hour: int = Field(
        default=16,
        env="MARKET_CLOSE_HOUR",
        description="Market close hour",
    )
    market_close_minute: int = Field(
        default=10,
        env="MARKET_CLOSE_MINUTE",
        description="Market close minute",
    )

    # Email Settings
    smtp_uri: str | None = Field(
        None,
        env="SMTP_URI",
        description="SMTP URI (e.g., smtp://user:pass@host:port)",
    )
    smtp_host: str | None = Field(
        None,
        env="SMTP_HOST",
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=587,
        env="SMTP_PORT",
        description="SMTP server port",
    )
    smtp_user: str | None = Field(
        None,
        env="SMTP_USER",
        description="SMTP username",
    )
    smtp_password: str | None = Field(
        None,
        env="SMTP_PASSWORD",
        description="SMTP password",
    )
    smtp_tls: bool = Field(
        default=True,
        env="SMTP_TLS",
        description="Enable SMTP TLS",
    )

    # GCS Settings
    gcs_bucket_name: str | None = Field(
        None,
        env="GCS_BUCKET_NAME",
        description="Google Cloud Storage bucket name for report files",
    )
    gcs_service_account_key_path: str | None = Field(
        None,
        env="GCS_SERVICE_ACCOUNT_KEY_PATH",
        description="Path to GCS service account key file",
    )

    # MinIO/S3 Settings
    minio_endpoint_url: str | None = Field(
        None,
        env="MINIO_ENDPOINT_URL",
        description="MinIO endpoint URL (e.g., https://minio.example.com)",
    )
    minio_access_key: str | None = Field(
        None,
        env="MINIO_ACCESS_KEY",
        description="MinIO access key",
    )
    minio_secret_key: str | None = Field(
        None,
        env="MINIO_SECRET_KEY",
        description="MinIO secret key",
    )
    minio_bucket_name: str | None = Field(
        None,
        env="MINIO_BUCKET_NAME",
        description="MinIO bucket name for report files",
    )
    minio_region: str = Field(
        default="us-east-1",
        env="MINIO_REGION",
        description="MinIO region",
    )
    minio_secure: bool = Field(
        default=True,
        env="MINIO_SECURE",
        description="Use HTTPS for MinIO connections",
    )

    # Dry-run mode
    dry_run_mode: bool = Field(
        default=False,
        env="DRY_RUN_MODE",
        description="Enable dry-run mode (simulate operations without executing)",
    )

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings."""
    settings = Settings()
    logger.info(
        "Loaded report worker settings",
        project_id=settings.project_id,
        mongo_db_name=settings.mongo_db_name,
        gcs_bucket_configured=bool(settings.gcs_bucket_name),
        smtp_configured=bool(settings.smtp_host),
        minio_configured=bool(settings.minio_endpoint_url),
    )
    return settings
