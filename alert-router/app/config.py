import logging
import os
from typing import List, Optional

from pydantic import Field, EmailStr, validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application configuration settings."""

    # General Settings
    GCP_PROJECT_ID: str = Field(..., env="GCP_PROJECT_ID")
    DASHBOARD_BASE_URL: str = Field(..., env="DASHBOARD_BASE_URL")

    # Telegram Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_IDS: List[str] = Field([], env="TELEGRAM_ADMIN_IDS")

    # Email Settings
    EMAIL_SENDER: Optional[EmailStr] = Field(None, env="EMAIL_SENDER")
    EMAIL_ADMIN_RECIPIENTS: List[EmailStr] = Field([], env="EMAIL_ADMIN_RECIPIENTS")
    SMTP_HOST: Optional[str] = Field(None, env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    SMTP_TLS: bool = Field(True, env="SMTP_TLS")

    # MongoDB Settings
    MONGO_URI: Optional[str] = Field(None, env="MONGO_URI")
    MONGO_DB_NAME: str = Field("spreadpilot_admin", env="MONGO_DB_NAME")
    MONGO_DB_NAME_SECRETS: Optional[str] = Field(None, env="MONGO_DB_NAME_SECRETS")
    
    # Redis Settings
    REDIS_URL: str = Field(..., env="REDIS_URL")

    @validator("TELEGRAM_ADMIN_IDS", "EMAIL_ADMIN_RECIPIENTS", pre=True)
    def split_string(cls, v):
        """Split comma-separated strings into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

try:
    settings = Settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Error loading settings: {e}")
    # Provide default settings or handle error appropriately
    settings = Settings(_env_file=None)  # Attempt to load with defaults if .env fails
    logger.warning("Falling back to default/empty settings due to loading error.")