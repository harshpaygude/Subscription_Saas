"""Public and internal HTTP routes for Lifecycle Service."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unisora_kit import RequestContext, require_admin_role
from app.api.deps import commit_with_outbox, get_current_context, get_lifecycle_service
from app.api.schemas import (
    LifecycleDashboardResponse,
    LifecycleEmployeeResponse,
    LifecycleTaskResponse,
    OffboardingRequest,
    OnboardingRequest,
    TaskCompletionRequest,
)
from app.application.lifecycle_service import LifecycleService
from app.infrastructure.db import get_db

router = APIRouter(tags=["Employee lifecycle"])
internal_router = APIRouter(prefix="/internal", tags=["Internal"])


class EnsureActiveLifecycleRequest(BaseModel):
    user_id: int
    joined_at: date


@router.get("/employee-lifecycle/dashboard", response_model=LifecycleDashboardResponse)
def lifecycle_dashboard(
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    return service.get_dashboard(ctx)


@router.post("/employees/{user_id}/onboarding", response_model=LifecycleEmployeeResponse)
def begin_onboarding(
    user_id: int,
    payload: OnboardingRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    require_admin_role(ctx)
    service.start_onboarding(
        ctx=ctx,
        user_id=user_id,
        department_id=payload.department_id,
        joined_at=payload.joined_at,
        task_specs=[t.model_dump() for t in payload.tasks],
    )
    commit_with_outbox(db)
    return service.get_employee_lifecycle_view(ctx, user_id)


@router.get("/employees/{user_id}/lifecycle", response_model=LifecycleEmployeeResponse)
def employee_lifecycle(
    user_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    return service.get_employee_lifecycle_view(ctx, user_id)


@router.post("/employees/{user_id}/offboarding", response_model=LifecycleEmployeeResponse)
def begin_offboarding(
    user_id: int,
    payload: OffboardingRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    require_admin_role(ctx)
    service.start_offboarding(ctx=ctx, user_id=user_id, last_working_date=payload.last_working_date)
    commit_with_outbox(db)
    return service.get_employee_lifecycle_view(ctx, user_id)


@router.get("/lifecycle-tasks", response_model=list[LifecycleTaskResponse])
def list_lifecycle_tasks(
    status_filter: str | None = None,
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    return service.list_tasks(ctx.organization_id, status_filter=status_filter)


@router.post("/lifecycle-tasks/{task_id}/complete", response_model=LifecycleTaskResponse)
def finish_lifecycle_task(
    task_id: int,
    payload: TaskCompletionRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    require_admin_role(ctx)
    task = service.complete_task(ctx=ctx, task_id=task_id, completion_note=payload.completion_note)
    commit_with_outbox(db)
    return task


@internal_router.post("/lifecycles/ensure-active")
def ensure_active_lifecycle(
    payload: EnsureActiveLifecycleRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LifecycleService = Depends(get_lifecycle_service),
):
    lc = service.ensure_active(
        organization_id=ctx.organization_id, user_id=payload.user_id, joined_at=payload.joined_at
    )
    commit_with_outbox(db)
    return {"id": lc.id, "status": lc.status}
