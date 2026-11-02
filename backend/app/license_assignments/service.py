from datetime import datetime

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.models import Subscription, SubscriptionAssignment, SubscriptionLicense, User


def assign_license(db: Session, actor: User, subscription: Subscription, license_item: SubscriptionLicense | None, values: dict) -> SubscriptionAssignment:
    employee = db.query(User).filter(User.id == values["user_id"], User.organization_id == actor.organization_id).first()
    if not employee:
        raise ValueError("Employee not found in this organization.")
    if license_item:
        if license_item.organization_id != actor.organization_id or license_item.subscription_id != subscription.id:
            raise ValueError("License does not belong to this subscription.")
        if license_item.status != "ACTIVE":
            raise ValueError("License is not active.")
        active_count = db.query(SubscriptionAssignment).filter(
            SubscriptionAssignment.license_id == license_item.id,
            SubscriptionAssignment.status == "ACTIVE",
        ).with_for_update().count()
        if active_count >= license_item.capacity:
            raise ValueError("License capacity has been reached.")
    else:
        # Pooled access is allowed only when the caller explicitly creates a
        # capacity-bearing license; unmodelled seats must not be over-allocated.
        raise ValueError("An active license is required for assignment.")
    duplicate = db.query(SubscriptionAssignment).filter(
        SubscriptionAssignment.organization_id == actor.organization_id,
        SubscriptionAssignment.subscription_id == subscription.id,
        SubscriptionAssignment.user_id == values["user_id"],
        SubscriptionAssignment.status == "ACTIVE",
    ).first()
    if duplicate:
        raise ValueError("Employee already has an active assignment for this subscription.")
    assignment = SubscriptionAssignment(
        organization_id=actor.organization_id,
        subscription_id=subscription.id,
        license_id=license_item.id,
        assigned_by=actor.id,
        **values,
    )
    db.add(assignment)
    db.flush()
    record_audit(db, actor, "subscription.license.assigned", "subscription_assignment", assignment.id, {"user_id": employee.id, "license_id": license_item.id})
    return assignment


def release_license(db: Session, actor: User, assignment: SubscriptionAssignment) -> SubscriptionAssignment:
    assignment.status = "RELEASED"
    assignment.released_at = datetime.utcnow()
    record_audit(db, actor, "subscription.license.released", "subscription_assignment", assignment.id)
    return assignment

