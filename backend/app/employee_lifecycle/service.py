from datetime import datetime

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.models import (
    Asset,
    AssetAssignment,
    Department,
    DepartmentMembership,
    EmployeeLifecycle,
    LifecycleTask,
    Subscription,
    SubscriptionAssignment,
    User,
)


LIFECYCLE_STATUSES = {"ONBOARDING", "ACTIVE", "OFFBOARDING", "COMPLETED"}


def get_lifecycle(db: Session, actor: User, employee_id: int) -> EmployeeLifecycle | None:
    return db.query(EmployeeLifecycle).filter(
        EmployeeLifecycle.id == employee_id,
        EmployeeLifecycle.organization_id == actor.organization_id,
    ).first()


def get_lifecycle_for_user(db: Session, actor: User, user_id: int) -> EmployeeLifecycle | None:
    return db.query(EmployeeLifecycle).filter(
        EmployeeLifecycle.user_id == user_id,
        EmployeeLifecycle.organization_id == actor.organization_id,
    ).first()


def _employee(db: Session, actor: User, user_id: int) -> User:
    employee = db.query(User).filter(User.id == user_id, User.organization_id == actor.organization_id).first()
    if not employee:
        raise ValueError("Employee not found in this organization.")
    return employee


def start_onboarding(db: Session, actor: User, user_id: int, department_id: int, joined_at, task_specs) -> EmployeeLifecycle:
    employee = _employee(db, actor, user_id)
    lifecycle = get_lifecycle_for_user(db, actor, user_id)
    if lifecycle and lifecycle.status == "OFFBOARDING":
        raise ValueError("Cannot start onboarding while offboarding is active.")
    if lifecycle is None:
        lifecycle = EmployeeLifecycle(organization_id=actor.organization_id, user_id=employee.id, status="ONBOARDING", joined_at=joined_at)
        db.add(lifecycle)
        db.flush()
    else:
        lifecycle.status = "ONBOARDING"
        lifecycle.joined_at = joined_at
        lifecycle.last_working_date = None
        lifecycle.completed_at = None

    department = db.query(Department).filter(Department.id == department_id, Department.organization_id == actor.organization_id, Department.is_active.is_(True)).first()
    if not department:
        raise ValueError("Active department not found in this organization.")
    previous = db.query(DepartmentMembership).filter(DepartmentMembership.user_id == employee.id, DepartmentMembership.organization_id == actor.organization_id, DepartmentMembership.is_active.is_(True)).all()
    for membership in previous:
        membership.is_active = False
        membership.effective_to = joined_at
    db.add(DepartmentMembership(organization_id=actor.organization_id, department_id=department.id, user_id=employee.id, effective_from=joined_at))

    for spec in task_specs:
        if spec.task_type == "SUBSCRIPTION_ACCESS":
            if not spec.subscription_id:
                raise ValueError("Subscription access tasks require a subscription.")
            subscription = db.query(Subscription).filter(Subscription.id == spec.subscription_id, Subscription.organization_id == actor.organization_id).first()
            if not subscription:
                raise ValueError("Subscription not found in this organization.")
        if spec.task_type == "ASSET_ISSUE":
            if not spec.asset_id:
                raise ValueError("Asset issue tasks require an asset.")
            asset = db.query(Asset).filter(Asset.id == spec.asset_id, Asset.organization_id == actor.organization_id).first()
            if not asset:
                raise ValueError("Asset not found in this organization.")
        db.add(LifecycleTask(
            organization_id=actor.organization_id,
            lifecycle_id=lifecycle.id,
            task_type=spec.task_type,
            title=spec.title,
            required=spec.required,
            due_at=spec.due_at,
            related_subscription_id=spec.subscription_id,
            related_asset_id=spec.asset_id,
        ))
    db.flush()
    if db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id, LifecycleTask.required.is_(True), LifecycleTask.status == "OPEN").count() == 0:
        lifecycle.status = "ACTIVE"
    record_audit(db, actor, "employee.onboarding.started", "employee_lifecycle", lifecycle.id, {"user_id": employee.id})
    db.flush()
    return lifecycle


def start_offboarding(db: Session, actor: User, lifecycle: EmployeeLifecycle, last_working_date) -> EmployeeLifecycle:
    if lifecycle.status == "COMPLETED":
        raise ValueError("Completed offboarding cannot be restarted.")
    lifecycle.status = "OFFBOARDING"
    lifecycle.last_working_date = last_working_date
    lifecycle.offboarding_initiated_at = datetime.utcnow()
    memberships = db.query(DepartmentMembership).filter(DepartmentMembership.user_id == lifecycle.user_id, DepartmentMembership.organization_id == actor.organization_id, DepartmentMembership.is_active.is_(True)).all()
    for membership in memberships:
        membership.is_active = False
        membership.effective_to = last_working_date

    active_subscriptions = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.user_id == lifecycle.user_id, SubscriptionAssignment.organization_id == actor.organization_id, SubscriptionAssignment.status == "ACTIVE").all()
    for assignment in active_subscriptions:
        exists = db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id, LifecycleTask.task_type == "REVOKE_SUBSCRIPTION", LifecycleTask.related_subscription_assignment_id == assignment.id, LifecycleTask.status == "OPEN").first()
        if not exists:
            db.add(LifecycleTask(organization_id=actor.organization_id, lifecycle_id=lifecycle.id, task_type="REVOKE_SUBSCRIPTION", title="Revoke software access", action_status="PENDING", related_subscription_id=assignment.subscription_id, related_subscription_assignment_id=assignment.id))

    active_assets = db.query(AssetAssignment).filter(AssetAssignment.user_id == lifecycle.user_id, AssetAssignment.organization_id == actor.organization_id, AssetAssignment.status == "ACTIVE").all()
    for assignment in active_assets:
        asset = db.query(Asset).filter(Asset.id == assignment.asset_id).first()
        asset_label = f"{asset.name} ({asset.asset_tag})" if asset else f"Asset #{assignment.asset_id}"
        exists = db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id, LifecycleTask.task_type == "RECOVER_ASSET", LifecycleTask.related_asset_assignment_id == assignment.id, LifecycleTask.status == "OPEN").first()
        if not exists:
            db.add(LifecycleTask(organization_id=actor.organization_id, lifecycle_id=lifecycle.id, task_type="RECOVER_ASSET", title=f"Recover company asset: {asset_label}", action_status="PENDING", related_asset_id=assignment.asset_id, related_asset_assignment_id=assignment.id))
    db.flush()
    if db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id, LifecycleTask.required.is_(True), LifecycleTask.status == "OPEN").count() == 0:
        lifecycle.status = "COMPLETED"
        lifecycle.completed_at = datetime.utcnow()
    record_audit(db, actor, "employee.offboarding.started", "employee_lifecycle", lifecycle.id, {"user_id": lifecycle.user_id, "last_working_date": str(last_working_date)})
    db.flush()
    return lifecycle


def complete_task(db: Session, actor: User, task: LifecycleTask, completion_note: str | None) -> LifecycleTask:
    if task.status == "COMPLETED":
        return task
    if task.task_type == "REVOKE_SUBSCRIPTION":
        assignment = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.id == task.related_subscription_assignment_id, SubscriptionAssignment.organization_id == actor.organization_id).first()
        if not assignment or assignment.status != "RELEASED":
            raise ValueError("Release the subscription assignment before completing this clearance task.")
        task.action_status = "REVOKED"
    elif task.task_type == "RECOVER_ASSET":
        assignment = db.query(AssetAssignment).filter(AssetAssignment.id == task.related_asset_assignment_id, AssetAssignment.organization_id == actor.organization_id).first()
        if not assignment or assignment.status != "RETURNED":
            raise ValueError("Return the asset before completing this clearance task.")
        task.action_status = "RETURNED"
    elif task.task_type == "SUBSCRIPTION_ACCESS":
        lifecycle = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.id == task.lifecycle_id, EmployeeLifecycle.organization_id == actor.organization_id).first()
        assignment = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.user_id == lifecycle.user_id, SubscriptionAssignment.subscription_id == task.related_subscription_id, SubscriptionAssignment.organization_id == actor.organization_id, SubscriptionAssignment.status == "ACTIVE").first() if lifecycle and task.related_subscription_id else None
        if not assignment:
            raise ValueError("Assign the requested subscription license before completing this task.")
        task.action_status = "ASSIGNED"
    elif task.task_type == "ASSET_ISSUE":
        lifecycle = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.id == task.lifecycle_id, EmployeeLifecycle.organization_id == actor.organization_id).first()
        assignment = db.query(AssetAssignment).filter(AssetAssignment.user_id == lifecycle.user_id, AssetAssignment.asset_id == task.related_asset_id, AssetAssignment.organization_id == actor.organization_id, AssetAssignment.status == "ACTIVE").first() if lifecycle else None
        if not assignment:
            raise ValueError("Assign the requested asset before completing this task.")
        task.action_status = "ASSIGNED"
    else:
        if not completion_note or not completion_note.strip():
            raise ValueError("A verification note is required for manual access tasks.")
        task.action_status = "VERIFIED"
    task.status = "COMPLETED"
    task.completed_at = datetime.utcnow()
    task.completed_by = actor.id
    task.completion_note = completion_note
    lifecycle = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.id == task.lifecycle_id, EmployeeLifecycle.organization_id == actor.organization_id).first()
    if lifecycle:
        remaining = db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id, LifecycleTask.required.is_(True), LifecycleTask.status == "OPEN").count()
        if remaining == 0:
            lifecycle.status = "ACTIVE" if lifecycle.status == "ONBOARDING" else "COMPLETED" if lifecycle.status == "OFFBOARDING" else lifecycle.status
            if lifecycle.status == "COMPLETED": lifecycle.completed_at = datetime.utcnow()
    record_audit(db, actor, "employee.lifecycle_task.completed", "lifecycle_task", task.id, {"task_type": task.task_type, "action_status": task.action_status})
    return task

