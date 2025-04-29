"""Position model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssignmentState(str, Enum):
    """Assignment state enum."""

    NONE = "NONE"
    ASSIGNED = "ASSIGNED"
    COMPENSATED = "COMPENSATED"


class Position(BaseModel):
    """Position model.
    
    Maps to Firestore collection: positions/{followerId}/daily/{YYYYMMDD}
    """

    follower_id: str = Field(..., description="Follower ID")
    date: str = Field(..., description="Position date (YYYYMMDD)")
    short_qty: int = Field(default=0, description="Short quantity")
    long_qty: int = Field(default=0, description="Long quantity")
    pnl_realized: float = Field(default=0.0, description="Realized P&L")
    pnl_mtm: float = Field(default=0.0, description="Mark-to-market P&L")
    assignment_state: AssignmentState = Field(
        default=AssignmentState.NONE, description="Assignment state"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    def to_dict(self):
        """Convert to dict for Firestore."""
        return {
            "shortQty": self.short_qty,
            "longQty": self.long_qty,
            "pnlRealized": self.pnl_realized,
            "pnlMTM": self.pnl_mtm,
            "assignmentState": self.assignment_state.value,
            "updatedAt": self.updated_at,
        }

    @classmethod # Correct indentation
    def collection_name(cls) -> str:
        """Returns the Firestore collection name."""
        return "positions"

    @classmethod # Correct indentation
    def from_dict(cls, follower_id: str, date: str, data: dict):
        """Create from Firestore dict."""
        return cls(
            follower_id=follower_id,
            date=date,
            short_qty=data.get("shortQty", 0),
            long_qty=data.get("longQty", 0),
            pnl_realized=data.get("pnlRealized", 0.0),
            pnl_mtm=data.get("pnlMTM", 0.0),
            assignment_state=AssignmentState(data.get("assignmentState", AssignmentState.NONE.value)),
            updated_at=data.get("updatedAt", datetime.utcnow()),
        )