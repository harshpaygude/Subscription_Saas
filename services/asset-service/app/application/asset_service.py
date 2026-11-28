"""Application service for IT Assets, Custody Assignments, and Maintenance (DIP)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from unisora_kit import ConflictError, NotFoundError, RequestContext
from app.domain.entities import (
    UNASSIGNABLE_STATUSES,
    AssetAssignmentEntity,
    AssetEntity,
    AssetMaintenanceEntity,
)
from app.domain.ports import (
    AssetAssignmentRepository,
    AssetMaintenanceRepository,
    AssetRepository,
    AuditEventPort,
    IdentityLookupPort,
)


class AssetService:
    def __init__(
        self,
        assets: AssetRepository,
        assignments: AssetAssignmentRepository,
        maintenance: AssetMaintenanceRepository,
        identity_lookup: IdentityLookupPort,
        audit: AuditEventPort,
    ):
        self.assets = assets
        self.assignments = assignments
        self.maintenance = maintenance
        self.identity_lookup = identity_lookup
        self.audit = audit

    def list_assets(
        self, organization_id: int, *, status: Optional[str] = None, asset_type: Optional[str] = None
    ) -> list[AssetEntity]:
        return self.assets.list_filtered(organization_id, status=status, asset_type=asset_type)

    def create_asset(self, *, organization_id: int, actor_id: int, data: dict[str, Any]) -> AssetEntity:
        now = datetime.utcnow()
        created = self.assets.create(
            AssetEntity(
                id=None,
                organization_id=organization_id,
                asset_tag=data["asset_tag"],
                asset_type=data["asset_type"],
                name=data["name"],
                manufacturer=data.get("manufacturer"),
                model=data.get("model"),
                serial_number=data.get("serial_number"),
                purchase_date=data.get("purchase_date"),
                purchase_cost=data.get("purchase_cost"),
                currency=data.get("currency", "USD"),
                warranty_expiry=data.get("warranty_expiry"),
                status="AVAILABLE",
                location=data.get("location"),
                created_at=now,
                updated_at=now,
            )
        )
        assert created.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="asset.created",
            entity_type="asset",
            entity_id=created.id,
        )
        return created

    def get_asset(self, organization_id: int, asset_id: int) -> AssetEntity:
        asset = self.assets.get_by_id(asset_id, organization_id)
        if not asset:
            raise NotFoundError("Asset not found.")
        return asset

    def update_asset(self, *, organization_id: int, asset_id: int, updates: dict[str, Any]) -> AssetEntity:
        asset = self.get_asset(organization_id, asset_id)
        for key, value in updates.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        return self.assets.save(asset)

    def assign_asset(
        self,
        *,
        ctx: RequestContext,
        asset_id: int,
        user_id: int,
        expected_return_at: Optional[date] = None,
        condition_at_issue: Optional[str] = None,
        handover_notes: Optional[str] = None,
    ) -> AssetAssignmentEntity:
        asset = self.get_asset(ctx.organization_id, asset_id)
        if not self.identity_lookup.user_exists_in_org(ctx, user_id):
            raise ConflictError("Employee not found in this organization.")

        active = self.assignments.get_active_for_asset_locked(asset_id, ctx.organization_id)
        if active:
            raise ConflictError("Asset is already assigned. Return it before reassigning.")
        if asset.status in UNASSIGNABLE_STATUSES:
            raise ConflictError(
                f"Asset cannot be assigned while it is {asset.status.lower().replace('_', ' ')}."
            )

        assignment = self.assignments.create(
            AssetAssignmentEntity(
                id=None,
                organization_id=ctx.organization_id,
                asset_id=asset_id,
                user_id=user_id,
                assigned_by=ctx.user_id,
                assigned_at=datetime.utcnow(),
                expected_return_at=expected_return_at,
                returned_at=None,
                returned_by=None,
                condition_at_issue=condition_at_issue,
                condition_at_return=None,
                handover_notes=handover_notes,
                status="ACTIVE",
            )
        )
        asset.status = "ASSIGNED"
        self.assets.save(asset)
        assert assignment.id is not None
        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="asset.assigned",
            entity_type="asset",
            entity_id=asset_id,
            details={"user_id": user_id, "assignment_id": assignment.id},
        )
        return assignment

    def list_assignments_with_users(
        self, *, ctx: RequestContext, asset_id: int
    ) -> list[dict[str, Any]]:
        self.get_asset(ctx.organization_id, asset_id)
        assignments = self.assignments.list_by_asset(asset_id, ctx.organization_id)
        user_map = {u["id"]: u for u in self.identity_lookup.list_org_users(ctx)}
        result = []
        for a in assignments:
            u = user_map.get(a.user_id)
            result.append(
                {
                    **a.__dict__,
                    "user_name": u.get("display_name") if u else None,
                    "user_email": u.get("email") if u else None,
                    "user_employee_id": u.get("employee_id") if u else None,
                }
            )
        return result

    def return_asset(
        self,
        *,
        ctx: RequestContext,
        assignment_id: int,
        condition_at_return: Optional[str],
        handover_notes: Optional[str],
    ) -> AssetAssignmentEntity:
        assignment = self.assignments.get_active_by_id(assignment_id, ctx.organization_id)
        if not assignment:
            raise NotFoundError("Active asset assignment not found.")
        assignment.status = "RETURNED"
        assignment.returned_at = datetime.utcnow()
        assignment.returned_by = ctx.user_id
        assignment.condition_at_return = condition_at_return
        if handover_notes:
            assignment.handover_notes = handover_notes
        saved = self.assignments.save(assignment)

        asset = self.assets.get_by_id_locked(assignment.asset_id, ctx.organization_id)
        if asset:
            asset.status = "AVAILABLE"
            self.assets.save(asset)

        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="asset.returned",
            entity_type="asset",
            entity_id=assignment.asset_id,
            details={"assignment_id": assignment.id},
        )
        return saved

    def add_maintenance(
        self, *, ctx: RequestContext, asset_id: int, data: dict[str, Any]
    ) -> AssetMaintenanceEntity:
        asset = self.get_asset(ctx.organization_id, asset_id)
        item = self.maintenance.create(
            AssetMaintenanceEntity(
                id=None,
                organization_id=ctx.organization_id,
                asset_id=asset_id,
                event_type=data["event_type"],
                description=data["description"],
                performed_at=data.get("performed_at") or date.today(),
                cost=data.get("cost"),
                currency=data.get("currency", "USD"),
                performed_by=ctx.user_id,
                status=data.get("status", "COMPLETED"),
                created_at=datetime.utcnow(),
            )
        )
        if data.get("status") in {"OPEN", "IN_PROGRESS"}:
            asset.status = "UNDER_MAINTENANCE"
            self.assets.save(asset)
        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="asset.maintenance.created",
            entity_type="asset",
            entity_id=asset_id,
            details={"maintenance_id": item.id},
        )
        return item

    def list_maintenance(self, *, organization_id: int, asset_id: int) -> list[AssetMaintenanceEntity]:
        self.get_asset(organization_id, asset_id)
        return self.maintenance.list_by_asset(asset_id, organization_id)
