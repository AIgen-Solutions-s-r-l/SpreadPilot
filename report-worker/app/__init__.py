"""Report Worker application."""

from .config import get_settings

# Cached settings instance (lazy-initialized)
_settings = None


def _get_cached_settings():
    """Get or create cached settings instance."""
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings


# Module-level __getattr__ for lazy attribute access (Python 3.7+)
# This allows `from report_worker.app import MINIO_ENDPOINT_URL` to work
# without triggering settings initialization at import time
def __getattr__(name):
    """Lazy attribute access for settings."""
    settings = _get_cached_settings()

    # Map attribute names to settings attributes
    attr_map = {
        # MongoDB
        "MONGO_URI": "mongo_uri",
        "MONGO_DB_NAME": "mongo_db_name",
        # Report settings
        "DEFAULT_COMMISSION_PERCENTAGE": "default_commission_percentage",
        "REPORT_SENDER_EMAIL": "report_sender_email",
        "ADMIN_EMAIL": "admin_email",
        # Timing
        "MARKET_CLOSE_TIMEZONE": "market_close_timezone",
        # GCP
        "GCP_PROJECT_ID": "project_id",
        # MinIO
        "MINIO_ENDPOINT_URL": "minio_endpoint_url",
        "MINIO_ACCESS_KEY": "minio_access_key",
        "MINIO_SECRET_KEY": "minio_secret_key",
        "MINIO_BUCKET_NAME": "minio_bucket_name",
        "MINIO_REGION": "minio_region",
        "MINIO_SECURE": "minio_secure",
        # Also expose config for direct access
        "config": None,  # Return settings object directly
    }

    if name in attr_map:
        attr_name = attr_map[name]
        if attr_name is None:
            # Return the settings object itself for "config"
            return settings
        return getattr(settings, attr_name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
