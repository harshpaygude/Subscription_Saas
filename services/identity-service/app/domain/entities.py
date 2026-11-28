"""Pure domain entities for Identity, Organizations, Departments, and Employees."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class OrganizationEntity:
    id: Optional[int]
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


@dataclass
class UserEntity:
    id: Optional[int]
    email: str
    password_hash: str
    organization_id: int
    role: str
    created_at: datetime
    display_name: Optional[str] = None
    employee_id: Optional[str] = None
    phone_number: Optional[str] = None


@dataclass
class DepartmentEntity:
    id: Optional[int]
    organization_id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class DepartmentMembershipEntity:
    id: Optional[int]
    organization_id: int
    department_id: int
    user_id: int
    is_active: bool
    effective_from: date
    effective_to: Optional[date]
    created_at: datetime
