"""Department and membership management application service."""
from __future__ import annotations

from datetime import date
from typing import Optional

from unisora_kit import ConflictError, DomainValidationError, NotFoundError
from app.domain.entities import DepartmentEntity, DepartmentMembershipEntity
from app.domain.ports import AuditEventPort, DepartmentRepository, UserRepository


class DepartmentService:
    def __init__(
        self,
        departments: DepartmentRepository,
        users: UserRepository,
        audit: AuditEventPort,
    ):
        self.departments = departments
        self.users = users
        self.audit = audit

    def list_departments(self, organization_id: int) -> list[DepartmentEntity]:
        return self.departments.list_by_org(organization_id)

    def create_department(
        self, *, organization_id: int, actor_id: int, name: str, description: Optional[str]
    ) -> DepartmentEntity:
        dept = self.departments.create(organization_id, name.strip(), description)
        assert dept.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="department.created",
            entity_type="department",
            entity_id=dept.id,
        )
        return dept

    def update_department(
        self,
        *,
        organization_id: int,
        actor_id: int,
        department_id: int,
        updates: dict,
    ) -> DepartmentEntity:
        dept = self.departments.get_by_id(department_id, organization_id)
        if not dept:
            raise NotFoundError("Department not found.")
        for key, value in updates.items():
            if hasattr(dept, key):
                setattr(dept, key, value)
        saved = self.departments.save(dept)
        assert saved.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="department.updated",
            entity_type="department",
            entity_id=saved.id,
        )
        return saved

    def add_membership(
        self,
        *,
        organization_id: int,
        actor_id: int,
        department_id: int,
        user_id: int,
        effective_from: date,
    ) -> tuple[DepartmentMembershipEntity, Optional[str], Optional[str]]:
        dept = self.departments.get_by_id(department_id, organization_id)
        if not dept:
            raise NotFoundError("Department not found.")
        if not dept.is_active:
            raise ConflictError("Cannot add members to an inactive department.")
        member = self.users.get_by_id_in_org(user_id, organization_id)
        if not member:
            raise DomainValidationError("Employee not found in this organization.")

        self.departments.deactivate_user_memberships(user_id, organization_id, effective_from)
        membership = self.departments.ensure_active_membership(
            organization_id, department_id, user_id, effective_from
        )
        assert membership.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="department.membership.created",
            entity_type="department_membership",
            entity_id=membership.id,
            details={"user_id": user_id, "department_id": department_id},
        )
        return membership, member.email, member.display_name

    def list_memberships(
        self, *, organization_id: int, department_id: int
    ) -> list[tuple[DepartmentMembershipEntity, Optional[str], Optional[str]]]:
        dept = self.departments.get_by_id(department_id, organization_id)
        if not dept:
            raise NotFoundError("Department not found.")
        memberships = self.departments.list_memberships_by_department(department_id, organization_id)
        user_map = {u.id: u for u in self.users.list_by_org(organization_id)}
        result = []
        for m in memberships:
            emp = user_map.get(m.user_id)
            result.append((m, emp.email if emp else None, emp.display_name if emp else None))
        return result
