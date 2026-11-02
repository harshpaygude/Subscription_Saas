from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class OrganizationProfileUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=120)
    company_size: Optional[str] = Field(default=None, max_length=40)
    website: Optional[str] = Field(default=None, max_length=255)
    company_email: Optional[str] = Field(default=None, max_length=255)
    company_phone: Optional[str] = Field(default=None, max_length=60)
    country: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = None
    postal_code: Optional[str] = Field(default=None, max_length=20)
    tax_registration_number: Optional[str] = Field(default=None, max_length=100)


class DepartmentInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)


class OnboardingSubmit(BaseModel):
    company: OrganizationProfileUpdate
    departments: list[DepartmentInput] = Field(default_factory=list)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    legal_name: Optional[str] = None
    display_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    website: Optional[str] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    tax_registration_number: Optional[str] = None
    onboarding_completed: bool = False
    onboarding_completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
