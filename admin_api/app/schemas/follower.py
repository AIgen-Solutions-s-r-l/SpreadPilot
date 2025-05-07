from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# Import FollowerState from the core library
from spreadpilot_core.models.follower import FollowerState


# Shared properties
class FollowerBase(BaseModel):
    email: EmailStr = Field(..., description="Follower email address")
    iban: str = Field(..., description="Follower IBAN for commission payments")
    ibkr_username: str = Field(..., description="IBKR username")
    ibkr_secret_ref: str = Field(..., description="Secret Manager reference for IBKR password")
    commission_pct: float = Field(..., ge=0, le=100, description="Commission percentage (0-100)")


# Properties to receive via API on creation
class FollowerCreate(FollowerBase):
    # No extra fields needed for creation, defaults are handled by the core model or DB layer
    pass


# Properties to return to client
class FollowerRead(FollowerBase):
    id: str = Field(..., description="Unique follower ID")
    enabled: bool = Field(..., description="Whether the follower is enabled")
    state: FollowerState = Field(..., description="Follower state")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        # Enable ORM mode if we were using an ORM like SQLModel/SQLAlchemy
        # orm_mode = True
        # For Firestore, we'll manually map dicts to this model
        pass


# Properties for updating
class FollowerUpdate(BaseModel):
    email: Optional[EmailStr] = None
    iban: Optional[str] = None
    ibkr_username: Optional[str] = None
    ibkr_secret_ref: Optional[str] = None
    commission_pct: Optional[float] = Field(default=None, ge=0, le=100)
    enabled: Optional[bool] = None
    state: Optional[FollowerState] = None