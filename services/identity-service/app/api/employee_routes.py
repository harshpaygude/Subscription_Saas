"""Employee directory routes for Identity Service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, RequestContext, ServiceHttpClient, require_admin_role
from app.api.deps import (
    commit_with_outbox,
    get_current_context,
    get_employee_service,
    get_outbox_dispatcher,
)
from app.api.schemas import EmployeeCreate, EmployeeDetail, EmployeeSummary, EmployeeUpdate
from app.application.employee_bulk_import import process_employee_bulk_import
from app.application.employee_service import EmployeeService
from app.config import settings
from app.infrastructure.adapters import (
    HttpAssetProvisioningAdapter,
    HttpLifecycleProvisioningAdapter,
    HttpSubscriptionProvisioningAdapter,
    OutboxAuditAdapter,
)
from app.infrastructure.db import get_db
from app.infrastructure.repositories import SqlAlchemyDepartmentRepository, SqlAlchemyUserRepository
from app.infrastructure.security import BcryptPasswordHasher

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: EmployeeService = Depends(get_employee_service),
):
    require_admin_role(ctx)
    created = service.create_employee(
        ctx=ctx,
        employee_id=payload.employee_id,
        name=payload.name,
        email=payload.email,
        phone_number=payload.phone_number,
        department_id=payload.department_id,
        joined_at=payload.joined_at,
        asset_ids=payload.asset_ids,
    )
    commit_with_outbox(db)
    return created


@router.get("", response_model=list[EmployeeSummary])
def list_employees(
    ctx: RequestContext = Depends(get_current_context),
    service: EmployeeService = Depends(get_employee_service),
):
    return service.list_employees(ctx)


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(
    employee_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: EmployeeService = Depends(get_employee_service),
):
    return service.get_employee(ctx, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: EmployeeService = Depends(get_employee_service),
):
    require_admin_role(ctx)
    updated = service.update_employee(
        ctx=ctx,
        user_id=employee_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    commit_with_outbox(db)
    return updated


@router.post("/import-csv")
async def import_employees_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    dispatcher: OutboxDispatcher = Depends(get_outbox_dispatcher),
):
    require_admin_role(ctx)
    if not file.filename:
        raise HTTPException(400, "No file uploaded.")
    fname = file.filename.lower()
    if not (fname.endswith(".csv") or fname.endswith(".xlsx") or fname.endswith(".xls")):
        raise HTTPException(400, "Invalid file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File exceeds maximum size limit of 15 MB.")

    def _c(url: str) -> ServiceHttpClient:
        return ServiceHttpClient(base_url=url, caller_service=settings.service_name, internal_secret=settings.internal_service_secret)

    try:
        result = process_employee_bulk_import(
            content=content,
            filename=file.filename,
            ctx=ctx,
            users=SqlAlchemyUserRepository(db),
            departments=SqlAlchemyDepartmentRepository(db),
            hasher=BcryptPasswordHasher(),
            lifecycle_port=HttpLifecycleProvisioningAdapter(_c(settings.lifecycle_service_url)),
            asset_port=HttpAssetProvisioningAdapter(_c(settings.asset_service_url)),
            subscription_port=HttpSubscriptionProvisioningAdapter(_c(settings.subscription_service_url)),
            audit=OutboxAuditAdapter(db, dispatcher),
        )
        commit_with_outbox(db)
        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Failed to import employee file: {exc}") from exc
