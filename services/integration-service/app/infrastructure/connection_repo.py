"""Shared Connection repository & error mapping helpers for Integration Service."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.infrastructure.models import Connection


def get_owned_connection(
    db: Session,
    ctx: RequestContext,
    connection_id: int,
    provider: str | None = None,
    not_found_detail: str = "Integration connection not found.",
) -> Connection:
    query = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.organization_id == ctx.organization_id,
    )
    if provider is not None:
        query = query.filter(
            Connection.user_id == ctx.user_id,
            func.upper(Connection.provider) == provider.upper(),
        )
    row = query.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail)
    return row


def map_provider_error(category: str, message: str) -> HTTPException:
    codes = {
        "configuration": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "region": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "model": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "authentication": status.HTTP_401_UNAUTHORIZED,
        "authorization": status.HTTP_403_FORBIDDEN,
        "billing": 402,
        "rate_limit": status.HTTP_429_TOO_MANY_REQUESTS,
        "network": status.HTTP_503_SERVICE_UNAVAILABLE,
        "provider": status.HTTP_502_BAD_GATEWAY,
        "service": status.HTTP_502_BAD_GATEWAY,
    }
    return HTTPException(status_code=codes.get(category, status.HTTP_502_BAD_GATEWAY), detail=message)
