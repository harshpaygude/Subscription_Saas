from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssetCreate(BaseModel):
    asset_tag: str = Field(min_length=1, max_length=120)
    asset_type: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    manufacturer: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    serial_number: Optional[str] = Field(default=None, max_length=160)
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    warranty_expiry: Optional[date] = None
    location: Optional[str] = Field(default=None, max_length=255)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    asset_type: Optional[str] = Field(default=None, min_length=1, max_length=80)
    status: Optional[str] = Field(default=None, max_length=30)
    location: Optional[str] = Field(default=None, max_length=255)
    warranty_expiry: Optional[date] = None


class AssetResponse(AssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class AssetAssignmentCreate(BaseModel):
    user_id: int
    expected_return_at: Optional[date] = None
    condition_at_issue: Optional[str] = Field(default=None, max_length=80)
    handover_notes: Optional[str] = Field(default=None, max_length=4000)


class AssetAssignmentReturn(BaseModel):
    condition_at_return: Optional[str] = Field(default=None, max_length=80)
    handover_notes: Optional[str] = Field(default=None, max_length=4000)


class AssetAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    asset_id: int
    user_id: int
    assigned_by: int
    assigned_at: datetime
    expected_return_at: Optional[date]
    returned_at: Optional[datetime]
    returned_by: Optional[int]
    condition_at_issue: Optional[str]
    condition_at_return: Optional[str]
    handover_notes: Optional[str]
    status: str


class MaintenanceCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    performed_at: date = Field(default_factory=date.today)
    cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    status: str = Field(default="COMPLETED", max_length=30)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class MaintenanceResponse(MaintenanceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    asset_id: int
    performed_by: int
    created_at: datetime

