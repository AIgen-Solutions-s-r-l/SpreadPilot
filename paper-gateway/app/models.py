"""Data models for paper trading gateway."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderAction(str, Enum):
    """Order action."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""

    MARKET = "MKT"
    LIMIT = "LMT"


class OrderStatus(str, Enum):
    """Order status."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class AssetType(str, Enum):
    """Asset type."""

    STOCK = "STOCK"
    OPTION = "OPTION"


class OptionType(str, Enum):
    """Option type."""

    CALL = "CALL"
    PUT = "PUT"


# Request Models


class OrderRequest(BaseModel):
    """Order placement request."""

    symbol: str = Field(..., description="Symbol to trade")
    action: OrderAction = Field(..., description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Number of shares/contracts")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    limit_price: Optional[float] = Field(None, gt=0, description="Limit price (for LMT orders)")
    asset_type: AssetType = Field(default=AssetType.STOCK, description="Asset type")

    # Option-specific fields
    strike: Optional[float] = Field(None, description="Strike price (for options)")
    expiry: Optional[str] = Field(None, description="Expiry date YYYY-MM-DD (for options)")
    option_type: Optional[OptionType] = Field(None, description="CALL or PUT (for options)")


class BalanceUpdateRequest(BaseModel):
    """Balance update request for admin."""

    new_balance: float = Field(..., gt=0, description="New account balance")


# Response Models


class OrderResponse(BaseModel):
    """Order response."""

    order_id: str
    symbol: str
    action: OrderAction
    quantity: int
    order_type: OrderType
    limit_price: Optional[float]
    status: OrderStatus
    fill_price: Optional[float]
    filled_quantity: int
    commission: float
    timestamp: datetime
    rejection_reason: Optional[str] = None


class Position(BaseModel):
    """Position response."""

    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    asset_type: AssetType

    # Option-specific fields
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[OptionType] = None


class AccountInfo(BaseModel):
    """Account information response."""

    net_liquidation: float
    available_funds: float
    buying_power: float
    daily_pnl: float
    total_pnl: float
    positions_value: float
    cash_balance: float
    margin_used: float


class PerformanceMetrics(BaseModel):
    """Performance metrics response."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_commission: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: float
    average_win: float
    average_loss: float
    profit_factor: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    market_open: bool
    timestamp: datetime


# Database Models


class OrderDocument(BaseModel):
    """Order document for MongoDB."""

    order_id: str
    symbol: str
    action: str
    quantity: int
    order_type: str
    limit_price: Optional[float] = None
    status: str
    fill_price: Optional[float] = None
    filled_quantity: int
    commission: float
    slippage: float
    timestamp: datetime
    rejection_reason: Optional[str] = None
    asset_type: str

    # Option-specific
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[str] = None


class PositionDocument(BaseModel):
    """Position document for MongoDB."""

    symbol: str
    quantity: int
    avg_cost: float
    realized_pnl: float
    asset_type: str

    # Option-specific
    strike: Optional[float] = None
    expiry: Optional[str] = None
    option_type: Optional[str] = None


class AccountDocument(BaseModel):
    """Account document for MongoDB."""

    cash_balance: float
    total_pnl: float
    total_commission: float
    initial_balance: float
    created_at: datetime
    updated_at: datetime
