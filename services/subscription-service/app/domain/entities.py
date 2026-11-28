"""Pure domain entities and spend calculations for Subscriptions & Licensing."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Optional

MONTHS = {
    "monthly": Decimal("1"),
    "annual": Decimal("12"),
    "quarterly": Decimal("3"),
    "weekly": Decimal("12") / Decimal("52"),
}


@dataclass
class SubscriptionEntity:
    id: Optional[int]
    organization_id: int
    user_id: int
    provider: str
    name: str
    plan: Optional[str]
    amount: Optional[Decimal]
    currency: str
    billing_interval: str
    start_date: Optional[date]
    next_renewal_date: Optional[date]
    status: str
    cancellation_date: Optional[date]
    source: str
    note: Optional[str]
    renewal_type: str
    created_at: datetime
    updated_at: datetime


@dataclass
class ManualSpendEntity:
    id: Optional[int]
    organization_id: int
    user_id: int
    provider: str
    amount: Decimal
    currency: str
    billing_interval: str
    period_start: date
    period_end: Optional[date]
    note: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class SubscriptionLicenseEntity:
    id: Optional[int]
    organization_id: int
    subscription_id: int
    reference: Optional[str]
    capacity: int
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class SubscriptionAssignmentEntity:
    id: Optional[int]
    organization_id: int
    subscription_id: int
    license_id: Optional[int]
    user_id: int
    assigned_by: int
    assigned_at: datetime
    released_at: Optional[datetime]
    status: str
    notes: Optional[str]


def normalize_monthly(amount: Decimal | float | None, interval: str) -> Decimal | None:
    if amount is None:
        return None
    normalized_interval = (interval or "").lower()
    if normalized_interval not in MONTHS:
        return None
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if normalized_interval == "weekly":
        return (dec * Decimal("52") / Decimal("12")).quantize(Decimal("0.000001"))
    return (dec / MONTHS[normalized_interval]).quantize(Decimal("0.000001"))


def month_start(value: date) -> date:
    return value.replace(day=1)


def month_end(value: date) -> date:
    return value.replace(day=monthrange(value.year, value.month)[1])


def upcoming(subscription: SubscriptionEntity, start: date, end: date) -> bool:
    return (
        subscription.status == "ACTIVE"
        and subscription.next_renewal_date is not None
        and start <= subscription.next_renewal_date <= end
    )


def aggregate_subscriptions(subscriptions: Iterable[SubscriptionEntity]) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for item in subscriptions:
        normalized = normalize_monthly(item.amount, item.billing_interval)
        if normalized is not None:
            result[item.currency] = result.get(item.currency, Decimal("0")) + normalized
    return result
