from typing import Optional

from pydantic import BaseModel, Field
from spreadpilot_core.models.trade import Trade as CoreTrade


class TradeResponse(CoreTrade):
    """Schema for trade response."""

    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True
