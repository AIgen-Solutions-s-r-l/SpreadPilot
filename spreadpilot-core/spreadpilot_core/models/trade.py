"""Trade model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    """Trade side enum."""

    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, Enum):
    """Trade status enum."""

    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"


class Trade(BaseModel):
    """Trade model.
    
    Maps to Firestore collection: trades/{tradeId}
    """

    id: str = Field(..., description="Trade ID")
    follower_id: str = Field(..., description="Follower ID")
    side: TradeSide = Field(..., description="Trade side")
    qty: int = Field(..., description="Quantity")
    strike: float = Field(..., description="Strike price")
    limit_price_requested: float = Field(..., description="Requested limit price")
    status: TradeStatus = Field(..., description="Trade status")
    timestamps: Dict[str, Optional[datetime]] = Field(default_factory=dict, description="Timestamps (e.g., 'submitted', 'filled', 'closed')")
    error_code: Optional[str] = Field(None, description="Error code (if any)")
    error_msg: Optional[str] = Field(None, description="Error message (if any)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    def to_dict(self):
        """Convert to dict for Firestore."""
        return {
            "followerId": self.follower_id,
            "side": self.side.value,
            "qty": self.qty,
            "strike": self.strike,
            "limitPriceRequested": self.limit_price_requested,
            "status": self.status.value,
            "timestamps": self.timestamps,
            "errorCode": self.error_code,
            "errorMsg": self.error_msg,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, id: str, data: dict):
        """Create from Firestore dict."""
        return cls(
            id=id,
            follower_id=data.get("followerId"),
            side=TradeSide(data.get("side")),
            qty=data.get("qty"),
            strike=data.get("strike"),
            limit_price_requested=data.get("limitPriceRequested"),
            status=TradeStatus(data.get("status")),
            timestamps=data.get("timestamps", {}),
            error_code=data.get("errorCode"),
            error_msg=data.get("errorMsg"),
            created_at=data.get("createdAt", datetime.utcnow()),
            updated_at=data.get("updatedAt", datetime.utcnow()),
        )