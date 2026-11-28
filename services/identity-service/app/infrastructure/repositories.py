"""SQLAlchemy repository implementations for Identity Service."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from unisora_kit import ConflictError
from app.domain.entities import (
    DepartmentEntity,
    DepartmentMembershipEntity,
    OrganizationEntity,
    UserEntity,
)
from app.infrastructure.models import Department, DepartmentMembership, Organization, User


def _to_org_entity(row: Organization) -> OrganizationEntity:
    return OrganizationEntity(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        legal_name=row.legal_name,
        display_name=row.display_name,
        industry=row.industry,
        company_size=row.company_size,
        website=row.website,
        company_email=row.company_email,
        company_phone=row.company_phone,
        country=row.country,
        state=row.state,
        city=row.city,
        address=row.address,
        postal_code=row.postal_code,
        tax_registration_number=row.tax_registration_number,
        onboarding_completed=bool(row.onboarding_completed),
        onboarding_completed_at=row.onboarding_completed_at,
    )


def _to_user_entity(row: User) -> UserEntity:
    return UserEntity(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        organization_id=row.organization_id,
        role=row.role,
        created_at=row.created_at,
        display_name=row.display_name,
        employee_id=row.employee_id,
        phone_number=row.phone_number,
    )


def _to_dept_entity(row: Department) -> DepartmentEntity:
    return DepartmentEntity(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_membership_entity(row: DepartmentMembership) -> DepartmentMembershipEntity:
    return DepartmentMembershipEntity(
        id=row.id,
        organization_id=row.organization_id,
        department_id=row.department_id,
        user_id=row.user_id,
        is_active=row.is_active,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        created_at=row.created_at,
    )


class SqlAlchemyOrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, organization_id: int) -> Optional[OrganizationEntity]:
        row = self.db.query(Organization).filter(Organization.id == organization_id).first()
        return _to_org_entity(row) if row else None

    def create(self, name: str) -> OrganizationEntity:
        row = Organization(name=name, created_at=datetime.utcnow())
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("Organization with this name already exists") from exc
        return _to_org_entity(row)

    def save(self, org: OrganizationEntity) -> OrganizationEntity:
        row = self.db.query(Organization).filter(Organization.id == org.id).first()
        if not row:
            raise ValueError("Organization not found")
        for field in (
            "name", "legal_name", "display_name", "industry", "company_size",
            "website", "company_email", "company_phone", "country", "state",
            "city", "address", "postal_code", "tax_registration_number",
            "onboarding_completed", "onboarding_completed_at",
        ):
            setattr(row, field, getattr(org, field))
        self.db.flush()
        return _to_org_entity(row)


class SqlAlchemyUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[UserEntity]:
        row = self.db.query(User).filter(User.id == user_id).first()
        return _to_user_entity(row) if row else None

    def get_by_id_in_org(self, user_id: int, organization_id: int) -> Optional[UserEntity]:
        row = self.db.query(User).filter(User.id == user_id, User.organization_id == organization_id).first()
        return _to_user_entity(row) if row else None

    def get_by_email(self, email: str) -> Optional[UserEntity]:
        row = self.db.query(User).filter(User.email.ilike(email)).first()
        return _to_user_entity(row) if row else None

    def get_by_email_in_org(self, email: str, organization_id: int) -> Optional[UserEntity]:
        row = self.db.query(User).filter(User.organization_id == organization_id, User.email.ilike(email)).first()
        return _to_user_entity(row) if row else None

    def get_by_employee_id_in_org(self, employee_id: str, organization_id: int) -> Optional[UserEntity]:
        row = (
            self.db.query(User)
            .filter(User.organization_id == organization_id, User.employee_id == employee_id)
            .first()
        )
        return _to_user_entity(row) if row else None

    def list_by_org(self, organization_id: int) -> list[UserEntity]:
        rows = self.db.query(User).filter(User.organization_id == organization_id).order_by(User.email.asc()).all()
        return [_to_user_entity(r) for r in rows]

    def create(self, user: UserEntity) -> UserEntity:
        row = User(
            email=user.email,
            display_name=user.display_name,
            employee_id=user.employee_id,
            phone_number=user.phone_number,
            password_hash=user.password_hash,
            organization_id=user.organization_id,
            role=user.role,
            created_at=user.created_at,
        )
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("An employee or user with this email already exists.") from exc
        return _to_user_entity(row)

    def save(self, user: UserEntity) -> UserEntity:
        row = self.db.query(User).filter(User.id == user.id).first()
        if not row:
            raise ValueError("User not found")
        row.email = user.email
        row.display_name = user.display_name
        row.employee_id = user.employee_id
        row.phone_number = user.phone_number
        row.password_hash = user.password_hash
        row.role = user.role
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("An employee or user with this email already exists.") from exc
        return _to_user_entity(row)


class SqlAlchemyDepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_org(self, organization_id: int) -> list[DepartmentEntity]:
        rows = (
            self.db.query(Department)
            .filter(Department.organization_id == organization_id)
            .order_by(Department.name.asc())
            .all()
        )
        return [_to_dept_entity(r) for r in rows]

    def get_by_id(self, department_id: int, organization_id: int) -> Optional[DepartmentEntity]:
        row = (
            self.db.query(Department)
            .filter(Department.id == department_id, Department.organization_id == organization_id)
            .first()
        )
        return _to_dept_entity(row) if row else None

    def get_by_name(self, name: str, organization_id: int) -> Optional[DepartmentEntity]:
        row = (
            self.db.query(Department)
            .filter(Department.organization_id == organization_id, Department.name.ilike(name))
            .first()
        )
        return _to_dept_entity(row) if row else None

    def create(self, organization_id: int, name: str, description: Optional[str]) -> DepartmentEntity:
        row = Department(organization_id=organization_id, name=name, description=description)
        self.db.add(row)
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("A department with this name already exists.") from exc
        return _to_dept_entity(row)

    def save(self, dept: DepartmentEntity) -> DepartmentEntity:
        row = self.db.query(Department).filter(Department.id == dept.id, Department.organization_id == dept.organization_id).first()
        if not row:
            raise ValueError("Department not found")
        row.name = dept.name
        row.description = dept.description
        row.is_active = dept.is_active
        try:
            self.db.flush()
        except IntegrityError as exc:
            raise ConflictError("A department with this name already exists.") from exc
        return _to_dept_entity(row)

    def list_memberships_by_department(self, department_id: int, organization_id: int) -> list[DepartmentMembershipEntity]:
        rows = (
            self.db.query(DepartmentMembership)
            .filter(
                DepartmentMembership.department_id == department_id,
                DepartmentMembership.organization_id == organization_id,
            )
            .order_by(DepartmentMembership.created_at.desc())
            .all()
        )
        return [_to_membership_entity(r) for r in rows]

    def list_active_memberships_by_user(self, user_id: int, organization_id: int) -> list[DepartmentMembershipEntity]:
        rows = (
            self.db.query(DepartmentMembership)
            .filter(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.organization_id == organization_id,
                DepartmentMembership.is_active.is_(True),
            )
            .all()
        )
        return [_to_membership_entity(r) for r in rows]

    def deactivate_user_memberships(
        self,
        user_id: int,
        organization_id: int,
        effective_to: date,
        exclude_department_id: Optional[int] = None,
    ) -> None:
        rows = (
            self.db.query(DepartmentMembership)
            .filter(
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.organization_id == organization_id,
                DepartmentMembership.is_active.is_(True),
            )
            .all()
        )
        for row in rows:
            if exclude_department_id is not None and row.department_id == exclude_department_id:
                continue
            row.is_active = False
            row.effective_to = effective_to
        self.db.flush()

    def ensure_active_membership(
        self,
        organization_id: int,
        department_id: int,
        user_id: int,
        effective_from: date,
    ) -> DepartmentMembershipEntity:
        existing = (
            self.db.query(DepartmentMembership)
            .filter(
                DepartmentMembership.organization_id == organization_id,
                DepartmentMembership.department_id == department_id,
                DepartmentMembership.user_id == user_id,
                DepartmentMembership.is_active.is_(True),
            )
            .first()
        )
        if existing:
            return _to_membership_entity(existing)
        row = DepartmentMembership(
            organization_id=organization_id,
            department_id=department_id,
            user_id=user_id,
            effective_from=effective_from,
            is_active=True,
        )
        self.db.add(row)
        self.db.flush()
        return _to_membership_entity(row)
