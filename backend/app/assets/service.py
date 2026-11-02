from datetime import datetime

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.models import Asset, AssetAssignment, AssetMaintenance, User


def get_asset(db: Session, actor: User, asset_id: int) -> Asset | None:
    return db.query(Asset).filter(Asset.id == asset_id, Asset.organization_id == actor.organization_id).first()


def assign_asset(db: Session, actor: User, asset: Asset, user_id: int, **values) -> AssetAssignment:
    employee = db.query(User).filter(User.id == user_id, User.organization_id == actor.organization_id).first()
    if not employee:
        raise ValueError("Employee not found in this organization.")
    active = db.query(AssetAssignment).filter(
        AssetAssignment.asset_id == asset.id,
        AssetAssignment.organization_id == actor.organization_id,
        AssetAssignment.status == "ACTIVE",
    ).with_for_update().first()
    if active:
        raise ValueError("Asset is already assigned. Return it before reassigning.")
    if asset.status in {"RETIRED", "LOST", "UNDER_MAINTENANCE"}:
        raise ValueError(f"Asset cannot be assigned while it is {asset.status.lower().replace('_', ' ')}.")
    assignment = AssetAssignment(
        organization_id=actor.organization_id,
        asset_id=asset.id,
        user_id=user_id,
        assigned_by=actor.id,
        **values,
    )
    asset.status = "ASSIGNED"
    db.add(assignment)
    db.flush()
    record_audit(db, actor, "asset.assigned", "asset", asset.id, {"user_id": user_id, "assignment_id": assignment.id})
    return assignment


def return_asset(db: Session, actor: User, assignment: AssetAssignment, condition_at_return: str | None, handover_notes: str | None) -> AssetAssignment:
    assignment.status = "RETURNED"
    assignment.returned_at = datetime.utcnow()
    assignment.returned_by = actor.id
    assignment.condition_at_return = condition_at_return
    if handover_notes:
        assignment.handover_notes = handover_notes
    asset = db.query(Asset).filter(Asset.id == assignment.asset_id, Asset.organization_id == actor.organization_id).with_for_update().first()
    if asset:
        asset.status = "AVAILABLE"
    record_audit(db, actor, "asset.returned", "asset", assignment.asset_id, {"assignment_id": assignment.id})
    return assignment


def add_maintenance(db: Session, actor: User, asset: Asset, values: dict) -> AssetMaintenance:
    item = AssetMaintenance(organization_id=actor.organization_id, asset_id=asset.id, performed_by=actor.id, **values)
    db.add(item)
    asset.status = "UNDER_MAINTENANCE" if values.get("status") in {"OPEN", "IN_PROGRESS"} else asset.status
    db.flush()
    record_audit(db, actor, "asset.maintenance.created", "asset", asset.id, {"maintenance_id": item.id})
    return item

