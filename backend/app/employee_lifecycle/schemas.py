from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OnboardingTaskRequest(BaseModel):
    task_type: str = Field(pattern="^(SUBSCRIPTION_ACCESS|ASSET_ISSUE|MANUAL_ACCESS)$")
    title: str = Field(min_length=1, max_length=255)
    subscription_id: Optional[int] = None
    asset_id: Optional[int] = None
    due_at: Optional[date] = None
    required: bool = True


class OnboardingRequest(BaseModel):
    department_id: int = Field(description="The employee's department. Onboarding always creates an active department membership.")
    joined_at: date = Field(default_factory=date.today)
    tasks: list[OnboardingTaskRequest] = Field(default_factory=list)


class OffboardingRequest(BaseModel):
    last_working_date: date


class TaskCompletionRequest(BaseModel):
    completion_note: Optional[str] = Field(default=None, max_length=4000)


class LifecycleTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
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


class LifecycleResourceResponse(BaseModel):
    id: int
    resource_id: int
    status: str
    assigned_at: datetime
    released_at: Optional[datetime] = None
    resource_name: Optional[str] = None
    resource_provider: Optional[str] = None


class LifecycleEmployeeResponse(BaseModel):
    id: int
    user_id: int
    email: str
    display_name: Optional[str]
    employee_id: Optional[str] = None
    phone_number: Optional[str] = None
    role: str
    status: str
    joined_at: date
    last_working_date: Optional[date]
    department_ids: list[int]
    department_names: list[str] = []
    subscription_assignments: list[LifecycleResourceResponse]
    asset_assignments: list[LifecycleResourceResponse]
    tasks: list[LifecycleTaskResponse]
    open_task_count: int
    completed_task_count: int


class LifecycleDashboardResponse(BaseModel):
    new_joiners: list[LifecycleEmployeeResponse]
    working: list[LifecycleEmployeeResponse]
    offboarding: list[LifecycleEmployeeResponse]
    completed: list[LifecycleEmployeeResponse]
    pending_tasks: list[LifecycleTaskResponse]

