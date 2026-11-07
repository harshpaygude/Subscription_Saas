from datetime import date, datetime
import secrets
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.auth.security import hash_password
from app.database.models import (
    Asset,
    AssetAssignment,
    Department,
    DepartmentMembership,
    EmployeeLifecycle,
    Subscription,
    SubscriptionAssignment,
    SubscriptionLicense,
    User,
)
from app.database.session import get_db
from app.employees.schemas import EmployeeCreate, EmployeeDetail, EmployeeSummary, EmployeeUpdate
from app.employees.csv_import import process_bulk_import
from app.audit.service import record_audit
from app.license_assignments.service import assign_license

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


@router.patch("/{employee_id}", response_model=EmployeeDetail)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    employee = db.query(User).filter(
        User.id == employee_id,
        User.organization_id == current_user.organization_id,
    ).first()
    if not employee:
        raise HTTPException(404, "Employee not found.")

    # Check email uniqueness if updating email
    if payload.email and payload.email.lower() != employee.email.lower():
        if db.query(User).filter(User.email == payload.email.lower()).first():
            raise HTTPException(409, "An employee with this email already exists.")
        employee.email = payload.email.lower()

    # Check employee_id uniqueness if updating
    if payload.employee_id and payload.employee_id != employee.employee_id:
        if db.query(User).filter(
            User.organization_id == current_user.organization_id,
            User.employee_id == payload.employee_id,
        ).first():
            raise HTTPException(409, "Employee ID already exists in this organization.")
        employee.employee_id = payload.employee_id

    if payload.name:
        employee.display_name = payload.name
    if payload.phone_number is not None:
        employee.phone_number = payload.phone_number
    if payload.role:
        employee.role = payload.role

    # Update Department
    if payload.department_id is not None:
        department = db.query(Department).filter(
            Department.id == payload.department_id,
            Department.organization_id == current_user.organization_id,
            Department.is_active.is_(True),
        ).first()
        if not department:
            raise HTTPException(400, "Active department not found in this organization.")

        prev_memberships = db.query(DepartmentMembership).filter(
            DepartmentMembership.user_id == employee.id,
            DepartmentMembership.organization_id == current_user.organization_id,
            DepartmentMembership.is_active.is_(True),
        ).all()
        for m in prev_memberships:
            if m.department_id != payload.department_id:
                m.is_active = False
                m.effective_to = date.today()

        active_m = db.query(DepartmentMembership).filter(
            DepartmentMembership.user_id == employee.id,
            DepartmentMembership.department_id == payload.department_id,
            DepartmentMembership.organization_id == current_user.organization_id,
            DepartmentMembership.is_active.is_(True),
        ).first()
        if not active_m:
            db.add(DepartmentMembership(
                organization_id=current_user.organization_id,
                department_id=payload.department_id,
                user_id=employee.id,
                effective_from=date.today(),
            ))

    # Add/assign subscriptions from subscriptions page
    if payload.subscription_ids is not None:
        for sub_id in payload.subscription_ids:
            sub = db.query(Subscription).filter(
                Subscription.id == sub_id,
                Subscription.organization_id == current_user.organization_id,
            ).first()
            if not sub:
                continue
            existing_sub_assignment = db.query(SubscriptionAssignment).filter(
                SubscriptionAssignment.organization_id == current_user.organization_id,
                SubscriptionAssignment.subscription_id == sub.id,
                SubscriptionAssignment.user_id == employee.id,
                SubscriptionAssignment.status == "ACTIVE",
            ).first()
            if not existing_sub_assignment:
                lic = db.query(SubscriptionLicense).filter(
                    SubscriptionLicense.organization_id == current_user.organization_id,
                    SubscriptionLicense.subscription_id == sub.id,
                    SubscriptionLicense.status == "ACTIVE",
                ).first()
                if not lic:
                    lic = SubscriptionLicense(
                        organization_id=current_user.organization_id,
                        subscription_id=sub.id,
                        reference=f"{sub.name} Seat",
                        capacity=100,
                        status="ACTIVE",
                    )
                    db.add(lic)
                    db.flush()
                assign_license(db, current_user, sub, lic, {"user_id": employee.id})

    # Assign multiple IT assets (1-to-many relationship)
    if payload.asset_ids is not None:
        for asset_id in payload.asset_ids:
            asset = db.query(Asset).filter(
                Asset.id == asset_id,
                Asset.organization_id == current_user.organization_id,
            ).first()
            if not asset:
                continue
            existing_asset_assignment = db.query(AssetAssignment).filter(
                AssetAssignment.organization_id == current_user.organization_id,
                AssetAssignment.asset_id == asset.id,
                AssetAssignment.status == "ACTIVE",
            ).first()
            if existing_asset_assignment:
                if existing_asset_assignment.user_id != employee.id:
                    existing_asset_assignment.status = "RETURNED"
                    existing_asset_assignment.returned_at = datetime.utcnow()
                    db.add(AssetAssignment(
                        organization_id=current_user.organization_id,
                        asset_id=asset.id,
                        user_id=employee.id,
                        assigned_by=current_user.id,
                        status="ACTIVE",
                    ))
                    asset.status = "ASSIGNED"
            else:
                db.add(AssetAssignment(
                    organization_id=current_user.organization_id,
                    asset_id=asset.id,
                    user_id=employee.id,
                    assigned_by=current_user.id,
                    status="ACTIVE",
                ))
                asset.status = "ASSIGNED"

    record_audit(
        db,
        current_user,
        "employee.updated",
        "employee",
        employee.id,
        {"updated_fields": list(payload.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    db.refresh(employee)
    summary = employee_summary(db, current_user, employee)
    return EmployeeDetail(**summary.model_dump(), created_at=employee.created_at)



@router.post("/import-csv")
async def import_employees_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_admin(current_user)
    if not file.filename:
        raise HTTPException(400, "No file uploaded.")
    fname = file.filename.lower()
    if not (fname.endswith(".csv") or fname.endswith(".xlsx") or fname.endswith(".xls")):
        raise HTTPException(400, "Invalid file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.")
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File exceeds maximum size limit of 15 MB.")
    try:
        result = process_bulk_import(content, file.filename, db, current_user)
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to import employee file: {str(e)}")


