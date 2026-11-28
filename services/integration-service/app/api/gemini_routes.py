"""Google Gemini integration routes."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import get_current_context
from app.api.schemas import (
    GeminiConnectRequest,
    GeminiConnectResponse,
    GeminiConnectionResponse,
    GeminiGenerateRequest,
    GeminiTestResponse,
    GeminiUsageResponse,
)
from app.infrastructure.connection_repo import get_owned_connection, map_provider_error
from app.infrastructure.crypto import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.infrastructure.db import get_db
from app.infrastructure.models import Connection, GeminiUsageEvent
from app.infrastructure.providers.gemini_client import (
    GeminiIntegrationError,
    generate_gemini_content,
    verify_gemini_api_key,
)

router = APIRouter(prefix="/integrations/gemini", tags=["Gemini Integration"])


def _response(connection: Connection) -> GeminiConnectionResponse:
    return GeminiConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        last_verified_at=connection.last_verified_at,
    )


def _api_key(connection: Connection) -> str:
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted or "")
        return credentials["api_key"]
    except (CredentialStorageError, KeyError) as exc:
        raise HTTPException(status_code=409, detail="Stored Gemini credentials are invalid. Reconnect this integration.") from exc


@router.post("/connections", response_model=GeminiConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_gemini(data: GeminiConnectRequest, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    api_key = data.secret_value()
    try:
        verification = verify_gemini_api_key(api_key)
        encrypted = encrypt_credentials({"api_key": api_key})
    except GeminiIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    connection = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "GEMINI")
        .first()
    )
    verified_at = datetime.utcnow()
    if connection is None:
        connection = Connection(
            user_id=ctx.user_id,
            organization_id=ctx.organization_id,
            provider="GEMINI",
            credentials_encrypted=encrypted,
            scopes="auth=api-key;verification=models",
            status="ACTIVE",
            last_verified_at=verified_at,
        )
        db.add(connection)
    else:
        connection.credentials_encrypted = encrypted
        connection.scopes = "auth=api-key;verification=models"
        connection.status = "ACTIVE"
        connection.last_verified_at = verified_at
    db.commit()
    db.refresh(connection)
    return GeminiConnectResponse(connection=_response(connection), model_count=verification["model_count"], message="Gemini API key verified and connected successfully.")


@router.get("/connections", response_model=List[GeminiConnectionResponse])
def list_gemini(db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    rows = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "GEMINI")
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(r) for r in rows]


@router.post("/connections/{connection_id}/test", response_model=GeminiTestResponse)
def test_gemini(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    connection = get_owned_connection(db, ctx, connection_id, provider="GEMINI", not_found_detail="Gemini connection not found.")
    try:
        verification = verify_gemini_api_key(_api_key(connection))
    except GeminiIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    verified_at = datetime.utcnow()
    connection.status = "ACTIVE"
    connection.last_verified_at = verified_at
    db.commit()
    return GeminiTestResponse(
        connection_id=connection.id,
        status=connection.status,
        model_count=verification["model_count"],
        last_verified_at=verified_at,
        message="Gemini connection verified successfully.",
    )


@router.delete("/connections/{connection_id}")
def disconnect_gemini(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    connection = get_owned_connection(db, ctx, connection_id, provider="GEMINI", not_found_detail="Gemini connection not found.")
    db.delete(connection)
    db.commit()
    return {"message": "Gemini integration removed from UniSora."}


@router.post("/generate")
def generate_gemini(data: GeminiGenerateRequest, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    connection = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "GEMINI", Connection.status == "ACTIVE")
        .order_by(Connection.created_at.desc())
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="No active Gemini integration is connected.")
    try:
        result = generate_gemini_content(_api_key(connection), data.model, data.contents, data.generation_config)
    except GeminiIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    db.add(
        GeminiUsageEvent(
            connection_id=connection.id,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            model=data.model,
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            total_tokens=result["total_tokens"],
        )
    )
    db.commit()
    return result["response"]


@router.get("/usage", response_model=GeminiUsageResponse)
def gemini_usage(start_date: date, end_date: date, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="The end date must be on or after the start date.")
    start = datetime.combine(start_date, time.min)
    end = datetime.combine(end_date + timedelta(days=1), time.min)
    rows = (
        db.query(GeminiUsageEvent)
        .filter(
            GeminiUsageEvent.user_id == ctx.user_id,
            GeminiUsageEvent.organization_id == ctx.organization_id,
            GeminiUsageEvent.created_at >= start,
            GeminiUsageEvent.created_at < end,
        )
        .all()
    )
    models: dict[str, dict[str, Any]] = {}
    days: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = models.setdefault(row.model, {"model": row.model, "requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        item["requests"] += 1
        item["input_tokens"] += row.input_tokens
        item["output_tokens"] += row.output_tokens
        item["total_tokens"] += row.total_tokens
        key = row.created_at.date().isoformat()
        day = days.setdefault(key, {"date": key, "requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        day["requests"] += 1
        day["input_tokens"] += row.input_tokens
        day["output_tokens"] += row.output_tokens
        day["total_tokens"] += row.total_tokens
    return GeminiUsageResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        requests=len(rows),
        input_tokens=sum(row.input_tokens for row in rows),
        output_tokens=sum(row.output_tokens for row in rows),
        total_tokens=sum(row.total_tokens for row in rows),
        by_model=list(models.values()),
        daily=sorted(days.values(), key=lambda item: item["date"]),
    )
