from datetime import date, datetime, time, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.database.models import Connection, GeminiUsageEvent, User
from app.database.session import get_db
from app.integrations.credentials import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.integrations.gemini.client import GeminiIntegrationError, verify_gemini_api_key
from app.integrations.gemini.schemas import GeminiConnectRequest, GeminiConnectResponse, GeminiConnectionResponse, GeminiTestResponse, GeminiGenerateRequest, GeminiUsageResponse
from app.integrations.gemini.client import generate_gemini_content

router = APIRouter(prefix="/integrations/gemini", tags=["Gemini Integration"])

def _http_exception(exc: GeminiIntegrationError | CredentialStorageError) -> HTTPException:
    if isinstance(exc, CredentialStorageError):
        return HTTPException(status_code=503, detail=str(exc))
    codes = {"configuration": 422, "authentication": 401, "rate_limit": 429, "network": 503, "provider": 502}
    return HTTPException(status_code=codes.get(exc.category, 502), detail=str(exc))

def _response(connection: Connection) -> GeminiConnectionResponse:
    return GeminiConnectionResponse(id=connection.id, provider=connection.provider, status=connection.status, created_at=connection.created_at, updated_at=connection.updated_at, last_verified_at=connection.last_verified_at)

def _owned(connection_id: int, db: Session, user: User) -> Connection:
    connection = db.query(Connection).filter(Connection.id == connection_id, Connection.user_id == user.id, Connection.organization_id == user.organization_id, Connection.provider == "GEMINI").first()
    if connection is None:
        raise HTTPException(status_code=404, detail="Gemini connection not found.")
    return connection

def _api_key(connection: Connection) -> str:
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted or "")
        key = credentials["api_key"]
    except (CredentialStorageError, KeyError) as exc:
        raise HTTPException(status_code=409, detail="Stored Gemini credentials are invalid. Reconnect this integration.") from exc
    return key

@router.post("/connections", response_model=GeminiConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_gemini(data: GeminiConnectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    api_key = data.secret_value()
    try:
        verification = verify_gemini_api_key(api_key)
        encrypted = encrypt_credentials({"api_key": api_key})
    except (GeminiIntegrationError, CredentialStorageError) as exc:
        raise _http_exception(exc)
    connection = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "GEMINI").first()
    verified_at = datetime.utcnow()
    if connection is None:
        connection = Connection(user_id=current_user.id, organization_id=current_user.organization_id, provider="GEMINI", credentials_encrypted=encrypted, scopes="auth=api-key;verification=models", status="ACTIVE", last_verified_at=verified_at)
        db.add(connection)
    else:
        connection.credentials_encrypted = encrypted
        connection.scopes = "auth=api-key;verification=models"
        connection.status = "ACTIVE"
        connection.last_verified_at = verified_at
    db.commit(); db.refresh(connection)
    return GeminiConnectResponse(connection=_response(connection), model_count=verification["model_count"], message="Gemini API key verified and connected successfully.")

@router.get("/connections", response_model=List[GeminiConnectionResponse])
def list_gemini(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "GEMINI").order_by(Connection.created_at.desc()).all()
    return [_response(row) for row in rows]

@router.post("/connections/{connection_id}/test", response_model=GeminiTestResponse)
def test_gemini(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = _owned(connection_id, db, current_user)
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted or "")
        verification = verify_gemini_api_key(credentials["api_key"])
    except (GeminiIntegrationError, CredentialStorageError, KeyError) as exc:
        if isinstance(exc, KeyError):
            exc = CredentialStorageError("Stored Gemini credentials are invalid. Reconnect this integration.")
        raise _http_exception(exc)
    verified_at = datetime.utcnow(); connection.status = "ACTIVE"; connection.last_verified_at = verified_at; db.commit()
    return GeminiTestResponse(connection_id=connection.id, status=connection.status, model_count=verification["model_count"], last_verified_at=verified_at, message="Gemini connection verified successfully.")

@router.delete("/connections/{connection_id}")
def disconnect_gemini(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = _owned(connection_id, db, current_user); db.delete(connection); db.commit()
    return {"message": "Gemini integration removed from UniSora."}

@router.post("/generate")
def generate_gemini(data: GeminiGenerateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "GEMINI", Connection.status == "ACTIVE").order_by(Connection.created_at.desc()).first()
    if connection is None:
        raise HTTPException(status_code=404, detail="No active Gemini integration is connected.")
    try:
        result = generate_gemini_content(_api_key(connection), data.model, data.contents, data.generation_config)
    except (GeminiIntegrationError, HTTPException) as exc:
        if isinstance(exc, HTTPException): raise exc
        raise _http_exception(exc)
    db.add(GeminiUsageEvent(connection_id=connection.id, organization_id=current_user.organization_id, user_id=current_user.id, model=data.model, input_tokens=result["input_tokens"], output_tokens=result["output_tokens"], total_tokens=result["total_tokens"]))
    db.commit()
    return result["response"]

@router.get("/usage", response_model=GeminiUsageResponse)
def gemini_usage(start_date: date, end_date: date, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="The end date must be on or after the start date.")
    start = datetime.combine(start_date, time.min)
    end = datetime.combine(end_date + timedelta(days=1), time.min)
    rows = db.query(GeminiUsageEvent).filter(GeminiUsageEvent.user_id == current_user.id, GeminiUsageEvent.organization_id == current_user.organization_id, GeminiUsageEvent.created_at >= start, GeminiUsageEvent.created_at < end).all()
    models: dict[str, dict[str, Any]] = {}
    days: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = models.setdefault(row.model, {"model": row.model, "requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        item["requests"] += 1; item["input_tokens"] += row.input_tokens; item["output_tokens"] += row.output_tokens; item["total_tokens"] += row.total_tokens
        key = row.created_at.date().isoformat(); day = days.setdefault(key, {"date": key, "requests": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        day["requests"] += 1; day["input_tokens"] += row.input_tokens; day["output_tokens"] += row.output_tokens; day["total_tokens"] += row.total_tokens
    return GeminiUsageResponse(start_date=start_date.isoformat(), end_date=end_date.isoformat(), requests=len(rows), input_tokens=sum(row.input_tokens for row in rows), output_tokens=sum(row.output_tokens for row in rows), total_tokens=sum(row.total_tokens for row in rows), by_model=list(models.values()), daily=sorted(days.values(), key=lambda item: item["date"]))
