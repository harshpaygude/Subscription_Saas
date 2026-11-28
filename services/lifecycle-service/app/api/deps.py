"""Dependency injection wiring for Lifecycle Service."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, ServiceHttpClient, get_request_context
from app.application.lifecycle_service import LifecycleService
from app.config import settings
from app.infrastructure.adapters import (
    HttpAssetAdapter,
    HttpIdentityAdapter,
    HttpSubscriptionAdapter,
    OutboxAuditAdapter,
)
from app.infrastructure.db import get_db
from app.infrastructure.models import OutboxEvent
from app.infrastructure.repositories import SqlAlchemyLifecycleRepository, SqlAlchemyLifecycleTaskRepository

get_current_context = get_request_context(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    internal_secret=settings.internal_service_secret,
)

_dispatcher = OutboxDispatcher(
    source_service=settings.service_name,
    internal_secret=settings.internal_service_secret,
)


def _client(base_url: str) -> ServiceHttpClient:
    return ServiceHttpClient(
        base_url=base_url,
        caller_service=settings.service_name,
        internal_secret=settings.internal_service_secret,
    )


def commit_with_outbox(db: Session) -> None:
    db.commit()
    try:
        _dispatcher.flush_pending(db, OutboxEvent)
    except Exception:
        pass


def get_lifecycle_service(db: Session = Depends(get_db)) -> LifecycleService:
    return LifecycleService(
        lifecycles=SqlAlchemyLifecycleRepository(db),
        tasks=SqlAlchemyLifecycleTaskRepository(db),
        identity=HttpIdentityAdapter(_client(settings.identity_service_url)),
        subscriptions=HttpSubscriptionAdapter(_client(settings.subscription_service_url)),
        assets=HttpAssetAdapter(_client(settings.asset_service_url)),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )
