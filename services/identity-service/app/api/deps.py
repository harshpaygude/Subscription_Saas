"""Composition root / FastAPI dependency injection for Identity Service."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, ServiceHttpClient, get_request_context
from app.application.auth_service import AuthService
from app.application.department_service import DepartmentService
from app.application.employee_service import EmployeeService
from app.application.organization_service import OrganizationService
from app.config import settings
from app.infrastructure.adapters import (
    HttpAssetProvisioningAdapter,
    HttpIntegrationProvisioningAdapter,
    HttpLifecycleProvisioningAdapter,
    HttpSubscriptionProvisioningAdapter,
    OutboxAuditAdapter,
)
from app.infrastructure.db import get_db
from app.infrastructure.models import OutboxEvent
from app.infrastructure.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.security import BcryptPasswordHasher, JoseTokenIssuer

get_current_context = get_request_context(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    internal_secret=settings.internal_service_secret,
)

_hasher = BcryptPasswordHasher()
_token_issuer = JoseTokenIssuer()
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


def get_outbox_dispatcher() -> OutboxDispatcher:
    return _dispatcher


def commit_with_outbox(db: Session) -> None:
    db.commit()
    try:
        _dispatcher.flush_pending(db, OutboxEvent)
    except Exception:
        pass


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(db),
        organizations=SqlAlchemyOrganizationRepository(db),
        hasher=_hasher,
        tokens=_token_issuer,
        audit=OutboxAuditAdapter(db, _dispatcher),
        token_expire_minutes=settings.access_token_expire_minutes,
    )


def get_department_service(db: Session = Depends(get_db)) -> DepartmentService:
    return DepartmentService(
        departments=SqlAlchemyDepartmentRepository(db),
        users=SqlAlchemyUserRepository(db),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )


def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
    return OrganizationService(
        organizations=SqlAlchemyOrganizationRepository(db),
        users=SqlAlchemyUserRepository(db),
        departments=SqlAlchemyDepartmentRepository(db),
        hasher=_hasher,
        lifecycle_port=HttpLifecycleProvisioningAdapter(_client(settings.lifecycle_service_url)),
        asset_port=HttpAssetProvisioningAdapter(_client(settings.asset_service_url)),
        subscription_port=HttpSubscriptionProvisioningAdapter(_client(settings.subscription_service_url)),
        integration_port=HttpIntegrationProvisioningAdapter(_client(settings.integration_service_url)),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )


def get_employee_service(db: Session = Depends(get_db)) -> EmployeeService:
    return EmployeeService(
        users=SqlAlchemyUserRepository(db),
        departments=SqlAlchemyDepartmentRepository(db),
        hasher=_hasher,
        asset_port=HttpAssetProvisioningAdapter(_client(settings.asset_service_url)),
        subscription_port=HttpSubscriptionProvisioningAdapter(_client(settings.subscription_service_url)),
        lifecycle_port=HttpLifecycleProvisioningAdapter(_client(settings.lifecycle_service_url)),
        audit=OutboxAuditAdapter(db, _dispatcher),
    )
