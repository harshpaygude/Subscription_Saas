"""Application services for Alerts, Portfolio Analytics, and Audit Export."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Optional

from unisora_kit import NotFoundError, RequestContext
from app.domain.contracts import (
    AlertEntity,
    AlertRepository,
    AssetReadPort,
    AuditRepository,
    IdentityReadPort,
    SubscriptionReadPort,
    normalize_monthly,
)


class AlertService:
    def __init__(self, alerts: AlertRepository, subscriptions: SubscriptionReadPort):
        self.alerts = alerts
        self.subscriptions = subscriptions

    def sync_renewal_alerts(self, ctx: RequestContext) -> None:
        today = date.today()
        items = self.subscriptions.list_subscriptions(ctx)
        now = datetime.utcnow()

        for item in items:
            if item.get("status") != "ACTIVE" or not item.get("next_renewal_date"):
                continue
            renewal_date = date.fromisoformat(str(item["next_renewal_date"])[:10])
            days_left = (renewal_date - today).days
            if days_left < -7:
                continue

            raw_type = (item.get("renewal_type") or "AUTOPAY").upper()
            note_text = (item.get("note") or "").lower()
            if "manual" in note_text or "invoice" in note_text:
                is_autopay = "auto" in raw_type.lower() and "manual" not in raw_type.lower()
            else:
                is_autopay = "MANUAL" not in raw_type

            mode_label = "Auto-Pay" if is_autopay else "Manual Invoice"
            amt = item.get("amount")
            currency = item.get("currency") or "USD"
            cost_str = f" ({currency} {float(amt):,.2f})" if amt is not None else ""
            sub_id = int(item["id"])
            sub_name = str(item["name"])
            sub_plan = item.get("plan") or "Standard"
            sub_provider = item.get("provider")

            if 1 < days_left <= 30:
                key_30d = f"renewal-30d:{sub_id}:{renewal_date.isoformat()}"
                if not self.alerts.exists_by_dedupe(ctx.organization_id, key_30d):
                    desc = (
                        f"Auto-Pay Renewal in {days_left} days: Your {sub_name} subscription ({sub_plan}) is scheduled to automatically charge{cost_str} on {renewal_date.isoformat()}. Review license seat allocations and payment card prior to renewal execution."
                        if is_autopay
                        else f"Manual Renewal Notice ({days_left} days remaining): Your {sub_name} contract ({sub_plan}) expires on {renewal_date.isoformat()}{cost_str}. Submit purchase order or contact vendor to approve payment and prevent service disruption."
                    )
                    self.alerts.create(
                        AlertEntity(
                            id=None,
                            organization_id=ctx.organization_id,
                            user_id=ctx.user_id,
                            provider=sub_provider,
                            subscription_id=sub_id,
                            category="renewal",
                            severity="info",
                            title=f"{sub_name}: 30-Day Renewal Notice ({mode_label})",
                            description=desc,
                            is_read=False,
                            is_resolved=False,
                            dedupe_key=key_30d,
                            created_at=now,
                            updated_at=now,
                        )
                    )

            if 0 <= days_left <= 1:
                key_1d = f"renewal-1d:{sub_id}:{renewal_date.isoformat()}"
                if not self.alerts.exists_by_dedupe(ctx.organization_id, key_1d):
                    timing = "tomorrow" if days_left == 1 else "today"
                    if is_autopay:
                        desc = f"Final Auto-Pay Notice: {sub_name} will be automatically charged{cost_str} {timing} ({renewal_date.isoformat()}). Ensure your company payment method has sufficient funds to avoid billing issues."
                        title = f"URGENT: {sub_name} Auto-Renews {timing.capitalize()} ({mode_label})"
                    else:
                        desc = f"Urgent Renewal Action: {sub_name} subscription contract expires {timing} ({renewal_date.isoformat()}){cost_str}. Settle vendor invoice or process purchase order immediately to maintain uninterrupted access."
                        title = f"ACTION REQUIRED: {sub_name} Renews {timing.capitalize()} ({mode_label})"
                    self.alerts.create(
                        AlertEntity(
                            id=None,
                            organization_id=ctx.organization_id,
                            user_id=ctx.user_id,
                            provider=sub_provider,
                            subscription_id=sub_id,
                            category="renewal",
                            severity="warning",
                            title=title,
                            description=desc,
                            is_read=False,
                            is_resolved=False,
                            dedupe_key=key_1d,
                            created_at=now,
                            updated_at=now,
                        )
                    )

    def create_alert(self, *, ctx: RequestContext, data: dict[str, Any]) -> AlertEntity:
        existing = self.alerts.exists_by_dedupe(ctx.organization_id, data["dedupe_key"])
        if existing:
            return existing
        now = datetime.utcnow()
        return self.alerts.create(
            AlertEntity(
                id=None,
                organization_id=ctx.organization_id,
                user_id=ctx.user_id,
                provider=data.get("provider"),
                subscription_id=data.get("subscription_id"),
                category=data["category"],
                severity=data.get("severity", "info"),
                title=data["title"],
                description=data["description"],
                is_read=False,
                is_resolved=False,
                dedupe_key=data["dedupe_key"],
                created_at=now,
                updated_at=now,
            )
        )

    def list_alerts(self, ctx: RequestContext, **filters) -> list[AlertEntity]:
        self.sync_renewal_alerts(ctx)
        return self.alerts.list_filtered(ctx.organization_id, **filters)

    def unread_count(self, ctx: RequestContext) -> int:
        self.sync_renewal_alerts(ctx)
        return self.alerts.count_unread(ctx.organization_id)

    def get_alert(self, organization_id: int, alert_id: int) -> AlertEntity:
        alert = self.alerts.get_by_id(alert_id, organization_id)
        if not alert:
            raise NotFoundError("Alert not found.")
        return alert

    def mark_read(self, organization_id: int, alert_id: int) -> AlertEntity:
        alert = self.get_alert(organization_id, alert_id)
        alert.is_read = True
        return self.alerts.save(alert)

    def resolve_alert(self, organization_id: int, alert_id: int) -> AlertEntity:
        alert = self.get_alert(organization_id, alert_id)
        alert.is_resolved = True
        alert.is_read = True
        return self.alerts.save(alert)


class AnalyticsService:
    def __init__(
        self,
        subscriptions: SubscriptionReadPort,
        assets: AssetReadPort,
        identity: IdentityReadPort,
        audits: AuditRepository,
    ):
        self.subscriptions = subscriptions
        self.assets = assets
        self.identity = identity
        self.audits = audits

    @staticmethod
    def _aggregate_by_currency_and_provider(active: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
        totals: dict[str, Decimal] = {}
        by_provider: dict[str, dict[str, str]] = {}
        for item in active:
            normalized = normalize_monthly(item.get("amount"), item.get("billing_interval", ""))
            if normalized is None:
                continue
            curr = str(item.get("currency") or "USD")
            totals[curr] = totals.get(curr, Decimal("0")) + normalized
            prov = str(item["provider"])
            row = by_provider.setdefault(prov, {"currency": curr, "monthly_spend": "0.000000", "data_status": "available"})
            if row["currency"] != curr:
                row["data_status"] = "multiple_currencies"
            row["monthly_spend"] = str((Decimal(row["monthly_spend"]) + normalized).quantize(Decimal("0.000001")))
        return {k: str(v) for k, v in totals.items()}, by_provider

    @staticmethod
    def _is_upcoming(item: dict[str, Any], start: date, end: date) -> bool:
        if item.get("status") != "ACTIVE" or not item.get("next_renewal_date"):
            return False
        d = date.fromisoformat(str(item["next_renewal_date"])[:10])
        return start <= d <= end

    def summary(self, ctx: RequestContext, days: int) -> dict[str, Any]:
        items = self.subscriptions.list_subscriptions(ctx)
        active = [i for i in items if i.get("status") == "ACTIVE"]
        totals_by_currency, by_provider = self._aggregate_by_currency_and_provider(active)
        start = date.today()
        end = start + timedelta(days=days)
        depts = [d for d in self.identity.list_departments(ctx) if d.get("is_active")]
        asset_summary = self.assets.get_summary(ctx)
        active_licenses = len(self.subscriptions.list_active_assignments(ctx))
        return {
            "active_subscriptions": len(active),
            "cancelled_subscriptions": sum(1 for i in items if i.get("status") == "CANCELLED"),
            "upcoming_renewals": sum(1 for i in items if self._is_upcoming(i, start, end)),
            "totals_by_currency": totals_by_currency,
            "by_provider": by_provider,
            "departments": len(depts),
            "assets": {
                "total": asset_summary.get("total", 0),
                "assigned": asset_summary.get("assigned", 0),
                "available": asset_summary.get("available", 0),
            },
            "license_utilization": active_licenses,
            "historical": [],
            "historical_note": "Historical snapshots begin when collection is implemented; no past values are fabricated.",
        }

    def audit_export(
        self,
        ctx: RequestContext,
        *,
        range_type: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> dict[str, Any]:
        today = date.today()
        if range_type == "1year":
            calc_start, calc_end = today - timedelta(days=365), today
        elif range_type == "6months":
            calc_start, calc_end = today - timedelta(days=180), today
        elif range_type == "monthly":
            calc_start, calc_end = today - timedelta(days=30), today
        else:
            try:
                calc_start = date.fromisoformat(start_date) if start_date else (today - timedelta(days=30))
            except Exception:
                calc_start = today - timedelta(days=30)
            try:
                calc_end = date.fromisoformat(end_date) if end_date else today
            except Exception:
                calc_end = today
        if calc_start > calc_end:
            calc_start, calc_end = calc_end, calc_start

        logs = self.audits.list_in_range(
            ctx.organization_id, datetime.combine(calc_start, time.min), datetime.combine(calc_end, time.max)
        )
        users_by_id = {u["id"]: u.get("email") for u in self.identity.list_users(ctx)}
        items = self.subscriptions.list_subscriptions(ctx)
        active = [i for i in items if i.get("status") == "ACTIVE"]
        totals_by_currency, by_provider = self._aggregate_by_currency_and_provider(active)
        org = self.identity.get_organization(ctx, ctx.organization_id)

        return {
            "organization_id": ctx.organization_id,
            "organization_name": org["name"] if org else "UniSora Workspace",
            "generated_at": datetime.utcnow().isoformat(),
            "range_type": range_type,
            "start_date": calc_start.isoformat(),
            "end_date": calc_end.isoformat(),
            "summary": {
                "active_subscriptions": len(active),
                "cancelled_subscriptions": sum(1 for i in items if i.get("status") == "CANCELLED"),
                "upcoming_renewals": sum(1 for i in items if self._is_upcoming(i, calc_start, calc_end)),
                "totals_by_currency": totals_by_currency,
            },
            "by_provider": by_provider,
            "subscriptions": [
                {
                    "id": s["id"],
                    "provider": s["provider"],
                    "currency": s["currency"],
                    "amount": str(s["amount"]),
                    "billing_interval": s["billing_interval"],
                    "status": s["status"],
                    "renewal_date": s.get("next_renewal_date"),
                }
                for s in items
            ],
            "audit_logs": [
                {
                    "id": log["id"],
                    "created_at": log["created_at"].isoformat(),
                    "actor_email": users_by_id.get(log["actor_id"], "system"),
                    "action": log["action"],
                    "entity_type": log["entity_type"],
                    "entity_id": log["entity_id"],
                    "details": log["details"],
                }
                for log in logs
            ],
        }
