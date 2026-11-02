from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.policies import require_admin
from app.database.models import Department, DepartmentMembership, User
from app.database.session import get_db
from app.departments.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate, MembershipCreate, MembershipResponse
from app.departments.service import add_membership, get_department
from app.audit.service import record_audit

router = APIRouter(prefix="/departments", tags=["Departments"])


def membership_response(db: Session, membership: DepartmentMembership) -> dict:
    employee = db.query(User).filter(User.id == membership.user_id, User.organization_id == membership.organization_id).first()
    return {"id": membership.id, "organization_id": membership.organization_id, "department_id": membership.department_id, "user_id": membership.user_id, "is_active": membership.is_active, "effective_from": membership.effective_from, "effective_to": membership.effective_to, "created_at": membership.created_at, "email": employee.email if employee else None, "display_name": employee.display_name if employee else None}


@router.get("", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Department).filter(Department.organization_id == current_user.organization_id).order_by(Department.name.asc()).all()


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = Department(organization_id=current_user.organization_id, **payload.model_dump())
    db.add(item)
    try:
        db.flush(); record_audit(db, current_user, "department.created", "department", item.id); db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A department with this name already exists.")
    return item


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, payload: DepartmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    item = get_department(db, current_user, department_id)
    if not item: raise HTTPException(404, "Department not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    try:
        record_audit(db, current_user, "department.updated", "department", item.id); db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "A department with this name already exists.")
    return item


@router.post("/{department_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def create_membership(department_id: int, payload: MembershipCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_admin(current_user)
    department = get_department(db, current_user, department_id)
    if not department: raise HTTPException(404, "Department not found.")
    if not department.is_active: raise HTTPException(409, "Cannot add members to an inactive department.")
    try:
        item = add_membership(db, current_user, department, payload.user_id, payload.effective_from); db.commit(); db.refresh(item); return membership_response(db, item)
    except ValueError as exc:
        db.rollback(); raise HTTPException(400, str(exc))


@router.get("/{department_id}/members", response_model=list[MembershipResponse])
def list_members(department_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    department = get_department(db, current_user, department_id)
    if not department: raise HTTPException(404, "Department not found.")
    return [membership_response(db, item) for item in db.query(DepartmentMembership).filter(DepartmentMembership.department_id == department.id, DepartmentMembership.organization_id == current_user.organization_id).order_by(DepartmentMembership.created_at.desc()).all()]

