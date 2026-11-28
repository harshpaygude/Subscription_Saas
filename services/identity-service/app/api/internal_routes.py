"""Internal service-to-service endpoints exposed by Identity Service."""
from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import commit_with_outbox, get_current_context
from app.domain.entities import UserEntity
from app.infrastructure.db import get_db
from app.infrastructure.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.security import BcryptPasswordHasher

router = APIRouter(prefix="/internal", tags=["Internal"])


class ProvisionUserRequest(BaseModel):
    email: str
    display_name: Optional[str] = None
    employee_id: Optional[str] = None


class DeactivateMembershipsRequest(BaseModel):
    user_id: int
    effective_to: date


class ActivateMembershipRequest(BaseModel):
    user_id: int
    department_id: int
    effective_from: date


@router.get("/users")
def list_org_users(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    users = SqlAlchemyUserRepository(db).list_by_org(ctx.organization_id)
    depts = SqlAlchemyDepartmentRepository(db)
    return [
        {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "employee_id": u.employee_id,
            "phone_number": u.phone_number,
            "role": u.role,
            "department_ids": [m.department_id for m in depts.list_active_memberships_by_user(u.id or 0, ctx.organization_id)],
        }
        for u in users
    ]


@router.get("/users/{user_id}")
def get_org_user(
    user_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    u = SqlAlchemyUserRepository(db).get_by_id_in_org(user_id, ctx.organization_id)
    if not u:
        raise HTTPException(status_code=404, detail="Employee not found in this organization.")
    depts = SqlAlchemyDepartmentRepository(db)
    return {
        "id": u.id,
        "email": u.email,
        "display_name": u.display_name,
        "employee_id": u.employee_id,
        "phone_number": u.phone_number,
        "role": u.role,
        "organization_id": u.organization_id,
        "department_ids": [m.department_id for m in depts.list_active_memberships_by_user(u.id or 0, ctx.organization_id)],
    }


@router.post("/users/provision")
def provision_org_user(
    payload: ProvisionUserRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    users = SqlAlchemyUserRepository(db)
    email = payload.email.strip().lower()
    existing = users.get_by_email_in_org(email, ctx.organization_id)
    if not existing and payload.employee_id:
        existing = users.get_by_employee_id_in_org(payload.employee_id, ctx.organization_id)
    if existing:
        return {"id": existing.id, "email": existing.email, "display_name": existing.display_name, "employee_id": existing.employee_id}

    candidate = email
    if users.get_by_email(candidate):
        local, domain = email.split("@", 1) if "@" in email else (email, "workspace.internal")
        candidate = f"{local}+{ctx.organization_id}@{domain}"
        suffix = 1
        while users.get_by_email(candidate):
            candidate = f"{local}+{ctx.organization_id}.{suffix}@{domain}"
            suffix += 1
    created = users.create(
        UserEntity(
            id=None,
            email=candidate,
            display_name=payload.display_name or candidate.split("@")[0],
            employee_id=payload.employee_id,
            password_hash=BcryptPasswordHasher().hash(secrets.token_urlsafe(24)),
            organization_id=ctx.organization_id,
            role="MEMBER",
            created_at=datetime.utcnow(),
        )
    )
    commit_with_outbox(db)
    return {"id": created.id, "email": created.email, "display_name": created.display_name, "employee_id": created.employee_id}


@router.get("/organizations/{organization_id}")
def get_internal_org(
    organization_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    if ctx.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    org = SqlAlchemyOrganizationRepository(db).get_by_id(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"id": org.id, "name": org.name}


@router.get("/departments")
def list_internal_departments(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    depts = SqlAlchemyDepartmentRepository(db).list_by_org(ctx.organization_id)
    return [{"id": d.id, "name": d.name, "is_active": d.is_active} for d in depts]


@router.post("/departments/sync-onboarding-membership")
def sync_onboarding_membership(
    payload: ActivateMembershipRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    depts = SqlAlchemyDepartmentRepository(db)
    dept = depts.get_by_id(payload.department_id, ctx.organization_id)
    if not dept or not dept.is_active:
        raise HTTPException(status_code=400, detail="Active department not found in this organization.")
    depts.deactivate_user_memberships(payload.user_id, ctx.organization_id, payload.effective_from)
    depts.ensure_active_membership(ctx.organization_id, payload.department_id, payload.user_id, payload.effective_from)
    commit_with_outbox(db)
    return {"status": "ok"}


@router.post("/departments/deactivate-memberships")
def deactivate_memberships(
    payload: DeactivateMembershipsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    SqlAlchemyDepartmentRepository(db).deactivate_user_memberships(
        payload.user_id, ctx.organization_id, payload.effective_to
    )
    commit_with_outbox(db)
    return {"status": "ok"}
