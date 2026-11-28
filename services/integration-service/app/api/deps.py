"""Dependency injection wiring for Integration Service."""
from __future__ import annotations

from unisora_kit import get_request_context
from app.config import settings

get_current_context = get_request_context(
    jwt_secret=settings.jwt_secret_key,
    jwt_algorithm=settings.jwt_algorithm,
    internal_secret=settings.internal_service_secret,
)
