from datetime import date, datetime, time, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.credentials import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.integrations.openai.client import OpenAIIntegrationError, get_openai_costs, get_openai_usage, verify_openai_api_key
from app.integrations.openai.schemas import (
    OpenAIConnectRequest,
    OpenAIConnectResponse,
    OpenAIConnectionResponse,
    OpenAICostResponse,
    OpenAISummaryResponse,
    OpenAITestResponse,
    OpenAIUsageResponse,
)

router = APIRouter(prefix="/integrations/openai", tags=["OpenAI Integration"])


def _http_exception(exc: OpenAIIntegrationError | CredentialStorageError) -> HTTPException:
    if isinstance(exc, CredentialStorageError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    status_by_category = {
        "configuration": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "authentication": status.HTTP_401_UNAUTHORIZED,
        "authorization": status.HTTP_403_FORBIDDEN,
        "rate_limit": status.HTTP_429_TOO_MANY_REQUESTS,
        "network": status.HTTP_503_SERVICE_UNAVAILABLE,
        "provider": status.HTTP_502_BAD_GATEWAY,
    }
    return HTTPException(status_code=status_by_category.get(exc.category, status.HTTP_502_BAD_GATEWAY), detail=str(exc))


def _response(connection: Connection) -> OpenAIConnectionResponse:
    return OpenAIConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        last_verified_at=connection.last_verified_at,
    )


def _owned_connection(connection_id: int, db: Session, current_user: User) -> Connection:
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "OPENAI",
        )
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="OpenAI connection not found.")
    return connection


def _api_key(connection: Connection) -> str:
    if not connection.credentials_encrypted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reconnect this OpenAI integration.")
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted)
        api_key = credentials.get("api_key")
    except (CredentialStorageError, AttributeError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stored OpenAI credentials could not be read. Reconnect this integration.") from exc
    if not isinstance(api_key, str) or not api_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stored OpenAI credentials are invalid. Reconnect this integration.")
    return api_key


def _period(start_date: date, end_date: date) -> tuple[int, int]:
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The end date must be on or after the start date.")
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return int(start.timestamp()), int(end.timestamp())


def _connection_for_user(db: Session, current_user: User) -> Connection:
    connection = (
        db.query(Connection)
        .filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "OPENAI")
        .order_by(Connection.created_at.desc())
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No OpenAI integration is connected.")
    return connection


def _usage_response(data: dict, start_time: int, end_time: int) -> OpenAIUsageResponse:
    return OpenAIUsageResponse(**data, start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())


def _cost_response(data: dict, start_time: int, end_time: int) -> OpenAICostResponse:
    return OpenAICostResponse(**data, start_time=start_time, end_time=end_time, synced_at=datetime.utcnow())


@router.post("/connections", response_model=OpenAIConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_openai(
    credentials_data: OpenAIConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = credentials_data.secret_value()
    try:
        verification = verify_openai_api_key(api_key)
        encrypted = encrypt_credentials({"api_key": api_key})
    except (OpenAIIntegrationError, CredentialStorageError) as exc:
        raise _http_exception(exc)

    verified_at = datetime.utcnow()
    connection = (
        db.query(Connection)
        .filter(
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "OPENAI",
        )
        .first()
    )
    if connection is None:
        connection = Connection(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            provider="OPENAI",
            provider_tenant_id=None,
            access_token=None,
            refresh_token=None,
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
def list_openai_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connections = (
        db.query(Connection)
        .filter(
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "OPENAI",
        )
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(connection) for connection in connections]


@router.post("/connections/{connection_id}/test", response_model=OpenAITestResponse)
def test_openai_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = _owned_connection(connection_id, db, current_user)
    if not connection.credentials_encrypted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reconnect this OpenAI integration.")
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted)
        verification = verify_openai_api_key(credentials["api_key"])
    except (OpenAIIntegrationError, CredentialStorageError, KeyError) as exc:
        if isinstance(exc, KeyError):
            exc = CredentialStorageError("Stored OpenAI credentials are invalid. Reconnect this integration.")
        raise _http_exception(exc)

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
def disconnect_openai(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = _owned_connection(connection_id, db, current_user)
    db.delete(connection)
    db.commit()
    return {"message": "OpenAI integration removed from UniSora."}


@router.get("/usage", response_model=OpenAIUsageResponse)
def openai_usage(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, current_user)
    try:
        data = get_openai_usage(_api_key(connection), start_time, end_time)
    except OpenAIIntegrationError as exc:
        raise _http_exception(exc)
    return _usage_response(data, start_time, end_time)


@router.get("/costs", response_model=OpenAICostResponse)
def openai_costs(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, current_user)
    try:
        data = get_openai_costs(_api_key(connection), start_time, end_time)
    except OpenAIIntegrationError as exc:
        raise _http_exception(exc)
    return _cost_response(data, start_time, end_time)


@router.get("/summary", response_model=OpenAISummaryResponse)
def openai_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time, end_time = _period(start_date, end_date)
    connection = _connection_for_user(db, current_user)
    api_key = _api_key(connection)
    try:
        usage = _usage_response(get_openai_usage(api_key, start_time, end_time), start_time, end_time)
    except OpenAIIntegrationError as exc:
        raise _http_exception(exc)
    costs = None
    costs_error = None
    try:
        costs = _cost_response(get_openai_costs(api_key, start_time, end_time), start_time, end_time)
    except OpenAIIntegrationError as exc:
        costs_error = str(exc)
    return OpenAISummaryResponse(usage=usage, costs=costs, costs_error=costs_error)
