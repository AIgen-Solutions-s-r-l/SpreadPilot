"""Alert model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, Annotated # Added Annotated
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


class AlertSeverity(str, Enum):
    """Alert severity enum."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    """Alert type enum."""

    COMPONENT_DOWN = "COMPONENT_DOWN"
    NO_MARGIN = "NO_MARGIN"
    MID_TOO_LOW = "MID_TOO_LOW"
    LIMIT_REACHED = "LIMIT_REACHED"
    ASSIGNMENT_DETECTED = "ASSIGNMENT_DETECTED"
    ASSIGNMENT_COMPENSATED = "ASSIGNMENT_COMPENSATED"
    REPORT_FAILED = "REPORT_FAILED"
    PARTIAL_FILL_HIGH = "PARTIAL_FILL_HIGH"
    GATEWAY_UNREACHABLE = "GATEWAY_UNREACHABLE"
    WATCHDOG_FAILURE = "WATCHDOG_FAILURE"


class Alert(BaseModel):
    """Alert model.
    
    Maps to MongoDB collection: alerts
    """

    # Use alias for MongoDB compatibility (_id) and validator for ObjectId -> str conversion
    id: Annotated[str, BeforeValidator(validate_objectid_to_str)] = Field(..., description="Unique Alert ID", alias='_id')
    follower_id: Optional[str] = Field(None, description="Follower ID (optional)")
    severity: AlertSeverity = Field(..., description="Alert severity")
    type: AlertType = Field(..., description="Alert type")
    message: str = Field(..., description="Alert message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    acknowledged: bool = Field(default=False, description="Whether the alert has been acknowledged")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgement timestamp")
    acknowledged_by: Optional[str] = Field(None, description="User who acknowledged the alert")

    # Removed custom to_dict and from_dict methods.
    # Rely on Pydantic's model_dump(by_alias=True) for MongoDB serialization
    # and model_validate for deserialization.

    class Config:
        # Allow population by field name OR alias
        # Needed for model_validate to correctly map _id from Mongo to id
        populate_by_name = True


class AlertEvent(BaseModel):
    """Alert event model for routing alerts."""
    
    event_type: AlertType
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    params: Optional[Dict[str, Any]] = None