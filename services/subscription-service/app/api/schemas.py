"""Pydantic API schemas for Subscription Service."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

Interval = Literal["monthly", "annual", "quarterly", "weekly"]
SubscriptionStatus = Literal["ACTIVE", "CANCELLED", "ARCHIVED"]


class SubscriptionCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    plan: Optional[str] = Field(default=None, max_length=255)
    amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: Interval
    start_date: Optional[date] = None
    next_renewal_date: Optional[date] = None
    status: SubscriptionStatus = "ACTIVE"
    renewal_type: Optional[str] = Field(default="AUTOPAY", max_length=50)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class SubscriptionUpdate(BaseModel):
    provider: Optional[str] = Field(default=None, min_length=1, max_length=100)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    plan: Optional[str] = Field(default=None, max_length=255)
    amount: Optional[Decimal] = Field(default=None, ge=0, max_digits=18, decimal_places=6)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    billing_interval: Optional[Interval] = None
    start_date: Optional[date] = None
    next_renewal_date: Optional[date] = None
    status: Optional[SubscriptionStatus] = None
    renewal_type: Optional[str] = Field(default=None, max_length=50)
    cancellation_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    provider: str
    name: str
    plan: Optional[str]
    amount: Optional[Decimal]
    currency: str
    billing_interval: str
    start_date: Optional[date]
    next_renewal_date: Optional[date]
    status: str
    renewal_type: Optional[str] = "AUTOPAY"
    cancellation_date: Optional[date]
    source: str
    note: Optional[str]
    created_at: datetime
    updated_at: datetime


class ManualSpendCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: Interval = "monthly"
    period_start: date
    period_end: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class ManualSpendResponse(ManualSpendCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


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
