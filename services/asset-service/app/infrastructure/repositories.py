"""SQLAlchemy repositories for Asset Service."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from unisora_kit import ConflictError
from app.domain.entities import (
    AssetAssignmentEntity,
    AssetEntity,
    AssetMaintenanceEntity,
)
from app.infrastructure.models import Asset, AssetAssignment, AssetMaintenance


def _to_asset(row: Asset) -> AssetEntity:
    return AssetEntity(
        id=row.id,
        organization_id=row.organization_id,
        asset_tag=row.asset_tag,
        asset_type=row.asset_type,
        name=row.name,
        manufacturer=row.manufacturer,
        model=row.model,
        serial_number=row.serial_number,
        purchase_date=row.purchase_date,
        purchase_cost=Decimal(str(row.purchase_cost)) if row.purchase_cost is not None else None,
        currency=row.currency,
        warranty_expiry=row.warranty_expiry,
        status=row.status,
        location=row.location,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_assignment(row: AssetAssignment) -> AssetAssignmentEntity:
    return AssetAssignmentEntity(
        id=row.id,
        organization_id=row.organization_id,
        asset_id=row.asset_id,
        user_id=row.user_id,
        assigned_by=row.assigned_by,
        assigned_at=row.assigned_at,
        expected_return_at=row.expected_return_at,
        returned_at=row.returned_at,
        returned_by=row.returned_by,
        condition_at_issue=row.condition_at_issue,
        condition_at_return=row.condition_at_return,
        handover_notes=row.handover_notes,
        status=row.status,
    )


def _to_maint(row: AssetMaintenance) -> AssetMaintenanceEntity:
    return AssetMaintenanceEntity(
        id=row.id,
        organization_id=row.organization_id,
        asset_id=row.asset_id,
        event_type=row.event_type,
        description=row.description,
        performed_at=row.performed_at,
        cost=Decimal(str(row.cost)) if row.cost is not None else None,
        currency=row.currency,
        performed_by=row.performed_by,
        status=row.status,
        created_at=row.created_at,
    )


class SqlAlchemyAssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, asset: AssetEntity) -> AssetEntity:
        row = Asset(
            organization_id=asset.organization_id,
            asset_tag=asset.asset_tag,
            asset_type=asset.asset_type,
            name=asset.name,
            manufacturer=asset.manufacturer,
            model=asset.model,
            serial_number=asset.serial_number,
            purchase_date=asset.purchase_date,
            purchase_cost=float(asset.purchase_cost) if asset.purchase_cost is not None else None,
            currency=asset.currency,
            warranty_expiry=asset.warranty_expiry,
            status=asset.status,
            location=asset.location,
        )
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("Asset tag already exists in this organization.") from exc
        return _to_asset(row)

    def get_by_id(self, asset_id: int, organization_id: int) -> Optional[AssetEntity]:
        row = self.db.query(Asset).filter(Asset.id == asset_id, Asset.organization_id == organization_id).first()
        return _to_asset(row) if row else None

    def get_by_id_locked(self, asset_id: int, organization_id: int) -> Optional[AssetEntity]:
        row = self.db.query(Asset).filter(Asset.id == asset_id, Asset.organization_id == organization_id).with_for_update().first()
        return _to_asset(row) if row else None

    def get_by_tag(self, asset_tag: str, organization_id: int) -> Optional[AssetEntity]:
        row = self.db.query(Asset).filter(Asset.organization_id == organization_id, Asset.asset_tag == asset_tag).first()
        return _to_asset(row) if row else None

    def list_filtered(self, organization_id: int, *, status: Optional[str] = None, asset_type: Optional[str] = None) -> list[AssetEntity]:
        query = self.db.query(Asset).filter(Asset.organization_id == organization_id)
        if status:
            query = query.filter(Asset.status == status.upper())
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        return [_to_asset(r) for r in query.order_by(Asset.created_at.desc()).all()]

    def list_by_ids(self, organization_id: int, asset_ids: list[int]) -> list[AssetEntity]:
        if not asset_ids:
            return []
        rows = self.db.query(Asset).filter(Asset.id.in_(asset_ids), Asset.organization_id == organization_id).all()
        return [_to_asset(r) for r in rows]

    def save(self, asset: AssetEntity) -> AssetEntity:
        row = self.db.query(Asset).filter(Asset.id == asset.id, Asset.organization_id == asset.organization_id).first()
        if not row:
            raise ValueError("Asset not found")
        row.name = asset.name
        row.asset_type = asset.asset_type
        row.manufacturer = asset.manufacturer
        row.model = asset.model
        row.serial_number = asset.serial_number
        row.purchase_date = asset.purchase_date
        row.purchase_cost = float(asset.purchase_cost) if asset.purchase_cost is not None else None
        row.warranty_expiry = asset.warranty_expiry
        row.location = asset.location
        row.status = asset.status
        self.db.flush()
        return _to_asset(row)


class SqlAlchemyAssetAssignmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_for_asset_locked(self, asset_id: int, organization_id: int) -> Optional[AssetAssignmentEntity]:
        row = (
            self.db.query(AssetAssignment)
            .filter(
                AssetAssignment.asset_id == asset_id,
                AssetAssignment.organization_id == organization_id,
                AssetAssignment.status == "ACTIVE",
            )
            .with_for_update()
            .first()
        )
        return _to_assignment(row) if row else None

    def get_active_by_id(self, assignment_id: int, organization_id: int) -> Optional[AssetAssignmentEntity]:
        row = (
            self.db.query(AssetAssignment)
            .filter(
                AssetAssignment.id == assignment_id,
                AssetAssignment.organization_id == organization_id,
                AssetAssignment.status == "ACTIVE",
            )
            .first()
        )
        return _to_assignment(row) if row else None

    def get_by_id(self, assignment_id: int, organization_id: int) -> Optional[AssetAssignmentEntity]:
        row = (
            self.db.query(AssetAssignment)
            .filter(
                AssetAssignment.id == assignment_id,
                AssetAssignment.organization_id == organization_id,
            )
            .first()
        )
        return _to_assignment(row) if row else None

    def list_by_asset(self, asset_id: int, organization_id: int) -> list[AssetAssignmentEntity]:
        rows = (
            self.db.query(AssetAssignment)
            .filter(AssetAssignment.asset_id == asset_id, AssetAssignment.organization_id == organization_id)
            .order_by(AssetAssignment.assigned_at.desc())
            .all()
        )
        return [_to_assignment(r) for r in rows]

    def list_filtered(self, organization_id: int, *, user_id: Optional[int] = None, status: Optional[str] = None) -> list[AssetAssignmentEntity]:
        query = self.db.query(AssetAssignment).filter(AssetAssignment.organization_id == organization_id)
        if user_id is not None:
            query = query.filter(AssetAssignment.user_id == user_id)
        if status is not None:
            query = query.filter(AssetAssignment.status == status)
        rows = query.order_by(AssetAssignment.assigned_at.desc()).all()
        return [_to_assignment(r) for r in rows]

    def list_active_by_asset_ids(self, asset_ids: list[int], organization_id: int) -> list[AssetAssignmentEntity]:
        if not asset_ids:
            return []
        rows = (
            self.db.query(AssetAssignment)
            .filter(
                AssetAssignment.asset_id.in_(asset_ids),
                AssetAssignment.organization_id == organization_id,
                AssetAssignment.status == "ACTIVE",
            )
            .all()
        )
        return [_to_assignment(r) for r in rows]

    def count_active_by_user(self, organization_id: int) -> dict[int, int]:
        rows = (
            self.db.query(AssetAssignment.user_id, func.count(AssetAssignment.id))
            .filter(AssetAssignment.organization_id == organization_id, AssetAssignment.status == "ACTIVE")
            .group_by(AssetAssignment.user_id)
            .all()
        )
        return {int(uid): int(cnt) for uid, cnt in rows}

    def count_active(self, organization_id: int) -> int:
        return (
            self.db.query(AssetAssignment)
            .filter(AssetAssignment.organization_id == organization_id, AssetAssignment.status == "ACTIVE")
            .count()
        )

    def create(self, assignment: AssetAssignmentEntity) -> AssetAssignmentEntity:
        row = AssetAssignment(
            organization_id=assignment.organization_id,
            asset_id=assignment.asset_id,
            user_id=assignment.user_id,
            assigned_by=assignment.assigned_by,
            expected_return_at=assignment.expected_return_at,
            condition_at_issue=assignment.condition_at_issue,
            handover_notes=assignment.handover_notes,
            status=assignment.status,
        )
        self.db.add(row)
        self.db.flush()
        return _to_assignment(row)

    def save(self, assignment: AssetAssignmentEntity) -> AssetAssignmentEntity:
        row = self.db.query(AssetAssignment).filter(AssetAssignment.id == assignment.id).first()
        if not row:
            raise ValueError("Asset assignment not found")
        row.status = assignment.status
        row.returned_at = assignment.returned_at
        row.returned_by = assignment.returned_by
        row.condition_at_return = assignment.condition_at_return
        row.handover_notes = assignment.handover_notes
        self.db.flush()
        return _to_assignment(row)


class SqlAlchemyAssetMaintenanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, item: AssetMaintenanceEntity) -> AssetMaintenanceEntity:
        row = AssetMaintenance(
            organization_id=item.organization_id,
            asset_id=item.asset_id,
            event_type=item.event_type,
            description=item.description,
            performed_at=item.performed_at,
            cost=float(item.cost) if item.cost is not None else None,
            currency=item.currency,
            performed_by=item.performed_by,
            status=item.status,
        )
        self.db.add(row)
        self.db.flush()
        return _to_maint(row)

    def list_by_asset(self, asset_id: int, organization_id: int) -> list[AssetMaintenanceEntity]:
        rows = (
            self.db.query(AssetMaintenance)
            .filter(AssetMaintenance.asset_id == asset_id, AssetMaintenance.organization_id == organization_id)
            .order_by(AssetMaintenance.performed_at.desc())
            .all()
        )
        return [_to_maint(r) for r in rows]
