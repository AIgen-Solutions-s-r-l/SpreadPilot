from typing import Optional

from pydantic import BaseModel, Field
from spreadpilot_core.models.alert import Alert as CoreAlert


class AlertResponse(CoreAlert):
    """Schema for alert response."""

    id: Optional[str] = Field(None, alias="_id")

    class Config:
        populate_by_name = True
