"""Trade model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any  # Added Any, Annotated

from bson import ObjectId  # Added ObjectId
from pydantic import BaseModel, Field
from pydantic.functional_validators import \
    BeforeValidator  # Added BeforeValidator


# Validator function to convert ObjectId to str
def validate_objectid_to_str(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    # If it's already a string (e.g., during creation), keep it
    if isinstance(v, str):
        return v
    # Raise error for other unexpected types
    raise TypeError("ObjectId or str required")


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

    Maps to MongoDB collection: trades
    """

    # Use alias for MongoDB compatibility (_id) and validator for ObjectId -> str conversion
    id: Annotated[str, BeforeValidator(validate_objectid_to_str)] = Field(
        ..., description="Unique Trade ID", alias="_id"
    )
    follower_id: str = Field(..., description="Follower ID (Index this field)")
    side: TradeSide = Field(..., description="Trade side")
    qty: int = Field(..., description="Quantity")
    strike: float = Field(..., description="Strike price")
    limit_price_requested: float = Field(..., description="Requested limit price")
    status: TradeStatus = Field(..., description="Trade status")
    timestamps: dict[str, datetime | None] = Field(
        default_factory=dict,
        description="Timestamps (e.g., 'submitted', 'filled', 'closed')",
    )
    error_code: str | None = Field(None, description="Error code (if any)")
    error_msg: str | None = Field(None, description="Error message (if any)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    # Removed custom to_dict and from_dict methods.
    # Rely on Pydantic's model_dump(by_alias=True) for MongoDB serialization
    # and model_validate for deserialization.

    class Config:
        # Allow population by field name OR alias
        # Needed for model_validate to correctly map _id from Mongo to id
        populate_by_name = True
