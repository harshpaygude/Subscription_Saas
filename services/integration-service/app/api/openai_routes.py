"""OpenAI integration routes."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import get_current_context
from app.api.schemas import (
    OpenAIConnectRequest,
    OpenAIConnectResponse,
    OpenAIConnectionResponse,
    OpenAICostResponse,
    OpenAISummaryResponse,
    OpenAITestResponse,
    OpenAIUsageResponse,
)
from app.infrastructure.connection_repo import get_owned_connection, map_provider_error
from app.infrastructure.crypto import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.infrastructure.db import get_db
from app.infrastructure.models import Connection
from app.infrastructure.providers.openai_client import (
    OpenAIIntegrationError,
    get_openai_costs,
    get_openai_usage,
    verify_openai_api_key,
)

router = APIRouter(prefix="/integrations/openai", tags=["OpenAI Integration"])


def _response(connection: Connection) -> OpenAIConnectionResponse:
    return OpenAIConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        last_verified_at=connection.last_verified_at,
    )


def _api_key(connection: Connection) -> str:
    if not connection.credentials_encrypted:
        raise HTTPException(status_code=409, detail="Reconnect this OpenAI integration.")
    try:
        api_key = decrypt_credentials(connection.credentials_encrypted).get("api_key")
    except (CredentialStorageError, AttributeError) as exc:
        raise HTTPException(status_code=503, detail="Stored OpenAI credentials could not be read. Reconnect this integration.") from exc
    if not isinstance(api_key, str) or not api_key:
        raise HTTPException(status_code=409, detail="Stored OpenAI credentials are invalid. Reconnect this integration.")
    return api_key


def _period(start_date: date, end_date: date) -> tuple[int, int]:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="The end date must be on or after the start date.")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return int(start.timestamp()), int(end.timestamp())


def _connection_for_user(db: Session, ctx: RequestContext) -> Connection:
    row = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "OPENAI")
        .order_by(Connection.created_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No OpenAI integration is connected.")
    return row


@router.post("/connections", response_model=OpenAIConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_openai(
    credentials_data: OpenAIConnectRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    api_key = credentials_data.secret_value()
    try:
        verification = verify_openai_api_key(api_key)
        encrypted = encrypt_credentials({"api_key": api_key})
    except OpenAIIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    verified_at = datetime.utcnow()
    connection = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "OPENAI")
        .first()
    )
    if connection is None:
        connection = Connection(
            user_id=ctx.user_id,
            organization_id=ctx.organization_id,
            provider="OPENAI",
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
    return OpenAIConnectResponse(
        connection=_response(connection),
        model_count=verification["model_count"],
        message="OpenAI API key verified and connected successfully.",
    )


@router.get("/connections", response_model=List[OpenAIConnectionResponse])
def list_openai_connections(db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    rows = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "OPENAI")
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(r) for r in rows]


@router.post("/connections/{connection_id}/test", response_model=OpenAITestResponse)
def test_openai_connection(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    connection = get_owned_connection(db, ctx, connection_id, provider="OPENAI", not_found_detail="OpenAI connection not found.")
    try:
        verification = verify_openai_api_key(_api_key(connection))
    except OpenAIIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    verified_at = datetime.utcnow()
    connection.status = "ACTIVE"
    connection.last_verified_at = verified_at
    db.commit()
    return OpenAITestResponse(
        connection_id=connection.id,
        status=connection.status,
        model_count=verification["model_count"],
        last_verified_at=verified_at,
        message="OpenAI connection verified successfully.",
    )


@router.delete("/connections/{connection_id}")
def disconnect_openai(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    connection = get_owned_connection(db, ctx, connection_id, provider="OPENAI", not_found_detail="OpenAI connection not found.")
    db.delete(connection)
    db.commit()
    return {"message": "OpenAI integration removed from UniSora."}


@router.get("/usage", response_model=OpenAIUsageResponse)
def openai_usage(start_date: date = Query(...), end_date: date = Query(...), db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, ctx)
    try:
        data = get_openai_usage(_api_key(connection), start_time, end_time)
    except OpenAIIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    return OpenAIUsageResponse(**data, start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())


@router.get("/costs", response_model=OpenAICostResponse)
def openai_costs(start_date: date = Query(...), end_date: date = Query(...), db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, ctx)
    try:
        data = get_openai_costs(_api_key(connection), start_time, end_time)
    except OpenAIIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    return OpenAICostResponse(**data, start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())


@router.get("/summary", response_model=OpenAISummaryResponse)
def openai_summary(start_date: date = Query(...), end_date: date = Query(...), db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, ctx)
    api_key = _api_key(connection)
    try:
        usage = OpenAIUsageResponse(**get_openai_usage(api_key, start_time, end_time), start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())
    except OpenAIIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    costs = None
    costs_error = None
    try:
        costs = OpenAICostResponse(**get_openai_costs(api_key, start_time, end_time), start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())
    except OpenAIIntegrationError as exc:
        costs_error = str(exc)
    return OpenAISummaryResponse(usage=usage, costs=costs, costs_error=costs_error)
