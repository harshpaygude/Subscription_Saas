"""Dependency injection wiring for Asset Service."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, ServiceHttpClient, get_request_context
from app.application.asset_service import AssetService
from app.config import settings
from app.infrastructure.adapters import HttpIdentityLookupAdapter, OutboxAuditAdapter
from app.infrastructure.db import get_db
from app.infrastructure.models import OutboxEvent
from app.infrastructure.repositories import (
    SqlAlchemyAssetAssignmentRepository,
    SqlAlchemyAssetMaintenanceRepository,
    SqlAlchemyAssetRepository,
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


def get_identity_adapter() -> HttpIdentityLookupAdapter:
    return HttpIdentityLookupAdapter(_identity_client())


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(
        assets=SqlAlchemyAssetRepository(db),
        assignments=SqlAlchemyAssetAssignmentRepository(db),
        maintenance=SqlAlchemyAssetMaintenanceRepository(db),
        identity_lookup=get_identity_adapter(),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )
