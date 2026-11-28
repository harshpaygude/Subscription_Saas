"""Department routes for Identity Service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from unisora_kit import RequestContext, require_admin_role
from app.api.deps import commit_with_outbox, get_current_context, get_department_service
from app.api.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    MembershipCreate,
    MembershipResponse,
)
from app.application.department_service import DepartmentService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    ctx: RequestContext = Depends(get_current_context),
    service: DepartmentService = Depends(get_department_service),
):
    return service.list_departments(ctx.organization_id)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: DepartmentService = Depends(get_department_service),
):
    require_admin_role(ctx)
    item = service.create_department(
        organization_id=ctx.organization_id,
        actor_id=ctx.user_id,
        name=payload.name,
        description=payload.description,
    )
    commit_with_outbox(db)
    return item


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: DepartmentService = Depends(get_department_service),
):
    require_admin_role(ctx)
    item = service.update_department(
        organization_id=ctx.organization_id,
        actor_id=ctx.user_id,
        department_id=department_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    commit_with_outbox(db)
    return item


@router.post("/{department_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership(
    department_id: int,
    payload: MembershipCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: DepartmentService = Depends(get_department_service),
):
    require_admin_role(ctx)
    membership, email, display_name = service.add_membership(
        organization_id=ctx.organization_id,
        actor_id=ctx.user_id,
        department_id=department_id,
        user_id=payload.user_id,
        effective_from=payload.effective_from,
    )
    commit_with_outbox(db)
    return MembershipResponse(
        id=membership.id or 0,
        organization_id=membership.organization_id,
        department_id=membership.department_id,
        user_id=membership.user_id,
        is_active=membership.is_active,
        effective_from=membership.effective_from,
        effective_to=membership.effective_to,
        created_at=membership.created_at,
        email=email,
        display_name=display_name,
    )


@router.get("/{department_id}/members", response_model=list[MembershipResponse])
def list_members(
    department_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: DepartmentService = Depends(get_department_service),
):
    rows = service.list_memberships(organization_id=ctx.organization_id, department_id=department_id)
    return [
        MembershipResponse(
            id=m.id or 0,
            organization_id=m.organization_id,
            department_id=m.department_id,
            user_id=m.user_id,
            is_active=m.is_active,
            effective_from=m.effective_from,
            effective_to=m.effective_to,
            created_at=m.created_at,
            email=email,
            display_name=display_name,
        )
        for m, email, display_name in rows
    ]
