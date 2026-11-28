"""Organization profile & onboarding orchestration service."""
from __future__ import annotations

import secrets
from datetime import date, datetime
from typing import Any

from unisora_kit import ForbiddenError, NotFoundError, RequestContext
from app.domain.entities import OrganizationEntity, UserEntity
from app.domain.ports import (
    AssetProvisioningPort,
    AuditEventPort,
    DepartmentRepository,
    IntegrationProvisioningPort,
    LifecycleProvisioningPort,
    OrganizationRepository,
    PasswordHasher,
    SubscriptionProvisioningPort,
    UserRepository,
)


class OrganizationService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        users: UserRepository,
        departments: DepartmentRepository,
        hasher: PasswordHasher,
        lifecycle_port: LifecycleProvisioningPort,
        asset_port: AssetProvisioningPort,
        subscription_port: SubscriptionProvisioningPort,
        integration_port: IntegrationProvisioningPort,
        audit: AuditEventPort,
    ):
        self.organizations = organizations
        self.users = users
        self.departments = departments
        self.hasher = hasher
        self.lifecycle_port = lifecycle_port
        self.asset_port = asset_port
        self.subscription_port = subscription_port
        self.integration_port = integration_port
        self.audit = audit

    def create_organization(self, name: str) -> OrganizationEntity:
        return self.organizations.create(name.strip())

    def get_organization(self, organization_id: int, caller_org_id: int | None = None) -> OrganizationEntity:
        if caller_org_id is not None and caller_org_id != organization_id:
            raise ForbiddenError("Cannot access organizations outside your workspace")
        org = self.organizations.get_by_id(organization_id)
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    def update_profile(self, organization_id: int, updates: dict[str, Any]) -> OrganizationEntity:
        org = self.get_organization(organization_id)
        for field, value in updates.items():
            if hasattr(org, field):
                setattr(org, field, value)
        return self.organizations.save(org)

    def _allocate_unique_email(self, raw_email: str, org_id: int) -> str:
        if self.users.get_by_email(raw_email) is None:
            return raw_email
        base_local, domain = raw_email.split("@", 1) if "@" in raw_email else (raw_email, "company.com")
        candidate = f"{base_local}+{org_id}@{domain}"
        suffix = 1
        while self.users.get_by_email(candidate) is not None:
            candidate = f"{base_local}+{org_id}.{suffix}@{domain}"
            suffix += 1
        return candidate

    def submit_onboarding(
        self,
        *,
        ctx: RequestContext,
        company_updates: dict[str, Any],
        departments_input: list[dict[str, Any]],
        employees_input: list[dict[str, Any]],
        assets_input: list[dict[str, Any]],
        subscriptions_input: list[dict[str, Any]],
        integrations_input: list[dict[str, Any]],
    ) -> OrganizationEntity:
        org = self.get_organization(ctx.organization_id)
        assert org.id is not None

        for field, value in company_updates.items():
            if hasattr(org, field):
                setattr(org, field, value)

        # 1. Create missing departments locally
        dept_map = {d.name.lower(): d for d in self.departments.list_by_org(org.id)}
        for dept_item in departments_input:
            key = dept_item["name"].strip().lower()
            if key and key not in dept_map:
                created = self.departments.create(org.id, dept_item["name"].strip(), dept_item.get("description"))
                dept_map[key] = created

        # 2. Provision employees locally & notify lifecycle service
        user_lookup: dict[str, int] = {}
        for emp in employees_input:
            raw_email = str(emp.get("email") or "").strip().lower()
            if not raw_email:
                continue

            existing = self.users.get_by_email_in_org(raw_email, org.id)
            emp_id = (emp.get("employee_id") or "").strip()
            if not existing and emp_id:
                existing = self.users.get_by_employee_id_in_org(emp_id, org.id)

            if existing is None:
                assigned_email = self._allocate_unique_email(raw_email, org.id)
                created_user = self.users.create(
                    UserEntity(
                        id=None,
                        email=assigned_email,
                        display_name=str(emp.get("full_name") or "").strip() or assigned_email.split("@")[0],
                        employee_id=emp_id or None,
                        phone_number=(emp.get("phone_number") or "").strip() or None,
                        password_hash=self.hasher.hash(secrets.token_urlsafe(24)),
                        organization_id=org.id,
                        role="MEMBER",
                        created_at=datetime.utcnow(),
                    )
                )
                assert created_user.id is not None
                user_lookup[raw_email] = created_user.id
                user_lookup[assigned_email] = created_user.id
                if emp_id:
                    user_lookup[emp_id.lower()] = created_user.id

                effective_date = date.today()
                if emp.get("joining_date"):
                    try:
                        effective_date = date.fromisoformat(str(emp["joining_date"])[:10])
                    except Exception:
                        pass

                self.lifecycle_port.ensure_active_lifecycle(ctx, created_user.id, effective_date)

                dept_name = (emp.get("department_name") or "").strip().lower()
                if dept_name and dept_name in dept_map:
                    dept_match = dept_map[dept_name]
                    assert dept_match.id is not None
                    self.departments.ensure_active_membership(org.id, dept_match.id, created_user.id, effective_date)
            else:
                assert existing.id is not None
                user_lookup[raw_email] = existing.id
                user_lookup[existing.email.lower()] = existing.id
                if existing.employee_id:
                    user_lookup[existing.employee_id.strip().lower()] = existing.id

        # Also map existing org users for asset assigned_to resolution
        for u in self.users.list_by_org(org.id):
            if u.id is not None:
                user_lookup.setdefault(u.email.lower(), u.id)
                if u.employee_id:
                    user_lookup.setdefault(u.employee_id.strip().lower(), u.id)

        # 3. Mark onboarding completed in Identity DB before cross-service orchestration
        org.onboarding_completed = True
        org.onboarding_completed_at = datetime.utcnow()
        saved_org = self.organizations.save(org)

        # 4. Delegate assets, subscriptions, and integrations to owning services
        if assets_input:
            self.asset_port.create_and_assign_assets(ctx, assets_input, user_lookup)
        if subscriptions_input:
            self.subscription_port.import_subscriptions(ctx, subscriptions_input)
        if integrations_input:
            self.integration_port.seed_connections(ctx, integrations_input)

        self.audit.record(
            organization_id=org.id,
            actor_id=ctx.user_id,
            action="organization.onboarding.completed",
            entity_type="organization",
            entity_id=org.id,
            details={
                "departments": len(departments_input),
                "employees": len(employees_input),
                "assets": len(assets_input),
                "subscriptions": len(subscriptions_input),
            },
        )
        return saved_org
