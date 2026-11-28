"""SQLAlchemy repositories for Subscription Service."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.entities import (
    ManualSpendEntity,
    SubscriptionAssignmentEntity,
    SubscriptionEntity,
    SubscriptionLicenseEntity,
)
from app.infrastructure.models import (
    ManualSpendEntry,
    Subscription,
    SubscriptionAssignment,
    SubscriptionLicense,
)


def _to_sub(row: Subscription) -> SubscriptionEntity:
    return SubscriptionEntity(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        provider=row.provider,
        name=row.name,
        plan=row.plan,
        amount=Decimal(str(row.amount)) if row.amount is not None else None,
        currency=row.currency,
        billing_interval=row.billing_interval,
        start_date=row.start_date,
        next_renewal_date=row.next_renewal_date,
        status=row.status,
        cancellation_date=row.cancellation_date,
        source=row.source,
        note=row.note,
        renewal_type=row.renewal_type,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_manual(row: ManualSpendEntry) -> ManualSpendEntity:
    return ManualSpendEntity(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        provider=row.provider,
        amount=Decimal(str(row.amount)),
        currency=row.currency,
        billing_interval=row.billing_interval,
        period_start=row.period_start,
        period_end=row.period_end,
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_license(row: SubscriptionLicense) -> SubscriptionLicenseEntity:
    return SubscriptionLicenseEntity(
        id=row.id,
        organization_id=row.organization_id,
        subscription_id=row.subscription_id,
        reference=row.reference,
        capacity=row.capacity,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_assignment(row: SubscriptionAssignment) -> SubscriptionAssignmentEntity:
    return SubscriptionAssignmentEntity(
        id=row.id,
        organization_id=row.organization_id,
        subscription_id=row.subscription_id,
        license_id=row.license_id,
        user_id=row.user_id,
        assigned_by=row.assigned_by,
        assigned_at=row.assigned_at,
        released_at=row.released_at,
        status=row.status,
        notes=row.notes,
    )


class SqlAlchemySubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, sub: SubscriptionEntity) -> SubscriptionEntity:
        row = Subscription(
            organization_id=sub.organization_id,
            user_id=sub.user_id,
            provider=sub.provider,
            name=sub.name,
            plan=sub.plan,
            amount=float(sub.amount) if sub.amount is not None else None,
            currency=sub.currency,
            billing_interval=sub.billing_interval,
            start_date=sub.start_date,
            next_renewal_date=sub.next_renewal_date,
            status=sub.status,
            cancellation_date=sub.cancellation_date,
            source=sub.source,
            note=sub.note,
            renewal_type=sub.renewal_type,
        )
        self.db.add(row)
        self.db.flush()
        return _to_sub(row)

    def get_by_id(self, subscription_id: int, organization_id: int) -> Optional[SubscriptionEntity]:
        row = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id, Subscription.organization_id == organization_id)
            .first()
        )
        return _to_sub(row) if row else None

    def find_by_provider_and_name(self, organization_id: int, provider: str, name: str) -> Optional[SubscriptionEntity]:
        row = (
            self.db.query(Subscription)
            .filter(
                Subscription.organization_id == organization_id,
                Subscription.provider.ilike(provider),
                Subscription.name.ilike(name),
            )
            .first()
        )
        return _to_sub(row) if row else None

    def find_by_provider(self, organization_id: int, provider: str) -> Optional[SubscriptionEntity]:
        row = (
            self.db.query(Subscription)
            .filter(
                Subscription.organization_id == organization_id,
                Subscription.provider.ilike(provider),
            )
            .first()
        )
        return _to_sub(row) if row else None

    def list_filtered(
        self,
        organization_id: int,
        *,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        billing_interval: Optional[str] = None,
        renewal_before: Optional[date] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[SubscriptionEntity]:
        query = self.db.query(Subscription).filter(Subscription.organization_id == organization_id)
        if provider:
            query = query.filter(Subscription.provider == provider)
        if status:
            query = query.filter(Subscription.status == status.upper())
        if billing_interval:
            query = query.filter(Subscription.billing_interval == billing_interval)
        if renewal_before:
            query = query.filter(Subscription.next_renewal_date <= renewal_before)
        rows = (
            query.order_by(Subscription.next_renewal_date.asc().nullslast(), Subscription.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_to_sub(r) for r in rows]

    def list_all(self, organization_id: int) -> list[SubscriptionEntity]:
        rows = (
            self.db.query(Subscription)
            .filter(Subscription.organization_id == organization_id)
            .order_by(Subscription.next_renewal_date.asc())
            .all()
        )
        return [_to_sub(r) for r in rows]

    def save(self, sub: SubscriptionEntity) -> SubscriptionEntity:
        row = self.db.query(Subscription).filter(Subscription.id == sub.id, Subscription.organization_id == sub.organization_id).first()
        if not row:
            raise ValueError("Subscription not found")
        row.provider = sub.provider
        row.name = sub.name
        row.plan = sub.plan
        row.amount = float(sub.amount) if sub.amount is not None else None
        row.currency = sub.currency
        row.billing_interval = sub.billing_interval
        row.start_date = sub.start_date
        row.next_renewal_date = sub.next_renewal_date
        row.status = sub.status
        row.cancellation_date = sub.cancellation_date
        row.note = sub.note
        row.renewal_type = sub.renewal_type
        self.db.flush()
        return _to_sub(row)

    def delete(self, subscription_id: int, organization_id: int) -> None:
        row = self.db.query(Subscription).filter(Subscription.id == subscription_id, Subscription.organization_id == organization_id).first()
        if row:
            self.db.delete(row)
            self.db.flush()


class SqlAlchemyManualSpendRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self, organization_id: int) -> list[ManualSpendEntity]:
        rows = self.db.query(ManualSpendEntry).filter(ManualSpendEntry.organization_id == organization_id).all()
        return [_to_manual(r) for r in rows]

    def upsert(self, entry: ManualSpendEntity) -> ManualSpendEntity:
        existing = (
            self.db.query(ManualSpendEntry)
            .filter(
                ManualSpendEntry.organization_id == entry.organization_id,
                ManualSpendEntry.provider == entry.provider,
                ManualSpendEntry.period_start == entry.period_start,
            )
            .first()
        )
        if existing:
            existing.amount = float(entry.amount)
            existing.currency = entry.currency
            existing.billing_interval = entry.billing_interval
            existing.period_end = entry.period_end
            existing.note = entry.note
            self.db.flush()
            return _to_manual(existing)
        row = ManualSpendEntry(
            organization_id=entry.organization_id,
            user_id=entry.user_id,
            provider=entry.provider,
            amount=float(entry.amount),
            currency=entry.currency,
            billing_interval=entry.billing_interval,
            period_start=entry.period_start,
            period_end=entry.period_end,
            note=entry.note,
        )
        self.db.add(row)
        self.db.flush()
        return _to_manual(row)


class SqlAlchemyLicenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, lic: SubscriptionLicenseEntity) -> SubscriptionLicenseEntity:
        row = SubscriptionLicense(
            organization_id=lic.organization_id,
            subscription_id=lic.subscription_id,
            reference=lic.reference,
            capacity=lic.capacity,
            status=lic.status,
        )
        self.db.add(row)
        self.db.flush()
        return _to_license(row)

    def get_by_id(self, license_id: int, organization_id: int) -> Optional[SubscriptionLicenseEntity]:
        row = (
            self.db.query(SubscriptionLicense)
            .filter(SubscriptionLicense.id == license_id, SubscriptionLicense.organization_id == organization_id)
            .first()
        )
        return _to_license(row) if row else None

    def list_by_subscription(self, subscription_id: int, organization_id: int) -> list[SubscriptionLicenseEntity]:
        rows = (
            self.db.query(SubscriptionLicense)
            .filter(SubscriptionLicense.subscription_id == subscription_id, SubscriptionLicense.organization_id == organization_id)
            .order_by(SubscriptionLicense.id.asc())
            .all()
        )
        return [_to_license(r) for r in rows]

    def get_first_active_for_subscription(self, subscription_id: int, organization_id: int) -> Optional[SubscriptionLicenseEntity]:
        row = (
            self.db.query(SubscriptionLicense)
            .filter(
                SubscriptionLicense.subscription_id == subscription_id,
                SubscriptionLicense.organization_id == organization_id,
                SubscriptionLicense.status == "ACTIVE",
            )
            .first()
        )
        return _to_license(row) if row else None


class SqlAlchemyAssignmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def count_active_for_license_locked(self, license_id: int) -> int:
        return (
            self.db.query(SubscriptionAssignment)
            .filter(
                SubscriptionAssignment.license_id == license_id,
                SubscriptionAssignment.status == "ACTIVE",
            )
            .with_for_update()
            .count()
        )

    def find_active_for_user_and_subscription(self, organization_id: int, subscription_id: int, user_id: int) -> Optional[SubscriptionAssignmentEntity]:
        row = (
            self.db.query(SubscriptionAssignment)
            .filter(
                SubscriptionAssignment.organization_id == organization_id,
                SubscriptionAssignment.subscription_id == subscription_id,
                SubscriptionAssignment.user_id == user_id,
                SubscriptionAssignment.status == "ACTIVE",
            )
            .first()
        )
        return _to_assignment(row) if row else None

    def create(self, assignment: SubscriptionAssignmentEntity) -> SubscriptionAssignmentEntity:
        row = SubscriptionAssignment(
            organization_id=assignment.organization_id,
            subscription_id=assignment.subscription_id,
            license_id=assignment.license_id,
            user_id=assignment.user_id,
            assigned_by=assignment.assigned_by,
            status=assignment.status,
            notes=assignment.notes,
        )
        self.db.add(row)
        self.db.flush()
        return _to_assignment(row)

    def get_active_by_id(self, assignment_id: int, organization_id: int) -> Optional[SubscriptionAssignmentEntity]:
        row = (
            self.db.query(SubscriptionAssignment)
            .filter(
                SubscriptionAssignment.id == assignment_id,
                SubscriptionAssignment.organization_id == organization_id,
                SubscriptionAssignment.status == "ACTIVE",
            )
            .first()
        )
        return _to_assignment(row) if row else None

    def get_by_id(self, assignment_id: int, organization_id: int) -> Optional[SubscriptionAssignmentEntity]:
        row = (
            self.db.query(SubscriptionAssignment)
            .filter(
                SubscriptionAssignment.id == assignment_id,
                SubscriptionAssignment.organization_id == organization_id,
            )
            .first()
        )
        return _to_assignment(row) if row else None

    def list_filtered(
        self,
        organization_id: int,
        *,
        subscription_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[SubscriptionAssignmentEntity]:
        query = self.db.query(SubscriptionAssignment).filter(SubscriptionAssignment.organization_id == organization_id)
        if subscription_id is not None:
            query = query.filter(SubscriptionAssignment.subscription_id == subscription_id)
        if user_id is not None:
            query = query.filter(SubscriptionAssignment.user_id == user_id)
        if status is not None:
            query = query.filter(SubscriptionAssignment.status == status)
        rows = query.order_by(SubscriptionAssignment.assigned_at.desc()).all()
        return [_to_assignment(r) for r in rows]

    def count_active_by_user(self, organization_id: int) -> dict[int, int]:
        rows = (
            self.db.query(SubscriptionAssignment.user_id, func.count(SubscriptionAssignment.id))
            .filter(
                SubscriptionAssignment.organization_id == organization_id,
                SubscriptionAssignment.status == "ACTIVE",
            )
            .group_by(SubscriptionAssignment.user_id)
            .all()
        )
        return {int(uid): int(cnt) for uid, cnt in rows}

    def save(self, assignment: SubscriptionAssignmentEntity) -> SubscriptionAssignmentEntity:
        row = self.db.query(SubscriptionAssignment).filter(SubscriptionAssignment.id == assignment.id).first()
        if not row:
            raise ValueError("Assignment not found")
        row.status = assignment.status
        row.released_at = assignment.released_at
        row.notes = assignment.notes
        self.db.flush()
        return _to_assignment(row)
