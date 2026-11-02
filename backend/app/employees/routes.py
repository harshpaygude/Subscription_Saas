from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.auth.security import hash_password
from app.database.models import Asset, AssetAssignment, Department, DepartmentMembership, EmployeeLifecycle, SubscriptionAssignment, User
from app.database.session import get_db
from app.employees.schemas import EmployeeCreate, EmployeeDetail, EmployeeSummary
from app.audit.service import record_audit
import secrets

router = APIRouter(prefix="/employees", tags=["Employees"])


def employee_summary(db: Session, actor: User, employee: User) -> EmployeeSummary:
    department_ids = [row.department_id for row in db.query(DepartmentMembership).filter(DepartmentMembership.user_id == employee.id, DepartmentMembership.organization_id == actor.organization_id, DepartmentMembership.is_active.is_(True)).all()]
    subscription_count = db.query(SubscriptionAssignment).filter(SubscriptionAssignment.user_id == employee.id, SubscriptionAssignment.organization_id == actor.organization_id, SubscriptionAssignment.status == "ACTIVE").count()
    asset_count = db.query(AssetAssignment).filter(AssetAssignment.user_id == employee.id, AssetAssignment.organization_id == actor.organization_id, AssetAssignment.status == "ACTIVE").count()
    return EmployeeSummary(id=employee.id, email=employee.email, display_name=employee.display_name, employee_id=employee.employee_id, phone_number=employee.phone_number, role=employee.role, department_ids=department_ids, active_subscription_assignments=subscription_count, active_asset_assignments=asset_count)


@router.post("", response_model=EmployeeDetail, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    department = db.query(Department).filter(Department.id == payload.department_id, Department.organization_id == current_user.organization_id, Department.is_active.is_(True)).first()
    if not department:
        raise HTTPException(400, "Active department not found in this organization.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "An employee with this email already exists.")
    if db.query(User).filter(User.organization_id == current_user.organization_id, User.employee_id == payload.employee_id).first():
        raise HTTPException(409, "Employee ID already exists in this organization.")
    assets = db.query(Asset).filter(Asset.id.in_(payload.asset_ids), Asset.organization_id == current_user.organization_id).all() if payload.asset_ids else []
    if len(assets) != len(set(payload.asset_ids)):
        raise HTTPException(400, "One or more selected assets were not found in this organization.")
    assigned_assets = db.query(AssetAssignment).filter(AssetAssignment.asset_id.in_(payload.asset_ids), AssetAssignment.status == "ACTIVE", AssetAssignment.organization_id == current_user.organization_id).all() if payload.asset_ids else []
    if assigned_assets:
        raise HTTPException(409, "One or more selected assets are already assigned.")
    employee = User(email=payload.email, display_name=payload.name, employee_id=payload.employee_id, phone_number=payload.phone_number, password_hash=hash_password(secrets.token_urlsafe(24)), organization_id=current_user.organization_id, role="MEMBER")
    db.add(employee)
    db.flush()
    lifecycle = EmployeeLifecycle(organization_id=current_user.organization_id, user_id=employee.id, status="ACTIVE", joined_at=payload.joined_at)
    db.add(lifecycle)
    db.add(DepartmentMembership(organization_id=current_user.organization_id, department_id=department.id, user_id=employee.id, effective_from=payload.joined_at))
    for asset in assets:
        asset.status = "ASSIGNED"
        db.add(AssetAssignment(organization_id=current_user.organization_id, asset_id=asset.id, user_id=employee.id, assigned_by=current_user.id))
    try:
        record_audit(db, current_user, "employee.created", "employee", employee.id, {"employee_id": payload.employee_id, "asset_ids": payload.asset_ids})
        db.commit(); db.refresh(employee); db.refresh(lifecycle)
        return EmployeeDetail(**employee_summary(db, current_user, employee).model_dump(), created_at=employee.created_at)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An employee with this email or employee ID already exists.")


@router.get("", response_model=list[EmployeeSummary])
def list_employees(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [employee_summary(db, current_user, item) for item in db.query(User).filter(User.organization_id == current_user.organization_id).order_by(User.email.asc()).all()]


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    employee = db.query(User).filter(User.id == employee_id, User.organization_id == current_user.organization_id).first()
    if not employee: raise HTTPException(404, "Employee not found.")
    summary = employee_summary(db, current_user, employee)
    return EmployeeDetail(**summary.model_dump(), created_at=employee.created_at)

