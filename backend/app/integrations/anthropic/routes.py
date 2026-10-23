from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.credentials import CredentialStorageError, decrypt_credentials, encrypt_credentials
from .client import AnthropicIntegrationError, verify_anthropic_api_key
from .schemas import AnthropicConnectRequest, AnthropicConnectResponse, AnthropicConnectionResponse, AnthropicTestResponse

router = APIRouter(prefix="/integrations/anthropic", tags=["Anthropic Claude Integration"])


def _http_exception(exc: AnthropicIntegrationError | CredentialStorageError) -> HTTPException:
    if isinstance(exc, CredentialStorageError):
        return HTTPException(status_code=503, detail=str(exc))
    codes = {"configuration": 422, "authentication": 401, "authorization": 403, "billing": 402, "rate_limit": 429, "model": 422, "network": 503, "provider": 502}
    return HTTPException(status_code=codes.get(exc.category, 502), detail=str(exc))


def _metadata(connection: Connection) -> dict[str, str | None]:
    values: dict[str, str | None] = {"model": "", "connection_name": None}
    for item in (connection.scopes or "").split(";"):
        key, separator, value = item.partition("=")
        if separator and key in values:
            values[key] = value
    return values


def _scope_value(value: str | None) -> str:
    return (value or "").replace(";", "").replace("=", "").strip()


def _response(connection: Connection) -> AnthropicConnectionResponse:
    metadata = _metadata(connection)
    return AnthropicConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        status=connection.status,
        model=metadata["model"] or "",
        connection_name=metadata["connection_name"],
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        last_verified_at=connection.last_verified_at,
    )


def _owned(connection_id: int, db: Session, user: User) -> Connection:
    row = db.query(Connection).filter(Connection.id == connection_id, Connection.user_id == user.id, Connection.organization_id == user.organization_id, Connection.provider == "ANTHROPIC").first()
    if row is None:
        raise HTTPException(status_code=404, detail="Anthropic connection not found.")
    return row


def _api_key(connection: Connection) -> str:
    try:
        values = decrypt_credentials(connection.credentials_encrypted or "")
        key = values.get("api_key")
    except (CredentialStorageError, AttributeError) as exc:
        raise HTTPException(status_code=409, detail="Stored Anthropic credentials are invalid. Reconnect this integration.") from exc
    if not isinstance(key, str) or not key:
        raise HTTPException(status_code=409, detail="Stored Anthropic credentials are invalid. Reconnect this integration.")
    return key


@router.post("/connections", response_model=AnthropicConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_anthropic(data: AnthropicConnectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    api_key = data.secret_value()
    model = _scope_value(data.model)
    if not model:
        raise HTTPException(status_code=422, detail="An Anthropic model is required.")
    try:
        verification = verify_anthropic_api_key(api_key, model)
        encrypted = encrypt_credentials({"api_key": api_key})
    except (AnthropicIntegrationError, CredentialStorageError) as exc:
        raise _http_exception(exc)

    row = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "ANTHROPIC").first()
    verified_at = datetime.utcnow()
    scopes = f"auth=api-key;verification=messages;model={model};connection_name={_scope_value(data.connection_name)}"
    if row is None:
        row = Connection(user_id=current_user.id, organization_id=current_user.organization_id, provider="ANTHROPIC", credentials_encrypted=encrypted, scopes=scopes, status="ACTIVE", last_verified_at=verified_at)
        db.add(row)
    else:
        row.credentials_encrypted = encrypted
        row.scopes = scopes
        row.status = "ACTIVE"
        row.last_verified_at = verified_at
    try:
        db.commit()
        db.refresh(row)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Anthropic connection could not be persisted.") from exc
    return AnthropicConnectResponse(connection=_response(row), message=f"Anthropic Claude verified successfully with {verification['model']}.")


@router.get("/connections", response_model=list[AnthropicConnectionResponse])
def list_anthropic(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "ANTHROPIC").order_by(Connection.created_at.desc()).all()
    return [_response(row) for row in rows]


@router.post("/connections/{connection_id}/test", response_model=AnthropicTestResponse)
def test_anthropic(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    model = _metadata(row)["model"]
    if not model:
        raise HTTPException(status_code=409, detail="Stored Anthropic model is missing. Reconnect this integration.")
    try:
        verify_anthropic_api_key(_api_key(row), model)
    except AnthropicIntegrationError as exc:
        if exc.category in {"authentication", "authorization", "billing", "model"}:
            row.status = "ERROR"
            db.commit()
        raise _http_exception(exc)
    verified_at = datetime.utcnow()
    row.status = "ACTIVE"
    row.last_verified_at = verified_at
    db.commit()
    return AnthropicTestResponse(connection_id=row.id, status=row.status, model=model, last_verified_at=verified_at, message="Anthropic Claude connection verified successfully.")


@router.delete("/connections/{connection_id}")
def disconnect_anthropic(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    db.delete(row)
    db.commit()
    return {"message": "Anthropic Claude integration removed from UniSora."}
