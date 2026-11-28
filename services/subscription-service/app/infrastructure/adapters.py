"""HTTP & Outbox adapters for Subscription Service."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from unisora_kit import (
    OutboxDispatcher,
    RequestContext,
    ServiceClientError,
    ServiceHttpClient,
    make_domain_event,
)
from app.config import settings
from app.infrastructure.models import OutboxEvent


class HttpIdentityLookupAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def user_exists_in_org(self, ctx: RequestContext, user_id: int) -> bool:
        try:
            self.client.request("GET", f"/internal/users/{user_id}", ctx=ctx)
            return True
        except ServiceClientError as exc:
            if exc.status_code == 404:
                return False
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
