"""Minimal cross-cutting runtime primitives for UniSora microservices."""

from unisora_kit.config import BaseServiceSettings
from unisora_kit.errors import (
    AppError,
    ConflictError,
    DomainValidationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    register_exception_handlers,
)
from unisora_kit.events import (
    DomainEvent,
    OutboxDispatcher,
    OutboxRecordMixin,
    ProcessedEventMixin,
    make_domain_event,
)
from unisora_kit.health import create_health_router
from unisora_kit.http_client import ServiceClientError, ServiceHttpClient
from unisora_kit.logging import (
    CorrelationIdMiddleware,
    configure_logging,
    get_correlation_id,
    get_logger,
)
from unisora_kit.security import (
    RequestContext,
    create_internal_service_token,
    get_request_context,
    require_admin_role,
    verify_internal_service_token,
)

__all__ = [
    "AppError",
    "BaseServiceSettings",
    "ConflictError",
    "CorrelationIdMiddleware",
    "DomainEvent",
    "DomainValidationError",
    "ExternalServiceError",
    "ForbiddenError",
    "NotFoundError",
    "OutboxDispatcher",
    "OutboxRecordMixin",
    "ProcessedEventMixin",
    "RequestContext",
    "ServiceClientError",
    "ServiceHttpClient",
    "ServiceUnavailableError",
    "UnauthorizedError",
    "configure_logging",
    "create_health_router",
    "create_internal_service_token",
    "get_correlation_id",
    "get_logger",
    "get_request_context",
    "make_domain_event",
    "register_exception_handlers",
    "require_admin_role",
    "verify_internal_service_token",
]
