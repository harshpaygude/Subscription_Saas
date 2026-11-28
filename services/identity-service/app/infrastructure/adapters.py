"""HTTP adapters and Transactional Outbox event publisher for Identity Service."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

from unisora_kit import (
    ConflictError,
    DomainValidationError,
    OutboxDispatcher,
    RequestContext,
    ServiceClientError,
    ServiceHttpClient,
    make_domain_event,
)
from app.config import settings
from app.infrastructure.models import OutboxEvent


class OutboxAuditAdapter:
    def __init__(self, db: Session, dispatcher: OutboxDispatcher):
        self.db = db
        self.dispatcher = dispatcher

    def record(
        self,
        *,
        organization_id: int,
        actor_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        event = make_domain_event(
            event_type="audit.recorded",
            source_service=settings.service_name,
            payload={
                "organization_id": organization_id,
                "actor_id": actor_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details,
            },
        )
        target = f"{settings.governance_service_url}/internal/events" if settings.governance_service_url else ""
        self.dispatcher.enqueue(self.db, OutboxEvent, event=event, target_url=target)


class HttpAssetProvisioningAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_active_assignment_counts(self, ctx: RequestContext) -> dict[int, int]:
        try:
            data = self.client.request("GET", "/internal/assignments/active-counts", ctx=ctx)
            return {int(k): int(v) for k, v in (data or {}).get("counts", {}).items()}
        except ServiceClientError:
            return {}

    def validate_available_assets(self, ctx: RequestContext, asset_ids: list[int]) -> list[int]:
        if not asset_ids:
            return []
        try:
            data = self.client.request("POST", "/internal/assets/validate-available", ctx=ctx, json_body={"asset_ids": asset_ids})
            return list(data.get("asset_ids", []))
        except ServiceClientError as exc:
            if exc.status_code == 409:
                raise ConflictError(exc.message) from exc
            if exc.status_code == 400:
                raise DomainValidationError(exc.message) from exc
            raise

    def assign_assets_to_user(self, ctx: RequestContext, user_id: int, asset_ids: list[int], reassign: bool = False) -> None:
        if not asset_ids:
            return
        self.client.request(
            "POST",
            "/internal/assets/bulk-assign",
            ctx=ctx,
            json_body={"user_id": user_id, "asset_ids": asset_ids, "reassign": reassign},
        )

    def create_and_assign_assets(self, ctx: RequestContext, assets: list[dict[str, Any]], user_lookup: dict[str, int]) -> tuple[int, int]:
        if not assets:
            return 0, 0
        data = self.client.request(
            "POST",
            "/internal/assets/onboarding-import",
            ctx=ctx,
            json_body={"assets": assets, "user_lookup": user_lookup},
        )
        return int(data.get("created", 0)), int(data.get("assigned", 0))


class HttpSubscriptionProvisioningAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_active_assignment_counts(self, ctx: RequestContext) -> dict[int, int]:
        try:
            data = self.client.request("GET", "/internal/assignments/active-counts", ctx=ctx)
            return {int(k): int(v) for k, v in (data or {}).get("counts", {}).items()}
        except ServiceClientError:
            return {}

    def assign_subscriptions_to_user(self, ctx: RequestContext, user_id: int, subscription_ids: list[int]) -> None:
        if not subscription_ids:
            return
        self.client.request(
            "POST",
            "/internal/subscriptions/bulk-assign",
            ctx=ctx,
            json_body={"user_id": user_id, "subscription_ids": subscription_ids},
        )

    def import_subscriptions(self, ctx: RequestContext, subscriptions: list[dict[str, Any]]) -> int:
        if not subscriptions:
            return 0
        data = self.client.request(
            "POST",
            "/internal/subscriptions/onboarding-import",
            ctx=ctx,
            json_body={"subscriptions": subscriptions},
        )
        return int(data.get("created", 0))

    def ensure_subscription_and_assign(self, ctx: RequestContext, user_id: int, sub_name: str, plan: str, amount: Optional[float]) -> bool:
        data = self.client.request(
            "POST",
            "/internal/subscriptions/ensure-and-assign",
            ctx=ctx,
            json_body={"user_id": user_id, "name": sub_name, "plan": plan, "amount": amount},
        )
        return bool(data.get("assigned", False))


class HttpLifecycleProvisioningAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def ensure_active_lifecycle(self, ctx: RequestContext, user_id: int, joined_at: date) -> None:
        try:
            self.client.request(
                "POST",
                "/internal/lifecycles/ensure-active",
                ctx=ctx,
                json_body={"user_id": user_id, "joined_at": joined_at.isoformat()},
            )
        except ServiceClientError:
            pass


class HttpIntegrationProvisioningAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def seed_connections(self, ctx: RequestContext, integrations: list[dict[str, Any]]) -> None:
        if not integrations:
            return
        self.client.request(
            "POST",
            "/internal/integrations/seed-connections",
            ctx=ctx,
            json_body={"connections": integrations},
        )
