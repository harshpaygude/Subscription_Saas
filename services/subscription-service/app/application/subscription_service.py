"""Application service for Subscriptions and Manual Spend (DIP)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from unisora_kit import NotFoundError
from app.domain.entities import (
    ManualSpendEntity,
    SubscriptionEntity,
    aggregate_subscriptions,
    normalize_monthly,
    upcoming,
)
from app.domain.ports import AuditEventPort, ManualSpendRepository, SubscriptionRepository


class SubscriptionService:
    def __init__(
        self,
        subscriptions: SubscriptionRepository,
        manual_spend: ManualSpendRepository,
        audit: AuditEventPort,
    ):
        self.subscriptions = subscriptions
        self.manual_spend = manual_spend
        self.audit = audit

    def create_subscription(self, *, organization_id: int, user_id: int, data: dict[str, Any]) -> SubscriptionEntity:
        renewal_type = (data.get("renewal_type") or "AUTOPAY").upper()
        now = datetime.utcnow()
        created = self.subscriptions.create(
            SubscriptionEntity(
                id=None,
                organization_id=organization_id,
                user_id=user_id,
                provider=data["provider"],
                name=data["name"],
                plan=data.get("plan"),
                amount=data.get("amount"),
                currency=data.get("currency", "USD"),
                billing_interval=data["billing_interval"],
                start_date=data.get("start_date"),
                next_renewal_date=data.get("next_renewal_date"),
                status=data.get("status", "ACTIVE"),
                cancellation_date=None,
                source="manual",
                note=data.get("note"),
                renewal_type=renewal_type,
                created_at=now,
                updated_at=now,
            )
        )
        assert created.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=user_id,
            action="subscription.created",
            entity_type="subscription",
            entity_id=created.id,
        )
        return created

    def get_subscription(self, organization_id: int, subscription_id: int) -> SubscriptionEntity:
        item = self.subscriptions.get_by_id(subscription_id, organization_id)
        if not item:
            raise NotFoundError("Subscription not found.")
        return item

    def list_subscriptions(
        self,
        organization_id: int,
        *,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        billing_interval: Optional[str] = None,
        renewal_before: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[SubscriptionEntity]:
        return self.subscriptions.list_filtered(
            organization_id,
            provider=provider,
            status=status,
            billing_interval=billing_interval,
            renewal_before=renewal_before,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    def summary(self, organization_id: int) -> dict[str, Any]:
        items = self.subscriptions.list_all(organization_id)
        totals = aggregate_subscriptions(items)
        return {
            "active_count": sum(item.status == "ACTIVE" for item in items),
            "cancelled_count": sum(item.status == "CANCELLED" for item in items),
            "totals_by_currency": {key: str(value) for key, value in totals.items()},
        }

    def upcoming_renewals(self, organization_id: int, days: int) -> list[SubscriptionEntity]:
        start = date.today()
        end = start + timedelta(days=days)
        return [item for item in self.subscriptions.list_all(organization_id) if upcoming(item, start, end)]

    def monthly_spend(self, organization_id: int) -> dict[str, Any]:
        subs = [s for s in self.subscriptions.list_all(organization_id) if s.status == "ACTIVE"]
        manual = self.manual_spend.list_all(organization_id)
        rows = []
        totals: dict[str, Decimal] = {}
        for item in subs:
            normalized = normalize_monthly(item.amount, item.billing_interval)
            if normalized is None:
                continue
            totals[item.currency] = totals.get(item.currency, Decimal("0")) + normalized
            rows.append(
                {
                    "service": item.provider,
                    "name": item.name,
                    "monthly_spend": str(normalized),
                    "currency": item.currency,
                    "billing_source": item.source,
                    "billing_period": item.billing_interval,
                    "last_updated": item.updated_at,
                    "status": "available",
                }
            )
        for item in manual:
            normalized = normalize_monthly(item.amount, item.billing_interval)
            if normalized is None:
                continue
            totals[item.currency] = totals.get(item.currency, Decimal("0")) + normalized
            rows.append(
                {
                    "service": item.provider,
                    "name": item.provider,
                    "monthly_spend": str(normalized),
                    "currency": item.currency,
                    "billing_source": "manual",
                    "billing_period": item.period_start,
                    "last_updated": item.updated_at,
                    "status": "available",
                }
            )
        return {
            "totals_by_currency": {key: str(value) for key, value in totals.items()},
            "services": rows,
        }

    def upsert_manual_spend(self, *, organization_id: int, user_id: int, data: dict[str, Any]) -> ManualSpendEntity:
        now = datetime.utcnow()
        return self.manual_spend.upsert(
            ManualSpendEntity(
                id=None,
                organization_id=organization_id,
                user_id=user_id,
                provider=data["provider"],
                amount=data["amount"],
                currency=data["currency"],
                billing_interval=data["billing_interval"],
                period_start=data["period_start"],
                period_end=data.get("period_end"),
                note=data.get("note"),
                created_at=now,
                updated_at=now,
            )
        )

    def update_subscription(self, *, organization_id: int, subscription_id: int, updates: dict[str, Any]) -> SubscriptionEntity:
        item = self.get_subscription(organization_id, subscription_id)
        if "renewal_type" in updates and updates["renewal_type"]:
            updates["renewal_type"] = str(updates["renewal_type"]).upper()
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)
        return self.subscriptions.save(item)

    def cancel_subscription(self, *, organization_id: int, actor_id: int, subscription_id: int) -> SubscriptionEntity:
        item = self.get_subscription(organization_id, subscription_id)
        item.status = "CANCELLED"
        item.cancellation_date = date.today()
        saved = self.subscriptions.save(item)
        assert saved.id is not None
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="subscription.cancelled",
            entity_type="subscription",
            entity_id=saved.id,
        )
        return saved

    def delete_subscription(self, *, organization_id: int, actor_id: int, subscription_id: int) -> None:
        self.get_subscription(organization_id, subscription_id)
        self.subscriptions.delete(subscription_id, organization_id)
        self.audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="subscription.deleted",
            entity_type="subscription",
            entity_id=subscription_id,
        )
