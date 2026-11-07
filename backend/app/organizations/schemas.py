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


class EmployeeInput(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=80)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    phone_number: Optional[str] = None
    department_name: Optional[str] = None
    joining_date: Optional[str] = None


class AssetInput(BaseModel):
    asset_tag: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=255)
    asset_type: str = Field(default="Laptop", max_length=80)
    manufacturer: Optional[str] = Field(default=None, max_length=120)
    model: Optional[str] = Field(default=None, max_length=120)
    serial_number: Optional[str] = Field(default=None, max_length=160)
    purchase_cost: Optional[str] = None
    currency: Optional[str] = Field(default="USD", max_length=3)
    location: Optional[str] = Field(default=None, max_length=255)
    assigned_to: Optional[str] = Field(default=None, max_length=255)


class SubscriptionImportInput(BaseModel):
    provider: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    plan: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = Field(default="USD", max_length=3)
    billing_interval: Optional[str] = Field(default="monthly", max_length=20)
    renewal_type: Optional[str] = Field(default="AUTOPAY", max_length=50)
    start_date: Optional[str] = None
    next_renewal_date: Optional[str] = None
    status: Optional[str] = Field(default="ACTIVE", max_length=30)
    note: Optional[str] = None


class IntegrationImportInput(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=100)
    provider_name: Optional[str] = None
    category: Optional[str] = Field(default="cloud", max_length=50)
    status: Optional[str] = Field(default="CONNECTED", max_length=50)
    account_or_tenant_id: Optional[str] = None
    notes: Optional[str] = None


class OnboardingSubmit(BaseModel):
    company: OrganizationProfileUpdate
    departments: list[DepartmentInput] = Field(default_factory=list)
    employees: list[EmployeeInput] = Field(default_factory=list)
    assets: list[AssetInput] = Field(default_factory=list)
    subscriptions: list[SubscriptionImportInput] = Field(default_factory=list)
    integrations: list[IntegrationImportInput] = Field(default_factory=list)


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
