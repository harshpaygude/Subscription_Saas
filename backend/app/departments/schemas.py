from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MembershipCreate(BaseModel):
    user_id: int
    effective_from: date = Field(default_factory=date.today)


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    department_id: int
    user_id: int
    is_active: bool
    effective_from: date
    effective_to: Optional[date]
    created_at: datetime
    email: Optional[str] = None
    display_name: Optional[str] = None

