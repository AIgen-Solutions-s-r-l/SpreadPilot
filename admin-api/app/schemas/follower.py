from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class FollowerBase(BaseModel):
    """Base Follower model with common attributes."""

    name: str
    email: EmailStr
    status: str = "active"  # active, inactive, pending
    telegram_id: str | None = None
    phone: str | None = None
    notes: str | None = None


class FollowerCreate(FollowerBase):
    """Model for creating a new follower."""

    pass


class FollowerUpdate(BaseModel):
    """Model for updating a follower (all fields optional)."""

    name: str | None = None
    email: EmailStr | None = None
    status: str | None = None
    telegram_id: str | None = None
    phone: str | None = None
    notes: str | None = None
    preferences: dict[str, Any] | None = None


class FollowerResponse(FollowerBase):
    """Model for follower response with additional fields."""

    id: str
    created_at: datetime
    updated_at: datetime | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
