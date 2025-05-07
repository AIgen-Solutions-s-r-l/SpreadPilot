"""Position model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Annotated # Added Any, Annotated
from bson import ObjectId # Added ObjectId
from pydantic.functional_validators import BeforeValidator # Added BeforeValidator

from pydantic import BaseModel, Field


# Validator function to convert ObjectId to str
def validate_objectid_to_str(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    # If it's already a string (e.g., during creation), keep it
    if isinstance(v, str):
        return v
    # Raise error for other unexpected types
    raise TypeError('ObjectId or str required')


class AssignmentState(str, Enum):
    """Assignment state enum."""

    NONE = "NONE"
    ASSIGNED = "ASSIGNED"
    COMPENSATED = "COMPENSATED"


class Position(BaseModel):
    """Position model.
    
    Maps to MongoDB collection: positions
    Note: Firestore structure was nested. In MongoDB, this is a flat collection.
    Querying will rely on follower_id and date fields.
    """

    # Use alias for MongoDB compatibility (_id) and validator for ObjectId -> str conversion
    id: Annotated[str, BeforeValidator(validate_objectid_to_str)] = Field(..., description="Unique Position ID", alias='_id')
    follower_id: str = Field(..., description="Follower ID (Index this field)")
    date: str = Field(..., description="Position date (YYYYMMDD) (Index this field)")
    short_qty: int = Field(default=0, description="Short quantity")
    long_qty: int = Field(default=0, description="Long quantity")
    pnl_realized: float = Field(default=0.0, description="Realized P&L")
    pnl_mtm: float = Field(default=0.0, description="Mark-to-market P&L")
    assignment_state: AssignmentState = Field(
        default=AssignmentState.NONE, description="Assignment state"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Removed custom to_dict, from_dict, and collection_name methods.
    # Rely on Pydantic's model_dump(by_alias=True) for MongoDB serialization
    # and model_validate for deserialization.

    class Config:
        # Allow population by field name OR alias
        # Needed for model_validate to correctly map _id from Mongo to id
        populate_by_name = True