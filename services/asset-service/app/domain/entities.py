"""Pure domain entities for IT Assets, Custody Assignments, and Maintenance."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

UNASSIGNABLE_STATUSES = {"RETIRED", "LOST", "UNDER_MAINTENANCE"}


@dataclass
class AssetEntity:
    id: Optional[int]
    organization_id: int
    asset_tag: str
    asset_type: str
    name: str
    manufacturer: Optional[str]
    model: Optional[str]
    serial_number: Optional[str]
    purchase_date: Optional[date]
    purchase_cost: Optional[Decimal]
    currency: str
    warranty_expiry: Optional[date]
    status: str
    location: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class AssetAssignmentEntity:
    id: Optional[int]
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


@dataclass
class AssetMaintenanceEntity:
    id: Optional[int]
    organization_id: int
    asset_id: int
    event_type: str
    description: str
    performed_at: date
    cost: Optional[Decimal]
    currency: str
    performed_by: int
    status: str
    created_at: datetime
