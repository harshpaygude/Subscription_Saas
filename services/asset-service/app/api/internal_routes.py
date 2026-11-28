"""Internal service-to-service endpoints for Asset Service."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import commit_with_outbox, get_current_context
from app.domain.entities import AssetAssignmentEntity, AssetEntity
from app.infrastructure.db import get_db
from app.infrastructure.repositories import SqlAlchemyAssetAssignmentRepository, SqlAlchemyAssetRepository

router = APIRouter(prefix="/internal", tags=["Internal"])


class ValidateAssetsRequest(BaseModel):
    asset_ids: list[int]


class BulkAssignAssetsRequest(BaseModel):
    user_id: int
    asset_ids: list[int]
    reassign: bool = False


class OnboardingAssetsRequest(BaseModel):
    assets: list[dict[str, Any]]
    user_lookup: dict[str, int] = {}


@router.get("/assets/summary")
def asset_summary(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    all_assets = SqlAlchemyAssetRepository(db).list_filtered(ctx.organization_id)
    active_assignments = SqlAlchemyAssetAssignmentRepository(db).count_active(ctx.organization_id)
    return {
        "total": len(all_assets),
        "assigned": active_assignments,
        "available": sum(a.status == "AVAILABLE" for a in all_assets),
    }


@router.get("/assets/{asset_id}")
def get_internal_asset(
    asset_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    asset = SqlAlchemyAssetRepository(db).get_by_id(asset_id, ctx.organization_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return {"id": asset.id, "name": asset.name, "asset_tag": asset.asset_tag, "asset_type": asset.asset_type, "status": asset.status}


@router.get("/assignments/active-counts")
def active_assignment_counts(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return {"counts": SqlAlchemyAssetAssignmentRepository(db).count_active_by_user(ctx.organization_id)}


@router.get("/assignments")
def list_internal_assignments(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    rows = SqlAlchemyAssetAssignmentRepository(db).list_filtered(ctx.organization_id, user_id=user_id, status=status)
    assets = {a.id: a for a in SqlAlchemyAssetRepository(db).list_filtered(ctx.organization_id)}
    return [
        {
            "id": r.id,
            "asset_id": r.asset_id,
            "user_id": r.user_id,
            "status": r.status,
            "assigned_at": r.assigned_at.isoformat(),
            "returned_at": r.returned_at.isoformat() if r.returned_at else None,
            "resource_name": f"{assets[r.asset_id].name} ({assets[r.asset_id].asset_tag})" if r.asset_id in assets else None,
            "resource_provider": assets[r.asset_id].asset_type if r.asset_id in assets else None,
        }
        for r in rows
    ]


@router.get("/assignments/{assignment_id}")
def get_internal_assignment(
    assignment_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    row = SqlAlchemyAssetAssignmentRepository(db).get_by_id(assignment_id, ctx.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="Asset assignment not found.")
    asset = SqlAlchemyAssetRepository(db).get_by_id(row.asset_id, ctx.organization_id)
    return {
        "id": row.id,
        "asset_id": row.asset_id,
        "user_id": row.user_id,
        "status": row.status,
        "asset_name": asset.name if asset else None,
        "asset_tag": asset.asset_tag if asset else None,
    }


@router.post("/assets/validate-available")
def validate_available_assets(
    payload: ValidateAssetsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    assets = SqlAlchemyAssetRepository(db).list_by_ids(ctx.organization_id, payload.asset_ids)
    if len(assets) != len(set(payload.asset_ids)):
        raise HTTPException(status_code=400, detail="One or more selected assets were not found in this organization.")
    assigned = SqlAlchemyAssetAssignmentRepository(db).list_active_by_asset_ids(payload.asset_ids, ctx.organization_id)
    if assigned:
        raise HTTPException(status_code=409, detail="One or more selected assets are already assigned.")
    return {"asset_ids": [a.id for a in assets]}


@router.post("/assets/bulk-assign")
def bulk_assign_assets(
    payload: BulkAssignAssetsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    assets_repo = SqlAlchemyAssetRepository(db)
    assign_repo = SqlAlchemyAssetAssignmentRepository(db)
    now = datetime.utcnow()
    for asset_id in payload.asset_ids:
        asset = assets_repo.get_by_id(asset_id, ctx.organization_id)
        if not asset or asset.id is None:
            continue
        existing = assign_repo.get_active_for_asset_locked(asset.id, ctx.organization_id)
        if existing:
            if not payload.reassign or existing.user_id == payload.user_id:
                continue
            existing.status = "RETURNED"
            existing.returned_at = now
            assign_repo.save(existing)
        assign_repo.create(
            AssetAssignmentEntity(
                id=None,
                organization_id=ctx.organization_id,
                asset_id=asset.id,
                user_id=payload.user_id,
                assigned_by=ctx.user_id,
                assigned_at=now,
                expected_return_at=None,
                returned_at=None,
                returned_by=None,
                condition_at_issue=None,
                condition_at_return=None,
                handover_notes=None,
                status="ACTIVE",
            )
        )
        asset.status = "ASSIGNED"
        assets_repo.save(asset)
    commit_with_outbox(db)
    return {"status": "ok"}


@router.post("/assets/onboarding-import")
def onboarding_import_assets(
    payload: OnboardingAssetsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    assets_repo = SqlAlchemyAssetRepository(db)
    assign_repo = SqlAlchemyAssetAssignmentRepository(db)
    created = 0
    assigned = 0
    now = datetime.utcnow()

    for asset_in in payload.assets:
        tag = str(asset_in.get("asset_tag") or "").strip()
        if not tag:
            continue
        existing = assets_repo.get_by_tag(tag, ctx.organization_id)
        if not existing:
            cost_val = None
            if asset_in.get("purchase_cost"):
                try:
                    cost_val = Decimal(str(asset_in["purchase_cost"]).replace("$", "").replace(",", "").strip())
                except Exception:
                    pass
            existing = assets_repo.create(
                AssetEntity(
                    id=None,
                    organization_id=ctx.organization_id,
                    asset_tag=tag,
                    asset_type=str(asset_in.get("asset_type") or "Laptop").strip(),
                    name=str(asset_in.get("name") or tag).strip(),
                    manufacturer=str(asset_in.get("manufacturer")).strip() if asset_in.get("manufacturer") else None,
                    model=str(asset_in.get("model")).strip() if asset_in.get("model") else None,
                    serial_number=str(asset_in.get("serial_number")).strip() if asset_in.get("serial_number") else None,
                    purchase_date=None,
                    purchase_cost=cost_val,
                    currency=str(asset_in.get("currency") or "USD").strip().upper()[:3],
                    warranty_expiry=None,
                    status="AVAILABLE",
                    location=str(asset_in.get("location")).strip() if asset_in.get("location") else None,
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1

        assigned_to = str(asset_in.get("assigned_to") or "").strip().lower()
        if assigned_to and existing.id is not None:
            uid = payload.user_lookup.get(assigned_to)
            if uid is not None and not assign_repo.get_active_for_asset_locked(existing.id, ctx.organization_id):
                assign_repo.create(
                    AssetAssignmentEntity(
                        id=None,
                        organization_id=ctx.organization_id,
                        asset_id=existing.id,
                        user_id=uid,
                        assigned_by=ctx.user_id,
                        assigned_at=now,
                        expected_return_at=None,
                        returned_at=None,
                        returned_by=None,
                        condition_at_issue=None,
                        condition_at_return=None,
                        handover_notes="Imported via initial company onboarding Excel",
                        status="ACTIVE",
                    )
                )
                existing.status = "ASSIGNED"
                assets_repo.save(existing)
                assigned += 1

    commit_with_outbox(db)
    return {"created": created, "assigned": assigned}
