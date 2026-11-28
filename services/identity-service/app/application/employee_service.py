"""Employee directory application service (coordinates via ports, zero cross-DB joins)."""
from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any, Optional

from unisora_kit import ConflictError, DomainValidationError, NotFoundError, RequestContext
from app.domain.entities import UserEntity
from app.domain.ports import (
    AssetProvisioningPort,
    AuditEventPort,
    DepartmentRepository,
    LifecycleProvisioningPort,
    PasswordHasher,
    SubscriptionProvisioningPort,
    UserRepository,
)


class EmployeeService:
    def __init__(
        self,
        users: UserRepository,
        departments: DepartmentRepository,
        hasher: PasswordHasher,
        asset_port: AssetProvisioningPort,
        subscription_port: SubscriptionProvisioningPort,
        lifecycle_port: LifecycleProvisioningPort,
        audit: AuditEventPort,
    ):
        self.users = users
        self.departments = departments
        self.hasher = hasher
        self.asset_port = asset_port
        self.subscription_port = subscription_port
        self.lifecycle_port = lifecycle_port
        self.audit = audit

    def list_employees(self, ctx: RequestContext) -> list[dict[str, Any]]:
        users = self.users.list_by_org(ctx.organization_id)
        asset_counts = self.asset_port.get_active_assignment_counts(ctx)
        sub_counts = self.subscription_port.get_active_assignment_counts(ctx)
        result = []
        for u in users:
            assert u.id is not None
            dept_ids = [
                m.department_id
                for m in self.departments.list_active_memberships_by_user(u.id, ctx.organization_id)
            ]
            result.append(
                {
                    "id": u.id,
                    "email": u.email,
                    "display_name": u.display_name,
                    "employee_id": u.employee_id,
                    "phone_number": u.phone_number,
                    "role": u.role,
                    "department_ids": dept_ids,
                    "active_subscription_assignments": sub_counts.get(u.id, 0),
                    "active_asset_assignments": asset_counts.get(u.id, 0),
                    "created_at": u.created_at,
                }
            )
        return result

    def get_employee(self, ctx: RequestContext, user_id: int) -> dict[str, Any]:
        u = self.users.get_by_id_in_org(user_id, ctx.organization_id)
        if not u:
            raise NotFoundError("Employee not found.")
        assert u.id is not None
        dept_ids = [
            m.department_id
            for m in self.departments.list_active_memberships_by_user(u.id, ctx.organization_id)
        ]
        asset_counts = self.asset_port.get_active_assignment_counts(ctx)
        sub_counts = self.subscription_port.get_active_assignment_counts(ctx)
        return {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "employee_id": u.employee_id,
            "phone_number": u.phone_number,
            "role": u.role,
            "department_ids": dept_ids,
            "active_subscription_assignments": sub_counts.get(u.id, 0),
            "active_asset_assignments": asset_counts.get(u.id, 0),
            "created_at": u.created_at,
        }

    def create_employee(
        self,
        *,
        ctx: RequestContext,
        employee_id: str,
        name: str,
        email: str,
        phone_number: Optional[str],
        department_id: int,
        joined_at: date,
        asset_ids: list[int],
    ) -> dict[str, Any]:
        dept = self.departments.get_by_id(department_id, ctx.organization_id)
        if not dept or not dept.is_active:
            raise DomainValidationError("Active department not found in this organization.")

        normalized_email = email.strip().lower()
        if self.users.get_by_email(normalized_email):
            raise ConflictError("An employee with this email already exists.")
        if self.users.get_by_employee_id_in_org(employee_id, ctx.organization_id):
            raise ConflictError("Employee ID already exists in this organization.")

        if asset_ids:
            self.asset_port.validate_available_assets(ctx, asset_ids)

        employee = self.users.create(
            UserEntity(
                id=None,
                email=normalized_email,
                display_name=name.strip(),
                employee_id=employee_id.strip(),
                phone_number=phone_number,
                password_hash=self.hasher.hash(secrets.token_urlsafe(24)),
                organization_id=ctx.organization_id,
                role="MEMBER",
                created_at=datetime.utcnow(),
            )
        )
        assert employee.id is not None
        self.departments.ensure_active_membership(ctx.organization_id, department_id, employee.id, joined_at)
        self.lifecycle_port.ensure_active_lifecycle(ctx, employee.id, joined_at)
        if asset_ids:
            self.asset_port.assign_assets_to_user(ctx, employee.id, asset_ids, reassign=False)

        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="employee.created",
            entity_type="employee",
            entity_id=employee.id,
            details={"employee_id": employee_id, "asset_ids": asset_ids},
        )
        return self.get_employee(ctx, employee.id)

    def update_employee(
        self,
        *,
        ctx: RequestContext,
        user_id: int,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        employee = self.users.get_by_id_in_org(user_id, ctx.organization_id)
        if not employee:
            raise NotFoundError("Employee not found.")

        new_email = updates.get("email")
        if new_email and new_email.lower() != employee.email.lower():
            if self.users.get_by_email(new_email.lower()):
                raise ConflictError("An employee with this email already exists.")
            employee.email = new_email.lower()

        new_emp_id = updates.get("employee_id")
        if new_emp_id and new_emp_id != employee.employee_id:
            if self.users.get_by_employee_id_in_org(new_emp_id, ctx.organization_id):
                raise ConflictError("Employee ID already exists in this organization.")
            employee.employee_id = new_emp_id

        if updates.get("name"):
            employee.display_name = updates["name"]
        if "phone_number" in updates and updates["phone_number"] is not None:
            employee.phone_number = updates["phone_number"]
        if updates.get("role"):
            employee.role = updates["role"]

        self.users.save(employee)
        assert employee.id is not None

        dept_id = updates.get("department_id")
        if dept_id is not None:
            dept = self.departments.get_by_id(dept_id, ctx.organization_id)
            if not dept or not dept.is_active:
                raise DomainValidationError("Active department not found in this organization.")
            self.departments.deactivate_user_memberships(
                employee.id, ctx.organization_id, date.today(), exclude_department_id=dept_id
            )
            self.departments.ensure_active_membership(ctx.organization_id, dept_id, employee.id, date.today())

        sub_ids = updates.get("subscription_ids")
        if sub_ids is not None:
            self.subscription_port.assign_subscriptions_to_user(ctx, employee.id, sub_ids)

        asset_ids = updates.get("asset_ids")
        if asset_ids is not None:
            self.asset_port.assign_assets_to_user(ctx, employee.id, asset_ids, reassign=True)

        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="employee.updated",
            entity_type="employee",
            entity_id=employee.id,
            details={"updated_fields": list(updates.keys())},
        )
        return self.get_employee(ctx, employee.id)
