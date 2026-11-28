"""HTTP routes & idempotent event ingestion for Governance Service."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from unisora_kit import RequestContext, ServiceHttpClient, get_request_context, verify_internal_service_token
from app.application.governance_service import AlertService, AnalyticsService
from app.config import settings
from app.infrastructure.adapters import (
    HttpAssetReadAdapter,
    HttpIdentityReadAdapter,
    HttpSubscriptionReadAdapter,
    SqlAlchemyAlertRepository,
    SqlAlchemyAuditRepository,
)
from app.infrastructure.db import get_db

get_current_context = get_request_context(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    internal_secret=settings.internal_service_secret,
)

alerts_router = APIRouter(prefix="/alerts", tags=["Alerts"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])
internal_router = APIRouter(prefix="/internal", tags=["Internal"])


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    provider: Optional[str]
    subscription_id: Optional[int]
    category: str
    severity: str
    title: str
    description: str
    is_read: bool
    is_resolved: bool
    created_at: object
    updated_at: object


class AlertCreate(BaseModel):
    category: str = Field(min_length=1, max_length=40)
    severity: str = Field(default="info", min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    provider: Optional[str] = None
    subscription_id: Optional[int] = None
    dedupe_key: str = Field(min_length=1, max_length=255)


class IncomingDomainEvent(BaseModel):
    event_id: str
    event_type: str
    event_version: str = "1.0"
    source_service: str
    occurred_at: str
    correlation_id: Optional[str] = None
    payload: dict[str, Any]


def _client(url: str) -> ServiceHttpClient:
    return ServiceHttpClient(
        base_url=url,
        caller_service=settings.service_name,
        internal_secret=settings.internal_service_secret,
    )


def get_alert_service(db: Session = Depends(get_db)) -> AlertService:
    return AlertService(
        alerts=SqlAlchemyAlertRepository(db),
        subscriptions=HttpSubscriptionReadAdapter(_client(settings.subscription_service_url)),
    )


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(
        subscriptions=HttpSubscriptionReadAdapter(_client(settings.subscription_service_url)),
        assets=HttpAssetReadAdapter(_client(settings.asset_service_url)),
        identity=HttpIdentityReadAdapter(_client(settings.identity_service_url)),
        audits=SqlAlchemyAuditRepository(db),
    )


@alerts_router.post("", response_model=AlertResponse, status_code=201)
def create_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    item = service.create_alert(ctx=ctx, data=payload.model_dump())
    db.commit()
    return item


@alerts_router.get("", response_model=list[AlertResponse])
def list_alerts(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    read: Optional[bool] = None,
    resolved: Optional[bool] = None,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    items = service.list_alerts(ctx, category=category, severity=severity, read=read, resolved=resolved)
    db.commit()
    return items


@alerts_router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    count = service.unread_count(ctx)
    db.commit()
    return {"count": count}


@alerts_router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    return service.get_alert(ctx.organization_id, alert_id)


@alerts_router.post("/{alert_id}/read", response_model=AlertResponse)
def mark_read(
    alert_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    item = service.mark_read(ctx.organization_id, alert_id)
    db.commit()
    return item


@alerts_router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: AlertService = Depends(get_alert_service),
):
    item = service.resolve_alert(ctx.organization_id, alert_id)
    db.commit()
    return item


@analytics_router.get("/summary")
def analytics_summary(
    days: int = Query(30, ge=1, le=366),
    ctx: RequestContext = Depends(get_current_context),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.summary(ctx, days)


@analytics_router.get("/audit-export")
def audit_export(
    range_type: str = Query("monthly", description="1year, 6months, monthly, or custom"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    ctx: RequestContext = Depends(get_current_context),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return service.audit_export(ctx, range_type=range_type, start_date=start_date, end_date=end_date)


@internal_router.post("/events")
def ingest_event(
    event: IncomingDomainEvent,
    x_internal_service_token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    if not x_internal_service_token or not verify_internal_service_token(
        x_internal_service_token, settings.internal_service_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid internal service signature")

    if event.event_type == "audit.recorded":
        p = event.payload
        repo = SqlAlchemyAuditRepository(db)
        inserted = repo.append_if_new_event(
            event_id=event.event_id,
            event_type=event.event_type,
            organization_id=int(p["organization_id"]),
            actor_id=int(p["actor_id"]),
            action=str(p["action"]),
            entity_type=str(p["entity_type"]),
            entity_id=int(p["entity_id"]),
            details=json.dumps(p.get("details"), default=str) if p.get("details") else None,
        )
        db.commit()
        return {"status": "accepted", "deduplicated": not inserted}

    return {"status": "ignored", "event_type": event.event_type}
