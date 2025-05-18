from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class FollowerBase(BaseModel):
    """Base Follower model with common attributes."""
    name: str
    email: EmailStr
    status: str = "active"  # active, inactive, pending
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class FollowerCreate(FollowerBase):
    """Model for creating a new follower."""
    pass

class FollowerUpdate(BaseModel):
    """Model for updating a follower (all fields optional)."""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    telegram_id: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class FollowerResponse(FollowerBase):
    """Model for follower response with additional fields."""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True