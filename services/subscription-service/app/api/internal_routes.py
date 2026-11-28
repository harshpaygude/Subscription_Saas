"""Internal service-to-service endpoints for Subscription Service."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import commit_with_outbox, get_current_context
from app.domain.entities import (
    SubscriptionAssignmentEntity,
    SubscriptionEntity,
    SubscriptionLicenseEntity,
)
from app.infrastructure.db import get_db
from app.infrastructure.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyLicenseRepository,
    SqlAlchemySubscriptionRepository,
)

router = APIRouter(prefix="/internal", tags=["Internal"])


class BulkAssignSubscriptionsRequest(BaseModel):
    user_id: int
    subscription_ids: list[int]


class OnboardingSubscriptionsRequest(BaseModel):
    subscriptions: list[dict[str, Any]]


class EnsureAndAssignRequest(BaseModel):
    user_id: int
    name: str
    plan: str = "Standard"
    amount: Optional[float] = None


@router.get("/subscriptions")
def list_internal_subscriptions(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    items = SqlAlchemySubscriptionRepository(db).list_all(ctx.organization_id)
    return [
        {
            "id": s.id,
            "organization_id": s.organization_id,
            "provider": s.provider,
            "name": s.name,
            "plan": s.plan,
            "amount": str(s.amount) if s.amount is not None else None,
            "currency": s.currency,
            "billing_interval": s.billing_interval,
            "next_renewal_date": s.next_renewal_date.isoformat() if s.next_renewal_date else None,
            "status": s.status,
            "renewal_type": s.renewal_type,
            "note": s.note,
        }
        for s in items
    ]


@router.get("/subscriptions/{subscription_id}")
def get_internal_subscription(
    subscription_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    s = SqlAlchemySubscriptionRepository(db).get_by_id(subscription_id, ctx.organization_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"id": s.id, "name": s.name, "provider": s.provider, "status": s.status}


@router.get("/assignments/active-counts")
def active_assignment_counts(
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    return {"counts": SqlAlchemyAssignmentRepository(db).count_active_by_user(ctx.organization_id)}


@router.get("/assignments")
def list_internal_assignments(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    rows = SqlAlchemyAssignmentRepository(db).list_filtered(
        ctx.organization_id, user_id=user_id, status=status
    )
    subs = {s.id: s for s in SqlAlchemySubscriptionRepository(db).list_all(ctx.organization_id)}
    return [
        {
            "id": r.id,
            "subscription_id": r.subscription_id,
            "user_id": r.user_id,
            "status": r.status,
            "assigned_at": r.assigned_at.isoformat(),
            "released_at": r.released_at.isoformat() if r.released_at else None,
            "resource_name": subs[r.subscription_id].name if r.subscription_id in subs else None,
            "resource_provider": subs[r.subscription_id].provider if r.subscription_id in subs else None,
        }
        for r in rows
    ]


@router.get("/assignments/{assignment_id}")
def get_internal_assignment(
    assignment_id: int,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    row = SqlAlchemyAssignmentRepository(db).get_by_id(assignment_id, ctx.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="Subscription assignment not found.")
    return {"id": row.id, "subscription_id": row.subscription_id, "user_id": row.user_id, "status": row.status}


@router.post("/subscriptions/bulk-assign")
def bulk_assign_subscriptions(
    payload: BulkAssignSubscriptionsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    subs = SqlAlchemySubscriptionRepository(db)
    lics = SqlAlchemyLicenseRepository(db)
    assigns = SqlAlchemyAssignmentRepository(db)
    now = datetime.utcnow()

    for sub_id in payload.subscription_ids:
        sub = subs.get_by_id(sub_id, ctx.organization_id)
        if not sub or sub.id is None:
            continue
        if assigns.find_active_for_user_and_subscription(ctx.organization_id, sub.id, payload.user_id):
            continue
        lic = lics.get_first_active_for_subscription(sub.id, ctx.organization_id)
        if not lic:
            lic = lics.create(
                SubscriptionLicenseEntity(
                    id=None,
                    organization_id=ctx.organization_id,
                    subscription_id=sub.id,
                    reference=f"{sub.name} Seat",
                    capacity=100,
                    status="ACTIVE",
                    created_at=now,
                    updated_at=now,
                )
            )
        assert lic.id is not None
        assigns.create(
            SubscriptionAssignmentEntity(
                id=None,
                organization_id=ctx.organization_id,
                subscription_id=sub.id,
                license_id=lic.id,
                user_id=payload.user_id,
                assigned_by=ctx.user_id,
                assigned_at=now,
                released_at=None,
                status="ACTIVE",
                notes=None,
            )
        )
    commit_with_outbox(db)
    return {"status": "ok"}


@router.post("/subscriptions/onboarding-import")
def onboarding_import_subscriptions(
    payload: OnboardingSubscriptionsRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    subs = SqlAlchemySubscriptionRepository(db)
    created = 0
    now = datetime.utcnow()
    for sub in payload.subscriptions:
        raw_name = str(sub.get("name") or "").strip()
        raw_provider = str(sub.get("provider") or "").strip().lower()
        if not raw_name or not raw_provider:
            continue
        if subs.find_by_provider_and_name(ctx.organization_id, raw_provider, raw_name):
            continue
        amount_val = None
        if sub.get("amount"):
            try:
                amount_val = Decimal(str(sub["amount"]).replace("$", "").replace(",", "").strip())
            except Exception:
                pass
        s_date = None
        if sub.get("start_date"):
            try:
                s_date = date.fromisoformat(str(sub["start_date"])[:10])
            except Exception:
                pass
        r_date = None
        if sub.get("next_renewal_date"):
            try:
                r_date = date.fromisoformat(str(sub["next_renewal_date"])[:10])
            except Exception:
                pass
        subs.create(
            SubscriptionEntity(
                id=None,
                organization_id=ctx.organization_id,
                user_id=ctx.user_id,
                provider=raw_provider,
                name=raw_name,
                plan=str(sub.get("plan")).strip() if sub.get("plan") else None,
                amount=amount_val,
                currency=(str(sub.get("currency") or "USD")).upper()[:3],
                billing_interval=str(sub.get("billing_interval") or "monthly"),
                start_date=s_date,
                next_renewal_date=r_date,
                status=(str(sub.get("status") or "ACTIVE")).upper(),
                cancellation_date=None,
                source="onboarding_import",
                note=str(sub.get("note")).strip() if sub.get("note") else None,
                renewal_type=(str(sub.get("renewal_type") or "AUTOPAY")).upper(),
                created_at=now,
                updated_at=now,
            )
        )
        created += 1
    commit_with_outbox(db)
    return {"created": created}


@router.post("/subscriptions/ensure-and-assign")
def ensure_and_assign_subscription(
    payload: EnsureAndAssignRequest,
    ctx: RequestContext = Depends(get_current_context),
    db: Session = Depends(get_db),
):
    subs = SqlAlchemySubscriptionRepository(db)
    lics = SqlAlchemyLicenseRepository(db)
    assigns = SqlAlchemyAssignmentRepository(db)
    now = datetime.utcnow()

    sub = subs.find_by_provider(ctx.organization_id, payload.name)
    if not sub:
        sub = subs.create(
            SubscriptionEntity(
                id=None,
                organization_id=ctx.organization_id,
                user_id=ctx.user_id,
                provider=payload.name,
                name=f"{payload.name} Workspace",
                plan=payload.plan,
                amount=Decimal(str(payload.amount if payload.amount is not None else 25.0)),
                currency="USD",
                billing_interval="MONTHLY",
                start_date=None,
                next_renewal_date=None,
                status="ACTIVE",
                cancellation_date=None,
                source="csv_import",
                note=None,
                renewal_type="AUTOPAY",
                created_at=now,
                updated_at=now,
            )
        )
    assert sub.id is not None
    lic = lics.get_first_active_for_subscription(sub.id, ctx.organization_id)
    if not lic:
        lic = lics.create(
            SubscriptionLicenseEntity(
                id=None,
                organization_id=ctx.organization_id,
                subscription_id=sub.id,
                reference=f"{payload.name} Seat",
                capacity=100,
                status="ACTIVE",
                created_at=now,
                updated_at=now,
            )
        )
    assert lic.id is not None
    assigned = False
    if not assigns.find_active_for_user_and_subscription(ctx.organization_id, sub.id, payload.user_id):
        assigns.create(
            SubscriptionAssignmentEntity(
                id=None,
                organization_id=ctx.organization_id,
                subscription_id=sub.id,
                license_id=lic.id,
                user_id=payload.user_id,
                assigned_by=ctx.user_id,
                assigned_at=now,
                released_at=None,
                status="ACTIVE",
                notes=None,
            )
        )
        assigned = True
    commit_with_outbox(db)
    return {"assigned": assigned}
