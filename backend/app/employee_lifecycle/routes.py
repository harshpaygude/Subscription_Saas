from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.database.models import Asset, AssetAssignment, Department, DepartmentMembership, EmployeeLifecycle, LifecycleTask, Subscription, SubscriptionAssignment, User
from app.database.session import get_db
from app.employee_lifecycle.schemas import (
    LifecycleDashboardResponse,
    LifecycleEmployeeResponse,
    LifecycleResourceResponse,
    LifecycleTaskResponse,
    OffboardingRequest,
    OnboardingRequest,
    TaskCompletionRequest,
)
from app.employee_lifecycle.service import complete_task, get_lifecycle_for_user, start_offboarding, start_onboarding

router = APIRouter(tags=["Employee lifecycle"])


def task_response(db: Session, task: LifecycleTask) -> LifecycleTaskResponse:
    res = LifecycleTaskResponse.model_validate(task)
    if task.task_type == "RECOVER_ASSET" and (task.title == "Recover company asset" or "Recover company asset:" not in task.title):
        asset = None
        if task.related_asset_id:
            asset = db.query(Asset).filter(Asset.id == task.related_asset_id).first()
        elif task.related_asset_assignment_id:
            asgn = db.query(AssetAssignment).filter(AssetAssignment.id == task.related_asset_assignment_id).first()
            if asgn:
                asset = db.query(Asset).filter(Asset.id == asgn.asset_id).first()
        if asset:
            res.title = f"Recover company asset: {asset.name} ({asset.asset_tag})"
    return res


def employee_response(db: Session, lifecycle: EmployeeLifecycle) -> LifecycleEmployeeResponse:
    user = db.query(User).filter(User.id == lifecycle.user_id).first()
    tasks = db.query(LifecycleTask).filter(LifecycleTask.lifecycle_id == lifecycle.id).order_by(LifecycleTask.created_at.asc()).all()
    departments = db.query(DepartmentMembership).filter(DepartmentMembership.user_id == lifecycle.user_id, DepartmentMembership.organization_id == lifecycle.organization_id, DepartmentMembership.is_active.is_(True)).all()
    department_records = {item.id: item.name for item in db.query(Department).filter(Department.organization_id == lifecycle.organization_id).all()}
    subscription_assignments = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.user_id == lifecycle.user_id, SubscriptionAssignment.organization_id == lifecycle.organization_id).order_by(SubscriptionAssignment.assigned_at.desc()).all()
    asset_assignments = db.query(AssetAssignment).filter(AssetAssignment.user_id == lifecycle.user_id, AssetAssignment.organization_id == lifecycle.organization_id).order_by(AssetAssignment.assigned_at.desc()).all()
    subscriptions = {item.id: item for item in db.query(Subscription).filter(Subscription.organization_id == lifecycle.organization_id).all()}
    assets = {item.id: item for item in db.query(Asset).filter(Asset.organization_id == lifecycle.organization_id).all()}
    return LifecycleEmployeeResponse(
        id=lifecycle.id,
        user_id=lifecycle.user_id,
        email=user.email,
        display_name=user.display_name,
        employee_id=user.employee_id,
        phone_number=user.phone_number,
        role=user.role,
        status=lifecycle.status,
        joined_at=lifecycle.joined_at,
        last_working_date=lifecycle.last_working_date,
        department_ids=[item.department_id for item in departments],
        department_names=[department_records[item.department_id] for item in departments if item.department_id in department_records],
        subscription_assignments=[LifecycleResourceResponse(id=item.id, resource_id=item.subscription_id, status=item.status, assigned_at=item.assigned_at, released_at=item.released_at, resource_name=subscriptions.get(item.subscription_id).name if subscriptions.get(item.subscription_id) else None, resource_provider=subscriptions.get(item.subscription_id).provider if subscriptions.get(item.subscription_id) else None) for item in subscription_assignments],
        asset_assignments=[LifecycleResourceResponse(id=item.id, resource_id=item.asset_id, status=item.status, assigned_at=item.assigned_at, released_at=item.returned_at, resource_name=f"{assets[item.asset_id].name} ({assets[item.asset_id].asset_tag})" if assets.get(item.asset_id) else None, resource_provider=assets[item.asset_id].asset_type if assets.get(item.asset_id) else None) for item in asset_assignments],
        tasks=[task_response(db, item) for item in tasks],
        open_task_count=sum(item.status == "OPEN" and item.required for item in tasks),
        completed_task_count=sum(item.status == "COMPLETED" for item in tasks),
    )


@router.get("/employee-lifecycle/dashboard", response_model=LifecycleDashboardResponse)
def lifecycle_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lifecycles = db.query(EmployeeLifecycle).filter(EmployeeLifecycle.organization_id == current_user.organization_id).order_by(EmployeeLifecycle.updated_at.desc()).all()
    pending_tasks = db.query(LifecycleTask).filter(LifecycleTask.organization_id == current_user.organization_id, LifecycleTask.status == "OPEN").order_by(LifecycleTask.due_at.asc().nullslast(), LifecycleTask.created_at.asc()).all()
    return LifecycleDashboardResponse(
        new_joiners=[employee_response(db, item) for item in lifecycles if item.status == "ONBOARDING"],
        working=[employee_response(db, item) for item in lifecycles if item.status == "ACTIVE"],
        offboarding=[employee_response(db, item) for item in lifecycles if item.status == "OFFBOARDING"],
        completed=[employee_response(db, item) for item in lifecycles if item.status == "COMPLETED"],
        pending_tasks=[task_response(db, item) for item in pending_tasks],
    )


@router.post("/employees/{user_id}/onboarding", response_model=LifecycleEmployeeResponse)
def begin_onboarding(user_id: int, payload: OnboardingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    try:
        lifecycle = start_onboarding(db, current_user, user_id, payload.department_id, payload.joined_at, payload.tasks)
        db.commit(); db.refresh(lifecycle)
        return employee_response(db, lifecycle)
    except ValueError as exc:
        db.rollback(); raise HTTPException(400, str(exc))


@router.get("/employees/{user_id}/lifecycle", response_model=LifecycleEmployeeResponse)
def employee_lifecycle(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lifecycle = get_lifecycle_for_user(db, current_user, user_id)
    if not lifecycle: raise HTTPException(404, "Employee lifecycle profile not found.")
    return employee_response(db, lifecycle)


@router.post("/employees/{user_id}/offboarding", response_model=LifecycleEmployeeResponse)
def begin_offboarding(user_id: int, payload: OffboardingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    lifecycle = get_lifecycle_for_user(db, current_user, user_id)
    if not lifecycle: raise HTTPException(404, "Employee lifecycle profile not found. Start onboarding first.")
    try:
        lifecycle = start_offboarding(db, current_user, lifecycle, payload.last_working_date)
        db.commit(); db.refresh(lifecycle)
        return employee_response(db, lifecycle)
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc))


@router.get("/lifecycle-tasks", response_model=list[LifecycleTaskResponse])
def list_lifecycle_tasks(status_filter: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(LifecycleTask).filter(LifecycleTask.organization_id == current_user.organization_id)
    if status_filter: query = query.filter(LifecycleTask.status == status_filter.upper())
    return [task_response(db, item) for item in query.order_by(LifecycleTask.created_at.desc()).all()]


@router.post("/lifecycle-tasks/{task_id}/complete", response_model=LifecycleTaskResponse)
def finish_lifecycle_task(task_id: int, payload: TaskCompletionRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    task = db.query(LifecycleTask).filter(LifecycleTask.id == task_id, LifecycleTask.organization_id == current_user.organization_id).first()
    if not task: raise HTTPException(404, "Lifecycle task not found.")
    try:
        complete_task(db, current_user, task, payload.completion_note)
        db.commit(); db.refresh(task); return task_response(db, task)
    except ValueError as exc:
        db.rollback(); raise HTTPException(409, str(exc))

