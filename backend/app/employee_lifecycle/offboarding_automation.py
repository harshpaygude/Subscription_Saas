from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.models import (
    EmployeeLifecycle,
    LifecycleTask,
    Subscription,
    SubscriptionAssignment,
    Asset,
    AssetAssignment,
    User,
    Department,
    DepartmentMembership,
)
from app.audit.service import record_audit

STANDARD_OFFBOARDING_TASKS = [
    {"task_type": "MANUAL_CHECK", "title": "Deactivate Google Workspace / Microsoft 365 Account", "required": True},
    {"task_type": "MANUAL_CHECK", "title": "Remove from Slack / Teams channels & user groups", "required": True},
    {"task_type": "MANUAL_CHECK", "title": "Revoke VPN credentials, SSH keys & cloud access", "required": True},
    {"task_type": "MANUAL_CHECK", "title": "Complete handover documentation & transfer shared files", "required": True},
    {"task_type": "MANUAL_CHECK", "title": "Collect physical keycard, security badge & parking pass", "required": False},
    {"task_type": "MANUAL_CHECK", "title": "Final payroll & benefits clearance sign-off", "required": False},
]

def generate_smart_offboarding_checklist(
    db: Session,
    actor: User,
    lifecycle: EmployeeLifecycle,
) -> List[LifecycleTask]:
    """Inspects user's assigned SaaS tools, hardware, and administrative requirements,
    and automatically provisions a comprehensive offboarding checklist."""
    created_tasks = []

    # 1. SaaS License Revocations
    active_subs = (
        db.query(SubscriptionAssignment)
        .filter(
            SubscriptionAssignment.user_id == lifecycle.user_id,
            SubscriptionAssignment.organization_id == actor.organization_id,
            SubscriptionAssignment.status == "ACTIVE",
        )
        .all()
    )
    for sub_assign in active_subs:
        sub = db.query(Subscription).filter(Subscription.id == sub_assign.subscription_id).first()
        sub_name = sub.name if sub else f"Subscription #{sub_assign.subscription_id}"
        existing = db.query(LifecycleTask).filter(
            LifecycleTask.lifecycle_id == lifecycle.id,
            LifecycleTask.task_type == "REVOKE_SUBSCRIPTION",
            LifecycleTask.related_subscription_assignment_id == sub_assign.id,
        ).first()
        if not existing:
            task = LifecycleTask(
                organization_id=actor.organization_id,
                lifecycle_id=lifecycle.id,
                task_type="REVOKE_SUBSCRIPTION",
                title=f"Revoke SaaS license: {sub_name}",
                action_status="PENDING",
                required=True,
                related_subscription_id=sub_assign.subscription_id,
                related_subscription_assignment_id=sub_assign.id,
            )
            db.add(task)
            created_tasks.append(task)

    # 2. Asset Returns
    active_assets = (
        db.query(AssetAssignment)
        .filter(
            AssetAssignment.user_id == lifecycle.user_id,
            AssetAssignment.organization_id == actor.organization_id,
            AssetAssignment.status == "ACTIVE",
        )
        .all()
    )
    for asset_assign in active_assets:
        asset = db.query(Asset).filter(Asset.id == asset_assign.asset_id).first()
        asset_label = f"{asset.name} ({asset.asset_tag})" if asset else f"Asset #{asset_assign.asset_id}"
        existing = db.query(LifecycleTask).filter(
            LifecycleTask.lifecycle_id == lifecycle.id,
            LifecycleTask.task_type == "RECOVER_ASSET",
            LifecycleTask.related_asset_assignment_id == asset_assign.id,
        ).first()
        if not existing:
            task = LifecycleTask(
                organization_id=actor.organization_id,
                lifecycle_id=lifecycle.id,
                task_type="RECOVER_ASSET",
                title=f"Recover hardware asset: {asset_label}",
                action_status="PENDING",
                required=True,
                related_asset_id=asset_assign.asset_id,
                related_asset_assignment_id=asset_assign.id,
            )
            db.add(task)
            created_tasks.append(task)

    # 3. Standard Operational & Security Tasks
    for std in STANDARD_OFFBOARDING_TASKS:
        existing = db.query(LifecycleTask).filter(
            LifecycleTask.lifecycle_id == lifecycle.id,
            LifecycleTask.title == std["title"],
        ).first()
        if not existing:
            task = LifecycleTask(
                organization_id=actor.organization_id,
                lifecycle_id=lifecycle.id,
                task_type=std["task_type"],
                title=std["title"],
                action_status="PENDING",
                required=std["required"],
            )
            db.add(task)
            created_tasks.append(task)

    db.commit()
    for t in created_tasks:
        db.refresh(t)

    return (
        db.query(LifecycleTask)
        .filter(LifecycleTask.lifecycle_id == lifecycle.id)
        .order_by(LifecycleTask.required.desc(), LifecycleTask.id.asc())
        .all()
    )

def get_orphan_accounts(db: Session, actor: User) -> List[Dict[str, Any]]:
    """Identifies departures where the employee completed offboarding (or is marked inactive),
    yet orphaned SaaS tool licenses or company hardware assignments remain lingering in the system."""
    completed_lifecycles = (
        db.query(EmployeeLifecycle)
        .filter(
            EmployeeLifecycle.organization_id == actor.organization_id,
            EmployeeLifecycle.status == "COMPLETED",
        )
        .all()
    )

    orphans = []
    today = date.today()

    for lc in completed_lifecycles:
        user = db.query(User).filter(User.id == lc.user_id).first()
        if not user:
            continue

        active_subs = (
            db.query(SubscriptionAssignment)
            .filter(
                SubscriptionAssignment.user_id == user.id,
                SubscriptionAssignment.organization_id == actor.organization_id,
                SubscriptionAssignment.status == "ACTIVE",
            )
            .all()
        )

        active_assets = (
            db.query(AssetAssignment)
            .filter(
                AssetAssignment.user_id == user.id,
                AssetAssignment.organization_id == actor.organization_id,
                AssetAssignment.status == "ACTIVE",
            )
            .all()
        )

        if active_subs or active_assets:
            sub_names = []
            for sa in active_subs:
                s = db.query(Subscription).filter(Subscription.id == sa.subscription_id).first()
                if s:
                    sub_names.append({"id": s.id, "assignment_id": sa.id, "name": s.name, "plan": s.plan or "Standard"})

            asset_names = []
            for aa in active_assets:
                a = db.query(Asset).filter(Asset.id == aa.asset_id).first()
                if a:
                    asset_names.append({"id": a.id, "assignment_id": aa.id, "name": a.name, "tag": a.asset_tag})

            completion_date = lc.completed_at.date() if lc.completed_at else (lc.last_working_date or today)
            days_since = (today - completion_date).days

            orphans.append({
                "lifecycle_id": lc.id,
                "user_id": user.id,
                "name": user.display_name or user.email,
                "email": user.email,
                "completed_at": completion_date.isoformat(),
                "days_since_offboarding": max(0, days_since),
                "active_subscriptions": sub_names,
                "active_assets": asset_names,
                "total_retained_items": len(sub_names) + len(asset_names),
            })

    return sorted(orphans, key=lambda x: x["days_since_offboarding"], reverse=True)

def bulk_revoke_orphan_access(db: Session, actor: User, target_user_id: int) -> Dict[str, Any]:
    """One-click instant revocation of all dangling licenses and recovery of assets for an orphan account."""
    user = db.query(User).filter(User.id == target_user_id, User.organization_id == actor.organization_id).first()
    if not user:
        raise ValueError("Employee user not found.")

    subs = (
        db.query(SubscriptionAssignment)
        .filter(
            SubscriptionAssignment.user_id == target_user_id,
            SubscriptionAssignment.organization_id == actor.organization_id,
            SubscriptionAssignment.status == "ACTIVE",
        )
        .all()
    )
    for s in subs:
        s.status = "RELEASED"

    assets = (
        db.query(AssetAssignment)
        .filter(
            AssetAssignment.user_id == target_user_id,
            AssetAssignment.organization_id == actor.organization_id,
            AssetAssignment.status == "ACTIVE",
        )
        .all()
    )
    for a in assets:
        a.status = "RETURNED"

    record_audit(
        db,
        actor,
        "employee.orphan_access_revoked",
        "employee",
        target_user_id,
        {"revoked_subscriptions": len(subs), "returned_assets": len(assets)},
    )
    db.commit()

    return {
        "status": "success",
        "revoked_subscriptions": len(subs),
        "returned_assets": len(assets),
        "message": f"Successfully revoked {len(subs)} SaaS licenses and recovered {len(assets)} hardware assets.",
    }

def get_offboarding_summary(db: Session, actor: User) -> Dict[str, Any]:
    active_count = (
        db.query(EmployeeLifecycle)
        .filter(
            EmployeeLifecycle.organization_id == actor.organization_id,
            EmployeeLifecycle.status == "OFFBOARDING",
        )
        .count()
    )

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    completed_month_count = (
        db.query(EmployeeLifecycle)
        .filter(
            EmployeeLifecycle.organization_id == actor.organization_id,
            EmployeeLifecycle.status == "COMPLETED",
            EmployeeLifecycle.completed_at >= thirty_days_ago,
        )
        .count()
    )

    orphans = get_orphan_accounts(db, actor)

    revoked_count = (
        db.query(LifecycleTask)
        .filter(
            LifecycleTask.organization_id == actor.organization_id,
            LifecycleTask.task_type == "REVOKE_SUBSCRIPTION",
            LifecycleTask.status == "COMPLETED",
        )
        .count()
    )

    return {
        "active_offboardings": active_count,
        "completed_this_month": completed_month_count,
        "orphan_accounts_count": len(orphans),
        "revoked_licenses_total": revoked_count,
    }
