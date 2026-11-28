"""Public HTTP routes for Asset Service."""
from __future__ import annotations

import io
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, RequestContext, require_admin_role
from app.api.deps import (
    commit_with_outbox,
    get_asset_service,
    get_current_context,
    get_identity_adapter,
    get_outbox_dispatcher,
)
from app.api.schemas import (
    AssetAssignmentCreate,
    AssetAssignmentResponse,
    AssetAssignmentReturn,
    AssetBulkImportResponse,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    MaintenanceCreate,
    MaintenanceResponse,
)
from app.application.asset_bulk_import import (
    generate_sample_asset_csv,
    generate_sample_asset_excel,
    process_asset_bulk_import,
)
from app.application.asset_service import AssetService
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import get_db
from app.infrastructure.repositories import SqlAlchemyAssetAssignmentRepository, SqlAlchemyAssetRepository

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=list[AssetResponse])
def list_assets(
    status_filter: str | None = Query(default=None, alias="status"),
    asset_type: str | None = None,
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    return service.list_assets(ctx.organization_id, status=status_filter, asset_type=asset_type)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    require_admin_role(ctx)
    item = service.create_asset(organization_id=ctx.organization_id, actor_id=ctx.user_id, data=payload.model_dump())
    commit_with_outbox(db)
    return item


@router.post("/import-csv", response_model=AssetBulkImportResponse)
@router.post("/import", response_model=AssetBulkImportResponse)
async def import_assets_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    dispatcher: OutboxDispatcher = Depends(get_outbox_dispatcher),
):
    require_admin_role(ctx)
    if not file.filename:
        raise HTTPException(400, "A valid file is required.")
    fname = file.filename.lower()
    if not (fname.endswith(".csv") or fname.endswith(".xlsx") or fname.endswith(".xls")):
        raise HTTPException(400, "Only CSV (.csv) and Excel (.xlsx, .xls) files are supported.")
    try:
        content = await file.read()
        result = process_asset_bulk_import(
            content=content,
            filename=file.filename,
            ctx=ctx,
            assets=SqlAlchemyAssetRepository(db),
            assignments=SqlAlchemyAssetAssignmentRepository(db),
            identity_lookup=get_identity_adapter(),
            audit=OutboxAuditAdapter(db, dispatcher),
        )
        commit_with_outbox(db)
        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Failed to import IT asset file: {exc}") from exc


@router.get("/sample-template")
def download_asset_sample_template(format: str = Query("csv", pattern="^(csv|excel|xlsx)$")):
    fmt = format.lower()
    if fmt in ("excel", "xlsx"):
        excel_bytes = generate_sample_asset_excel()
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=unisora_it_assets_sample_template.xlsx"},
        )
    return Response(
        content=generate_sample_asset_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=unisora_it_assets_sample_template.csv"},
    )


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_route(
    asset_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    return service.get_asset(ctx.organization_id, asset_id)


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    require_admin_role(ctx)
    item = service.update_asset(
        organization_id=ctx.organization_id,
        asset_id=asset_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    commit_with_outbox(db)
    return item


@router.post("/{asset_id}/assignments", response_model=AssetAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_asset_route(
    asset_id: int,
    payload: AssetAssignmentCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    require_admin_role(ctx)
    assignment = service.assign_asset(
        ctx=ctx,
        asset_id=asset_id,
        user_id=payload.user_id,
        expected_return_at=payload.expected_return_at,
        condition_at_issue=payload.condition_at_issue,
        handover_notes=payload.handover_notes,
    )
    commit_with_outbox(db)
    return assignment


@router.get("/{asset_id}/assignments", response_model=list[AssetAssignmentResponse])
def list_asset_assignments(
    asset_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    return service.list_assignments_with_users(ctx=ctx, asset_id=asset_id)


@router.post("/assignments/{assignment_id}/return", response_model=AssetAssignmentResponse)
def return_asset_route(
    assignment_id: int,
    payload: AssetAssignmentReturn,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    require_admin_role(ctx)
    assignment = service.return_asset(
        ctx=ctx,
        assignment_id=assignment_id,
        condition_at_return=payload.condition_at_return,
        handover_notes=payload.handover_notes,
    )
    commit_with_outbox(db)
    return assignment


@router.post("/{asset_id}/maintenance", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance(
    asset_id: int,
    payload: MaintenanceCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    require_admin_role(ctx)
    item = service.add_maintenance(ctx=ctx, asset_id=asset_id, data=payload.model_dump())
    commit_with_outbox(db)
    return item


@router.get("/{asset_id}/maintenance", response_model=list[MaintenanceResponse])
def list_maintenance(
    asset_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: AssetService = Depends(get_asset_service),
):
    return service.list_maintenance(organization_id=ctx.organization_id, asset_id=asset_id)
