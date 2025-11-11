"""Configuration module for the trading bot."""

from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings

from spreadpilot_core.logging import get_logger
from spreadpilot_core.utils.vault import get_vault_client

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
    google_sheets_api_key: str | None = Field(
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
    firestore_emulator_host: str | None = Field(
        None,
        env="FIRESTORE_EMULATOR_HOST",
        description="Firestore emulator host (for local development)",
    )

    # Alerting
    telegram_bot_token: str | None = Field(
        None,
        env="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token",
    )
    telegram_chat_id: str | None = Field(
        None,
        env="TELEGRAM_CHAT_ID",
        description="Telegram chat ID",
    )
    sendgrid_api_key: str | None = Field(
        None,
        env="SENDGRID_API_KEY",
        description="SendGrid API key",
    )
    admin_email: str | None = Field(
        None,
        env="ADMIN_EMAIL",
        description="Admin email address",
    )

    # Dashboard URL
    dashboard_url: str | None = Field(
        None,
        env="DASHBOARD_URL",
        description="Dashboard URL for deep links in alerts",
    )

    # Vault configuration
    vault_url: str = Field(
        default="http://vault:8200",
        env="VAULT_ADDR",
        description="HashiCorp Vault server URL",
    )
    vault_token: str | None = Field(
        None,
        env="VAULT_TOKEN",
        description="HashiCorp Vault authentication token",
    )
    vault_mount_point: str = Field(
        default="secret",
        env="VAULT_MOUNT_POINT",
        description="Vault KV mount point",
    )
    vault_enabled: bool = Field(
        default=True,
        env="VAULT_ENABLED",
        description="Enable Vault integration for secrets",
    )

    # Dry-run mode
    dry_run_mode: bool = Field(
        default=False,
        env="DRY_RUN_MODE",
        description="Enable dry-run mode (simulate operations without executing)",
    )

    @validator("ib_trading_mode")
    def validate_trading_mode(cls, v):
        """Validate trading mode."""
        if v not in ["paper", "live"]:
            raise ValueError("Trading mode must be 'paper' or 'live'")
        return v

    def get_ibkr_credentials_from_vault(self, secret_ref: str) -> dict[str, str] | None:
        """Get IBKR credentials from Vault.

        Args:
            secret_ref: Secret reference/path for IBKR credentials

        Returns:
            Dict with 'IB_USER' and 'IB_PASS' keys or None if not found
        """
        if not self.vault_enabled:
            logger.info("Vault integration is disabled, skipping credential retrieval")
            return None

        try:
            vault_client = get_vault_client()
            # Override client settings with config values
            vault_client.vault_url = self.vault_url
            if self.vault_token:
                vault_client.vault_token = self.vault_token
            vault_client.mount_point = self.vault_mount_point
            # Reset client to pick up new settings
            vault_client._client = None

            credentials = vault_client.get_ibkr_credentials(secret_ref)

            if credentials:
                logger.info(f"Successfully retrieved IBKR credentials from Vault for: {secret_ref}")
                return credentials
            else:
                logger.warning(f"No IBKR credentials found in Vault for: {secret_ref}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving IBKR credentials from Vault: {e}")
            return None

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
        "Loaded settings",
        project_id=settings.project_id,
        ib_gateway_host=settings.ib_gateway_host,
        ib_gateway_port=settings.ib_gateway_port,
        ib_trading_mode=settings.ib_trading_mode,
    )
    return settings


# Configuration for the Vertical Spreads on QQQ Strategy
VERTICAL_SPREADS_STRATEGY = {
    "enabled": True,
    "ibkr_secret_ref": "ibkr_vertical_spreads_strategy",  # For dedicated credentials
    "symbol": "QQQ",
    "signal_time": "09:27:00",  # NY Time to check for signals
    "max_attempts": 10,  # Maximum number of attempts for limit orders
    "price_increment": 0.01,  # Price increment for each attempt
    "min_price": 0.70,  # Minimum price threshold for vertical spreads
    "timeout_seconds": 5,  # Timeout in seconds for each attempt
    "time_value_threshold": 0.10,  # Time Value threshold for closing positions
    "time_value_check_interval": 60,  # Check Time Value every 60 seconds
}
