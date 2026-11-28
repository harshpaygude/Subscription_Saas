"""Dependency injection wiring for Subscription Service."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, ServiceHttpClient, get_request_context
from app.application.license_service import LicenseAssignmentService
from app.application.subscription_service import SubscriptionService
from app.config import settings
from app.infrastructure.adapters import HttpIdentityLookupAdapter, OutboxAuditAdapter
from app.infrastructure.db import get_db
from app.infrastructure.models import OutboxEvent
from app.infrastructure.repositories import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyLicenseRepository,
    SqlAlchemyManualSpendRepository,
    SqlAlchemySubscriptionRepository,
)

get_current_context = get_request_context(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    internal_secret=settings.internal_service_secret,
)

_dispatcher = OutboxDispatcher(
    source_service=settings.service_name,
    internal_secret=settings.internal_service_secret,
)


def _identity_client() -> ServiceHttpClient:
    return ServiceHttpClient(
        base_url=settings.identity_service_url,
        caller_service=settings.service_name,
        internal_secret=settings.internal_service_secret,
    )


def commit_with_outbox(db: Session) -> None:
    db.commit()
    try:
        _dispatcher.flush_pending(db, OutboxEvent)
    except Exception:
        pass


def get_outbox_dispatcher() -> OutboxDispatcher:
    return _dispatcher


def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    return SubscriptionService(
        subscriptions=SqlAlchemySubscriptionRepository(db),
        manual_spend=SqlAlchemyManualSpendRepository(db),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )


def get_license_service(db: Session = Depends(get_db)) -> LicenseAssignmentService:
    return LicenseAssignmentService(
        subscriptions=SqlAlchemySubscriptionRepository(db),
        licenses=SqlAlchemyLicenseRepository(db),
        assignments=SqlAlchemyAssignmentRepository(db),
        identity_lookup=HttpIdentityLookupAdapter(_identity_client()),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )
