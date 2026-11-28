"""Application service for Subscription Licenses & Seat Assignments (DIP)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from unisora_kit import ConflictError, NotFoundError, RequestContext
from app.domain.entities import SubscriptionAssignmentEntity, SubscriptionLicenseEntity
from app.domain.ports import (
    AssignmentRepository,
    AuditEventPort,
    IdentityLookupPort,
    LicenseRepository,
    SubscriptionRepository,
)


class LicenseAssignmentService:
    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        licenses: LicenseRepository,
        assignments: AssignmentRepository,
        identity_lookup: IdentityLookupPort,
        audit: AuditEventPort,
    ):
        self.subscriptions = subscriptions
        self.licenses = licenses
        self.assignments = assignments
        self.identity_lookup = identity_lookup
        self.audit = audit

    def create_license(
        self, *, organization_id: int, subscription_id: int, reference: Optional[str], capacity: int
    ) -> SubscriptionLicenseEntity:
        sub = self.subscriptions.get_by_id(subscription_id, organization_id)
        if not sub:
            raise NotFoundError("Subscription not found.")
        now = datetime.utcnow()
        return self.licenses.create(
            SubscriptionLicenseEntity(
                id=None,
                organization_id=organization_id,
                subscription_id=subscription_id,
                reference=reference,
                capacity=capacity,
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )

    def list_licenses(self, *, organization_id: int, subscription_id: int) -> list[SubscriptionLicenseEntity]:
        sub = self.subscriptions.get_by_id(subscription_id, organization_id)
        if not sub:
            raise NotFoundError("Subscription not found.")
        return self.licenses.list_by_subscription(subscription_id, organization_id)

    def assign_license(
        self,
        *,
        ctx: RequestContext,
        subscription_id: int,
        license_id: Optional[int],
        user_id: int,
        notes: Optional[str] = None,
    ) -> SubscriptionAssignmentEntity:
        sub = self.subscriptions.get_by_id(subscription_id, ctx.organization_id)
        if not sub:
            raise NotFoundError("Subscription not found.")
        if not self.identity_lookup.user_exists_in_org(ctx, user_id):
            raise ConflictError("Employee not found in this organization.")

        if license_id is None:
            raise ConflictError("An active license is required for assignment.")

        lic = self.licenses.get_by_id(license_id, ctx.organization_id)
        if not lic or lic.subscription_id != subscription_id:
            raise ConflictError("License does not belong to this subscription.")
        if lic.status != "ACTIVE":
            raise ConflictError("License is not active.")
        assert lic.id is not None

        active_count = self.assignments.count_active_for_license_locked(lic.id)
        if active_count >= lic.capacity:
            raise ConflictError("License capacity has been reached.")

        duplicate = self.assignments.find_active_for_user_and_subscription(
            ctx.organization_id, subscription_id, user_id
        )
        if duplicate:
            raise ConflictError("Employee already has an active assignment for this subscription.")

        assignment = self.assignments.create(
            SubscriptionAssignmentEntity(
                id=None,
                organization_id=ctx.organization_id,
                subscription_id=subscription_id,
                license_id=lic.id,
                user_id=user_id,
                assigned_by=ctx.user_id,
                assigned_at=datetime.utcnow(),
                released_at=None,
                status="ACTIVE",
                notes=notes,
            )
        )
        assert assignment.id is not None
        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="subscription.license.assigned",
            entity_type="subscription_assignment",
            entity_id=assignment.id,
            details={"user_id": user_id, "license_id": lic.id},
        )
        return assignment

    def release_license(self, *, ctx: RequestContext, assignment_id: int) -> SubscriptionAssignmentEntity:
        item = self.assignments.get_active_by_id(assignment_id, ctx.organization_id)
        if not item:
            raise NotFoundError("Active subscription assignment not found.")
        item.status = "RELEASED"
        item.released_at = datetime.utcnow()
        saved = self.assignments.save(item)
        assert saved.id is not None
        self.audit.record(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            action="subscription.license.released",
            entity_type="subscription_assignment",
            entity_id=saved.id,
        )
        return saved

    def list_assignments(
        self, *, organization_id: int, subscription_id: Optional[int] = None, user_id: Optional[int] = None
    ) -> list[SubscriptionAssignmentEntity]:
        return self.assignments.list_filtered(
            organization_id, subscription_id=subscription_id, user_id=user_id
        )
