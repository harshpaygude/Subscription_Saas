"""Pure domain entities and spend calculations for Governance Service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional, Protocol

from unisora_kit import RequestContext

MONTHS = {
    "monthly": Decimal("1"),
    "annual": Decimal("12"),
    "quarterly": Decimal("3"),
    "weekly": Decimal("12") / Decimal("52"),
}


def normalize_monthly(amount: Any, interval: str) -> Decimal | None:
    if amount is None:
        return None
    norm = (interval or "").lower()
    if norm not in MONTHS:
        return None
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    if norm == "weekly":
        return (dec * Decimal("52") / Decimal("12")).quantize(Decimal("0.000001"))
    return (dec / MONTHS[norm]).quantize(Decimal("0.000001"))


@dataclass
class AlertEntity:
    id: Optional[int]
    organization_id: int
    user_id: Optional[int]
    provider: Optional[str]
    subscription_id: Optional[int]
    category: str
    severity: str
    title: str
    description: str
    is_read: bool
    is_resolved: bool
    dedupe_key: str
    created_at: datetime
    updated_at: datetime


class AlertRepository(Protocol):
    def exists_by_dedupe(self, organization_id: int, dedupe_key: str) -> Optional[AlertEntity]: ...
    def create(self, alert: AlertEntity) -> AlertEntity: ...
    def list_filtered(
        self,
        organization_id: int,
        *,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        read: Optional[bool] = None,
        resolved: Optional[bool] = None,
    ) -> list[AlertEntity]: ...
    def count_unread(self, organization_id: int) -> int: ...
    def get_by_id(self, alert_id: int, organization_id: int) -> Optional[AlertEntity]: ...
    def save(self, alert: AlertEntity) -> AlertEntity: ...


class AuditRepository(Protocol):
    def append_if_new_event(self, *, event_id: str, event_type: str, organization_id: int, actor_id: int, action: str, entity_type: str, entity_id: int, details: Optional[str]) -> bool: ...
    def list_in_range(self, organization_id: int, start_dt: datetime, end_dt: datetime, limit: int = 500) -> list[dict[str, Any]]: ...


class SubscriptionReadPort(Protocol):
    def list_subscriptions(self, ctx: RequestContext) -> list[dict[str, Any]]: ...
    def list_active_assignments(self, ctx: RequestContext) -> list[dict[str, Any]]: ...


class AssetReadPort(Protocol):
    def get_summary(self, ctx: RequestContext) -> dict[str, Any]: ...


class IdentityReadPort(Protocol):
    def get_organization(self, ctx: RequestContext, organization_id: int) -> Optional[dict[str, Any]]: ...
    def list_users(self, ctx: RequestContext) -> list[dict[str, Any]]: ...
    def list_departments(self, ctx: RequestContext) -> list[dict[str, Any]]: ...
