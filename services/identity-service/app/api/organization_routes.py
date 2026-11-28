"""Organization and onboarding routes for Identity Service."""
from __future__ import annotations

import io
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from unisora_kit import RequestContext, require_admin_role
from app.api.deps import commit_with_outbox, get_current_context, get_organization_service
from app.api.schemas import (
    OnboardingSubmit,
    OrganizationCreate,
    OrganizationProfileUpdate,
    OrganizationResponse,
)
from app.application.excel_import import generate_onboarding_excel_template, parse_excel_workbook
from app.application.organization_service import OrganizationService
from app.infrastructure.db import get_db

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def register_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    service: OrganizationService = Depends(get_organization_service),
):
    org = service.create_organization(payload.name)
    commit_with_outbox(db)
    return org


@router.get("/me", response_model=OrganizationResponse)
def get_current_user_organization(
    ctx: RequestContext = Depends(get_current_context),
    service: OrganizationService = Depends(get_organization_service),
):
    return service.get_organization(ctx.organization_id)


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization_by_id(
    organization_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: OrganizationService = Depends(get_organization_service),
):
    return service.get_organization(organization_id, caller_org_id=ctx.organization_id)


@router.get("/me/onboarding-status", response_model=dict)
async def get_onboarding_status(
    ctx: RequestContext = Depends(get_current_context),
    service: OrganizationService = Depends(get_organization_service),
):
    org = service.get_organization(ctx.organization_id)
    return {
        "organization_id": org.id,
        "organization_name": org.name,
        "onboarding_completed": bool(org.onboarding_completed),
        "onboarding_completed_at": org.onboarding_completed_at.isoformat() if org.onboarding_completed_at else None,
    }


@router.patch("/me/profile", response_model=OrganizationResponse)
async def update_organization_profile(
    payload: OrganizationProfileUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: OrganizationService = Depends(get_organization_service),
):
    org = service.update_profile(ctx.organization_id, payload.model_dump(exclude_unset=True))
    commit_with_outbox(db)
    return org


@router.post("/me/onboarding", response_model=OrganizationResponse)
async def submit_onboarding(
    payload: OnboardingSubmit,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: OrganizationService = Depends(get_organization_service),
):
    require_admin_role(ctx)
    org = service.submit_onboarding(
        ctx=ctx,
        company_updates=payload.company.model_dump(exclude_unset=True),
        departments_input=[d.model_dump() for d in payload.departments],
        employees_input=[e.model_dump() for e in payload.employees],
        assets_input=[a.model_dump() for a in payload.assets],
        subscriptions_input=[s.model_dump() for s in payload.subscriptions],
        integrations_input=[i.model_dump() for i in payload.integrations],
    )
    commit_with_outbox(db)
    return org


@router.post("/me/onboarding/parse-excel", response_model=dict)
async def parse_onboarding_excel(
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_current_context),
):
    del ctx
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    preview = parse_excel_workbook(content)
    return {
        "valid": preview.valid,
        "company": preview.company.__dict__ if preview.company else None,
        "departments": [{"name": d.name, "description": d.description} for d in preview.departments],
        "employees": [e.__dict__ for e in preview.employees],
        "assets": [a.__dict__ for a in preview.assets],
        "subscriptions": [s.__dict__ for s in preview.subscriptions],
        "integrations": [i.__dict__ for i in preview.integrations],
        "errors": preview.errors,
        "warnings": preview.warnings,
        "department_count": len(preview.departments),
        "employee_count": len(preview.employees),
        "asset_count": len(preview.assets),
        "subscription_count": len(preview.subscriptions),
        "integration_count": len(preview.integrations),
    }


@router.get("/me/onboarding/excel-template")
async def download_excel_template(ctx: RequestContext = Depends(get_current_context)):
    del ctx
    try:
        data = generate_onboarding_excel_template()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=unisora_onboarding_template.xlsx"},
    )
