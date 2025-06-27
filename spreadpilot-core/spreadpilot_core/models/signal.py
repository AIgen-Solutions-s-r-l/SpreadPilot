"""Signal model for SpreadPilot trading signals."""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

from pydantic import BaseModel, Field


@dataclass
class Signal:
    """Trading signal data structure.
    
    This dataclass represents a trading signal extracted from Google Sheets
    and emitted via Redis Pub/Sub for processing by the trading bot.
    """
    
    ticker: str
    strategy: str  # "Long" for Bull Put, "Short" for Bear Call
    qty_per_leg: int
    strike_long: float
    strike_short: float
    signal_date: datetime
    sheet_row: int
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Convert signal to dictionary for Redis serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Signal':
        """Create Signal instance from dictionary."""
        # Handle datetime conversion if they come as strings
        if isinstance(data.get('signal_date'), str):
            data['signal_date'] = datetime.fromisoformat(data['signal_date'])
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the signal."""
        return (f"Signal({self.ticker} {self.strategy} "
                f"{self.qty_per_leg}x {self.strike_long}/{self.strike_short} "
                f"on {self.signal_date.strftime('%Y-%m-%d')})")


class SignalResponse(BaseModel):
    """Pydantic model for API responses containing signals."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    strategy: str = Field(..., description="Strategy type (Long/Short)")
    qty_per_leg: int = Field(..., description="Quantity per leg")
    strike_long: float = Field(..., description="Strike price for long leg")
    strike_short: float = Field(..., description="Strike price for short leg")
    signal_date: datetime = Field(..., description="Date of the signal")
    sheet_row: int = Field(..., description="Row number in Google Sheet")
    timestamp: datetime = Field(..., description="Signal emission timestamp")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }