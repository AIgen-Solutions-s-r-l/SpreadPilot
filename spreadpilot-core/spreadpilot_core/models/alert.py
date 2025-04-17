"""Alert model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


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
    
    Maps to Firestore collection: alerts/{alertId}
    """

    id: str = Field(..., description="Alert ID")
    follower_id: Optional[str] = Field(None, description="Follower ID (optional)")
    severity: AlertSeverity = Field(..., description="Alert severity")
    type: AlertType = Field(..., description="Alert type")
    message: str = Field(..., description="Alert message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    acknowledged: bool = Field(default=False, description="Whether the alert has been acknowledged")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgement timestamp")
    acknowledged_by: Optional[str] = Field(None, description="User who acknowledged the alert")

    def to_dict(self):
        """Convert to dict for Firestore."""
        return {
            "followerId": self.follower_id,
            "severity": self.severity.value,
            "type": self.type.value,
            "message": self.message,
            "createdAt": self.created_at,
            "acknowledged": self.acknowledged,
            "acknowledgedAt": self.acknowledged_at,
            "acknowledgedBy": self.acknowledged_by,
        }

    @classmethod
    def from_dict(cls, id: str, data: dict):
        """Create from Firestore dict."""
        return cls(
            id=id,
            follower_id=data.get("followerId"),
            severity=AlertSeverity(data.get("severity")),
            type=AlertType(data.get("type")),
            message=data.get("message"),
            created_at=data.get("createdAt", datetime.utcnow()),
            acknowledged=data.get("acknowledged", False),
            acknowledged_at=data.get("acknowledgedAt"),
            acknowledged_by=data.get("acknowledgedBy"),
        )


class AlertEvent(BaseModel):
    """Alert event model for routing alerts."""
    
    event_type: AlertType
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    params: Optional[Dict[str, Any]] = None