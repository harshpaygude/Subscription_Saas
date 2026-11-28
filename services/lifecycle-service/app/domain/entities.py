"""Pure domain entities for Employee Lifecycle and Clearance Tasks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class EmployeeLifecycleEntity:
    id: Optional[int]
    organization_id: int
    user_id: int
    status: str
    joined_at: date
    last_working_date: Optional[date]
    offboarding_initiated_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class LifecycleTaskEntity:
    id: Optional[int]
    organization_id: int
    lifecycle_id: int
    task_type: str
    title: str
    status: str
    action_status: str
    required: bool
    assignee_id: Optional[int]
    related_subscription_id: Optional[int]
    related_subscription_assignment_id: Optional[int]
    related_asset_id: Optional[int]
    related_asset_assignment_id: Optional[int]
    due_at: Optional[date]
    completed_at: Optional[datetime]
    completed_by: Optional[int]
    completion_note: Optional[str]
    created_at: datetime
    updated_at: datetime
