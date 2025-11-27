from typing import Optional

from pydantic import BaseModel, Field
from spreadpilot_core.models.position import Position as CorePosition


class PositionResponse(CorePosition):
    """Schema for position response."""

    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True
