"""Configuration for paper trading gateway."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Paper gateway settings."""

    # MongoDB
    mongo_uri: str = Field(
        default="mongodb://admin:password@localhost:27017",
        env="MONGO_URI",
        description="MongoDB connection URI",
    )
    mongo_db_name: str = Field(
        default="spreadpilot_paper",
        env="MONGO_DB_NAME",
        description="MongoDB database name for paper trading",
    )

    # Paper Trading Configuration
    paper_initial_balance: float = Field(
        default=100000.0,
        env="PAPER_INITIAL_BALANCE",
        description="Initial paper trading account balance",
    )
    paper_commission_rate: float = Field(
        default=0.005,
        env="PAPER_COMMISSION_RATE",
        description="Commission per share (default: $0.005)",
    )
    paper_option_commission: float = Field(
        default=0.65,
        env="PAPER_OPTION_COMMISSION",
        description="Commission per option contract (default: $0.65)",
    )
    paper_slippage_bps: float = Field(
        default=5.0,
        env="PAPER_SLIPPAGE_BPS",
        description="Slippage in basis points (default: 5 bps)",
    )
    paper_volatility: float = Field(
        default=0.02,
        env="PAPER_VOLATILITY",
        description="Daily volatility for price simulation (default: 2%)",
    )

    # Market Data
    market_data_source: str = Field(
        default="mock",
        env="MARKET_DATA_SOURCE",
        description="Market data source: mock, historical, or live",
    )

    # Market Hours (US Eastern Time)
    market_open_hour: int = Field(default=9, env="MARKET_OPEN_HOUR")
    market_open_minute: int = Field(default=30, env="MARKET_OPEN_MINUTE")
    market_close_hour: int = Field(default=16, env="MARKET_CLOSE_HOUR")
    market_close_minute: int = Field(default=0, env="MARKET_CLOSE_MINUTE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
_settings = None


def get_settings() -> Settings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
