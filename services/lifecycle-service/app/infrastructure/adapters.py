"""HTTP & Outbox adapters for Lifecycle Service."""
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


class HttpIdentityAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_user(self, ctx: RequestContext, user_id: int) -> dict[str, Any]:
        try:
            return self.client.request("GET", f"/internal/users/{user_id}", ctx=ctx)
        except ServiceClientError as exc:
            if exc.status_code == 404:
                raise DomainValidationError("Employee not found in this organization.") from exc
            raise

    def list_users(self, ctx: RequestContext) -> list[dict[str, Any]]:
        return list(self.client.request("GET", "/internal/users", ctx=ctx) or [])

    def list_departments(self, ctx: RequestContext) -> list[dict[str, Any]]:
        return list(self.client.request("GET", "/internal/departments", ctx=ctx) or [])

    def sync_onboarding_membership(self, ctx: RequestContext, user_id: int, department_id: int, effective_from: date) -> None:
        try:
            self.client.request(
                "POST",
                "/internal/departments/sync-onboarding-membership",
                ctx=ctx,
                json_body={"user_id": user_id, "department_id": department_id, "effective_from": effective_from.isoformat()},
            )
        except ServiceClientError as exc:
            if exc.status_code == 400:
                raise DomainValidationError(exc.message) from exc
            raise

    def deactivate_memberships(self, ctx: RequestContext, user_id: int, effective_to: date) -> None:
        self.client.request(
            "POST",
            "/internal/departments/deactivate-memberships",
            ctx=ctx,
            json_body={"user_id": user_id, "effective_to": effective_to.isoformat()},
        )


class HttpSubscriptionAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def subscription_exists(self, ctx: RequestContext, subscription_id: int) -> bool:
        try:
            self.client.request("GET", f"/internal/subscriptions/{subscription_id}", ctx=ctx)
            return True
        except ServiceClientError as exc:
            if exc.status_code == 404:
                return False
            raise

    def list_user_assignments(self, ctx: RequestContext, user_id: int, status: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"user_id": user_id}
        if status:
            params["status"] = status
        return list(self.client.request("GET", "/internal/assignments", ctx=ctx, params=params) or [])

    def list_all_assignments(self, ctx: RequestContext) -> list[dict[str, Any]]:
        return list(self.client.request("GET", "/internal/assignments", ctx=ctx) or [])

    def get_assignment(self, ctx: RequestContext, assignment_id: int) -> Optional[dict[str, Any]]:
        try:
            return self.client.request("GET", f"/internal/assignments/{assignment_id}", ctx=ctx)
        except ServiceClientError as exc:
            if exc.status_code == 404:
                return None
            raise


class HttpAssetAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_asset(self, ctx: RequestContext, asset_id: int) -> Optional[dict[str, Any]]:
        try:
            return self.client.request("GET", f"/internal/assets/{asset_id}", ctx=ctx)
        except ServiceClientError as exc:
            if exc.status_code == 404:
                return None
            raise

    def list_user_assignments(self, ctx: RequestContext, user_id: int, status: Optional[str] = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"user_id": user_id}
        if status:
            params["status"] = status
        return list(self.client.request("GET", "/internal/assignments", ctx=ctx, params=params) or [])

    def list_all_assignments(self, ctx: RequestContext) -> list[dict[str, Any]]:
        return list(self.client.request("GET", "/internal/assignments", ctx=ctx) or [])

    def get_assignment(self, ctx: RequestContext, assignment_id: int) -> Optional[dict[str, Any]]:
        try:
            return self.client.request("GET", f"/internal/assignments/{assignment_id}", ctx=ctx)
        except ServiceClientError as exc:
            if exc.status_code == 404:
                return None
            raise


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
