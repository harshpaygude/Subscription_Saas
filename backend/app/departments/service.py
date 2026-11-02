from datetime import date

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.models import Department, DepartmentMembership, User


def get_department(db: Session, user: User, department_id: int) -> Department | None:
    return db.query(Department).filter(
        Department.id == department_id,
        Department.organization_id == user.organization_id,
    ).first()


def add_membership(db: Session, actor: User, department: Department, user_id: int, effective_from: date) -> DepartmentMembership:
    member = db.query(User).filter(User.id == user_id, User.organization_id == actor.organization_id).first()
    if not member:
        raise ValueError("Employee not found in this organization.")
    active = db.query(DepartmentMembership).filter(
        DepartmentMembership.organization_id == actor.organization_id,
        DepartmentMembership.user_id == user_id,
        DepartmentMembership.is_active.is_(True),
    ).all()
    for previous in active:
        previous.is_active = False
        previous.effective_to = effective_from
    membership = DepartmentMembership(
        organization_id=actor.organization_id,
        department_id=department.id,
        user_id=user_id,
        effective_from=effective_from,
    )
    db.add(membership)
    db.flush()
    record_audit(db, actor, "department.membership.created", "department_membership", membership.id, {"user_id": user_id, "department_id": department.id})
    return membership

