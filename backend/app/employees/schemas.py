from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EmployeeSummary(BaseModel):
    id: int
    email: str
    display_name: Optional[str]
    employee_id: Optional[str]
    phone_number: Optional[str]
    role: str
    department_ids: list[int]
    active_subscription_assignments: int
    active_asset_assignments: int


class EmployeeDetail(EmployeeSummary):
    created_at: datetime


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone_number: Optional[str] = Field(default=None, max_length=40)
    department_id: int
    joined_at: date
    asset_ids: list[int] = Field(default_factory=list)

