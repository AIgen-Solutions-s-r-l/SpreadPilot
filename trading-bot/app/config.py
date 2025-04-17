"""Configuration module for the trading bot."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field, validator

from spreadpilot_core.logging import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Application settings.
    
    Loads settings from environment variables.
    """

    # Google Cloud Project
    project_id: str = Field(
        default="spreadpilot-dev",
        env="GOOGLE_CLOUD_PROJECT",
        description="Google Cloud Project ID",
    )
    
    # Google Sheets
    google_sheet_url: str = Field(
        ...,
        env="GOOGLE_SHEET_URL",
        description="Google Sheet URL containing trading signals",
    )
    google_sheets_api_key: Optional[str] = Field(
        None,
        env="GOOGLE_SHEETS_API_KEY",
        description="Google Sheets API key",
    )
    
    # IBKR
    ib_gateway_host: str = Field(
        default="127.0.0.1",
        env="IB_GATEWAY_HOST",
        description="IB Gateway host",
    )
    ib_gateway_port: int = Field(
        default=4002,
        env="IB_GATEWAY_PORT",
        description="IB Gateway port (4001 for live, 4002 for paper)",
    )
    ib_client_id: int = Field(
        default=1,
        env="IB_CLIENT_ID",
        description="IB client ID",
    )
    ib_trading_mode: str = Field(
        default="paper",
        env="IB_TRADING_MODE",
        description="IB trading mode (paper or live)",
    )
    
    # Trading parameters
    min_price: float = Field(
        default=0.70,
        env="MIN_PRICE",
        description="Minimum price for vertical spread (absolute value)",
    )
    price_increment: float = Field(
        default=0.01,
        env="PRICE_INCREMENT",
        description="Price increment for limit orders",
    )
    max_attempts: int = Field(
        default=10,
        env="MAX_ATTEMPTS",
        description="Maximum number of attempts for limit orders",
    )
    timeout_seconds: int = Field(
        default=5,
        env="TIMEOUT_SECONDS",
        description="Timeout in seconds for each limit order attempt",
    )
    
    # Polling parameters
    polling_interval_seconds: float = Field(
        default=1.0,
        env="POLLING_INTERVAL_SECONDS",
        description="Interval in seconds for polling Google Sheets",
    )
    position_check_interval_seconds: float = Field(
        default=60.0,
        env="POSITION_CHECK_INTERVAL_SECONDS",
        description="Interval in seconds for checking positions",
    )
    
    # Firestore
    firestore_emulator_host: Optional[str] = Field(
        None,
        env="FIRESTORE_EMULATOR_HOST",
        description="Firestore emulator host (for local development)",
    )
    
    # Alerting
    telegram_bot_token: Optional[str] = Field(
        None,
        env="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token",
    )
    telegram_chat_id: Optional[str] = Field(
        None,
        env="TELEGRAM_CHAT_ID",
        description="Telegram chat ID",
    )
    sendgrid_api_key: Optional[str] = Field(
        None,
        env="SENDGRID_API_KEY",
        description="SendGrid API key",
    )
    admin_email: Optional[str] = Field(
        None,
        env="ADMIN_EMAIL",
        description="Admin email address",
    )
    
    # Dashboard URL
    dashboard_url: Optional[str] = Field(
        None,
        env="DASHBOARD_URL",
        description="Dashboard URL for deep links in alerts",
    )
    
    @validator("ib_trading_mode")
    def validate_trading_mode(cls, v):
        """Validate trading mode."""
        if v not in ["paper", "live"]:
            raise ValueError("Trading mode must be 'paper' or 'live'")
        return v
    
    class Config:
        """Pydantic config."""
        
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings."""
    settings = Settings()
    logger.info(
        "Loaded settings",
        project_id=settings.project_id,
        ib_gateway_host=settings.ib_gateway_host,
        ib_gateway_port=settings.ib_gateway_port,
        ib_trading_mode=settings.ib_trading_mode,
    )
    return settings