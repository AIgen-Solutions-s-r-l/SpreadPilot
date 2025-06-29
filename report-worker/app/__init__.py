"""Report Worker application."""

from .config import get_settings

# Export settings as config module attributes for backward compatibility
_settings = get_settings()

# MongoDB
MONGO_URI = _settings.mongo_uri
MONGO_DB_NAME = _settings.mongo_db_name

# Report settings
DEFAULT_COMMISSION_PERCENTAGE = _settings.default_commission_percentage
REPORT_SENDER_EMAIL = _settings.report_sender_email
ADMIN_EMAIL = _settings.admin_email

# Timing
MARKET_CLOSE_TIMEZONE = _settings.market_close_timezone

# GCP
GCP_PROJECT_ID = _settings.project_id

# MinIO
MINIO_ENDPOINT_URL = _settings.minio_endpoint_url
MINIO_ACCESS_KEY = _settings.minio_access_key
MINIO_SECRET_KEY = _settings.minio_secret_key
MINIO_BUCKET_NAME = _settings.minio_bucket_name
MINIO_REGION = _settings.minio_region
MINIO_SECURE = _settings.minio_secure
