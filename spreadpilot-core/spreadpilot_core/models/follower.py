"""Follower model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any  # Added Annotated

from bson import ObjectId  # Added ObjectId
from pydantic import BaseModel, EmailStr, Field, validator
from pydantic.functional_validators import BeforeValidator  # Added BeforeValidator


class FollowerState(str, Enum):
    """Follower state enum."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    MANUAL_INTERVENTION = "MANUAL_INTERVENTION"


# Validator function to convert ObjectId to str
def validate_objectid_to_str(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    # If it's already a string (e.g., during creation), keep it
    if isinstance(v, str):
        return v
    # Raise error for other unexpected types
    raise TypeError("ObjectId or str required")


class Follower(BaseModel):
    """Follower model.

    Maps to MongoDB collection: followers
    """

    # Use alias for MongoDB compatibility (_id) and validator for ObjectId -> str conversion
    id: Annotated[str, BeforeValidator(validate_objectid_to_str)] = Field(
        ..., description="Unique follower ID", alias="_id"
    )
    email: EmailStr = Field(..., description="Follower email address")
    iban: str = Field(..., description="Follower IBAN for commission payments")
    ibkr_username: str = Field(..., description="IBKR username")
    ibkr_secret_ref: str = Field(
        ..., description="Secret Manager reference for IBKR password"
    )
    commission_pct: float = Field(..., description="Commission percentage (0-100)")
    enabled: bool = Field(default=False, description="Whether the follower is enabled")
    state: FollowerState = Field(
        default=FollowerState.DISABLED, description="Follower state"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    @validator("commission_pct")
    def validate_commission_pct(cls, v):
        """Validate commission percentage."""
        if v < 0 or v > 100:
            raise ValueError("Commission percentage must be between 0 and 100")
        return v

    # Removed custom to_dict and from_dict methods.
    # Rely on Pydantic's model_dump(by_alias=True) for MongoDB serialization
    # and model_validate for deserialization.
    # Ensure MongoDB stores fields in snake_case matching the model attributes.

    class Config:
        # Allow population by field name OR alias
        # Needed for model_validate to correctly map _id from Mongo to id
        populate_by_name = True
        # Optional: If you want to ensure _id is always used in output dicts
        # serialization_alias = {'id': '_id'} # Handled by model_dump(by_alias=True)
