"""SQLAlchemy repositories & HTTP read adapters for Governance Service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from unisora_kit import RequestContext, ServiceClientError, ServiceHttpClient
from app.domain.contracts import AlertEntity
from app.infrastructure.models import Alert, AuditLog, ProcessedEvent


def _to_alert(row: Alert) -> AlertEntity:
    return AlertEntity(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        provider=row.provider,
        subscription_id=row.subscription_id,
        category=row.category,
        severity=row.severity,
        title=row.title,
        description=row.description,
        is_read=row.is_read,
        is_resolved=row.is_resolved,
        dedupe_key=row.dedupe_key,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyAlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def exists_by_dedupe(self, organization_id: int, dedupe_key: str) -> Optional[AlertEntity]:
        row = self.db.query(Alert).filter(Alert.organization_id == organization_id, Alert.dedupe_key == dedupe_key).first()
        return _to_alert(row) if row else None

    def create(self, alert: AlertEntity) -> AlertEntity:
        row = Alert(
            organization_id=alert.organization_id,
            user_id=alert.user_id,
            provider=alert.provider,
            subscription_id=alert.subscription_id,
            category=alert.category,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            is_read=alert.is_read,
            is_resolved=alert.is_resolved,
            dedupe_key=alert.dedupe_key,
        )
        self.db.add(row)
        self.db.flush()
        return _to_alert(row)

    def list_filtered(
        self,
        organization_id: int,
        *,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        read: Optional[bool] = None,
        resolved: Optional[bool] = None,
    ) -> list[AlertEntity]:
        query = self.db.query(Alert).filter(Alert.organization_id == organization_id)
        if category:
            query = query.filter(Alert.category == category)
        if severity:
            query = query.filter(Alert.severity == severity)
        if read is not None:
            query = query.filter(Alert.is_read == read)
        if resolved is not None:
            query = query.filter(Alert.is_resolved == resolved)
        return [_to_alert(r) for r in query.order_by(Alert.created_at.desc()).all()]

    def count_unread(self, organization_id: int) -> int:
        return (
            self.db.query(Alert)
            .filter(Alert.organization_id == organization_id, Alert.is_read.is_(False), Alert.is_resolved.is_(False))
            .count()
        )

    def get_by_id(self, alert_id: int, organization_id: int) -> Optional[AlertEntity]:
        row = self.db.query(Alert).filter(Alert.id == alert_id, Alert.organization_id == organization_id).first()
        return _to_alert(row) if row else None

    def save(self, alert: AlertEntity) -> AlertEntity:
        row = self.db.query(Alert).filter(Alert.id == alert.id, Alert.organization_id == alert.organization_id).first()
        if not row:
            raise ValueError("Alert not found")
        row.is_read = alert.is_read
        row.is_resolved = alert.is_resolved
        self.db.flush()
        return _to_alert(row)


class SqlAlchemyAuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def append_if_new_event(
        self,
        *,
        event_id: str,
        event_type: str,
        organization_id: int,
        actor_id: int,
        action: str,
        entity_type: str,
        entity_id: int,
        details: Optional[str],
    ) -> bool:
        existing = self.db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
        if existing:
            return False
        self.db.add(ProcessedEvent(event_id=event_id, event_type=event_type))
        self.db.add(
            AuditLog(
                organization_id=organization_id,
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
        )
        try:
            self.db.flush()
            return True
        except IntegrityError:
            self.db.rollback()
            return False

    def list_in_range(self, organization_id: int, start_dt: datetime, end_dt: datetime, limit: int = 500) -> list[dict[str, Any]]:
        rows = (
            self.db.query(AuditLog)
            .filter(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at >= start_dt,
                AuditLog.created_at <= end_dt,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "actor_id": r.actor_id,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "details": r.details,
                "created_at": r.created_at,
            }
            for r in rows
        ]


class HttpSubscriptionReadAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def list_subscriptions(self, ctx: RequestContext) -> list[dict[str, Any]]:
        try:
            return list(self.client.request("GET", "/internal/subscriptions", ctx=ctx) or [])
        except ServiceClientError:
            return []

    def list_active_assignments(self, ctx: RequestContext) -> list[dict[str, Any]]:
        try:
            return list(self.client.request("GET", "/internal/assignments", ctx=ctx, params={"status": "ACTIVE"}) or [])
        except ServiceClientError:
            return []


class HttpAssetReadAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_summary(self, ctx: RequestContext) -> dict[str, Any]:
        try:
            return dict(self.client.request("GET", "/internal/assets/summary", ctx=ctx) or {})
        except ServiceClientError:
            return {"total": 0, "assigned": 0, "available": 0}


class HttpIdentityReadAdapter:
    def __init__(self, client: ServiceHttpClient):
        self.client = client

    def get_organization(self, ctx: RequestContext, organization_id: int) -> Optional[dict[str, Any]]:
        try:
            return self.client.request("GET", f"/internal/organizations/{organization_id}", ctx=ctx)
        except ServiceClientError:
            return None

    def list_users(self, ctx: RequestContext) -> list[dict[str, Any]]:
        try:
            return list(self.client.request("GET", "/internal/users", ctx=ctx) or [])
        except ServiceClientError:
            return []

    def list_departments(self, ctx: RequestContext) -> list[dict[str, Any]]:
        try:
            return list(self.client.request("GET", "/internal/departments", ctx=ctx) or [])
        except ServiceClientError:
            return []
