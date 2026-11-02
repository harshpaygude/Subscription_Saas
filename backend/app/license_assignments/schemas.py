from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LicenseCreate(BaseModel):
    reference: Optional[str] = Field(default=None, max_length=255)
    capacity: int = Field(default=1, ge=1, le=100000)


class LicenseResponse(LicenseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    subscription_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class SubscriptionAssignmentCreate(BaseModel):
    subscription_id: int
    license_id: Optional[int] = None
    user_id: int
    notes: Optional[str] = Field(default=None, max_length=4000)


class SubscriptionAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    subscription_id: int
    license_id: Optional[int]
    user_id: int
    assigned_by: int
    assigned_at: datetime
    released_at: Optional[datetime]
    status: str
    notes: Optional[str]

