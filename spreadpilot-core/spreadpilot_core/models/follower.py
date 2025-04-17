"""Follower model for SpreadPilot."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class FollowerState(str, Enum):
    """Follower state enum."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    MANUAL_INTERVENTION = "MANUAL_INTERVENTION"


class Follower(BaseModel):
    """Follower model.
    
    Maps to Firestore collection: followers/{followerId}
    """

    id: str = Field(..., description="Unique follower ID")
    email: EmailStr = Field(..., description="Follower email address")
    iban: str = Field(..., description="Follower IBAN for commission payments")
    ibkr_username: str = Field(..., description="IBKR username")
    ibkr_secret_ref: str = Field(..., description="Secret Manager reference for IBKR password")
    commission_pct: float = Field(..., description="Commission percentage (0-100)")
    enabled: bool = Field(default=False, description="Whether the follower is enabled")
    state: FollowerState = Field(default=FollowerState.DISABLED, description="Follower state")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @validator("commission_pct")
    def validate_commission_pct(cls, v):
        """Validate commission percentage."""
        if v < 0 or v > 100:
            raise ValueError("Commission percentage must be between 0 and 100")
        return v

    def to_dict(self):
        """Convert to dict for Firestore."""
        return {
            "email": self.email,
            "iban": self.iban,
            "ibkrUsername": self.ibkr_username,
            "ibkrSecretRef": self.ibkr_secret_ref,
            "commissionPct": self.commission_pct,
            "enabled": self.enabled,
            "state": self.state.value,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, id: str, data: dict):
        """Create from Firestore dict."""
        return cls(
            id=id,
            email=data.get("email"),
            iban=data.get("iban"),
            ibkr_username=data.get("ibkrUsername"),
            ibkr_secret_ref=data.get("ibkrSecretRef"),
            commission_pct=data.get("commissionPct"),
            enabled=data.get("enabled", False),
            state=FollowerState(data.get("state", FollowerState.DISABLED.value)),
            created_at=data.get("createdAt", datetime.utcnow()),
            updated_at=data.get("updatedAt", datetime.utcnow()),
        )