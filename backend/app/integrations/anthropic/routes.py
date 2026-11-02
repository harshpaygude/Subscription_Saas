import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.credentials import CredentialStorageError, decrypt_credentials, encrypt_credentials
from .client import AnthropicIntegrationError, as_decimal, get_anthropic_usage_and_cost, verify_anthropic_api_key, verify_anthropic_reporting_credential
from .schemas import AnthropicAdminCredentialRequest, AnthropicAdminCredentialResponse, AnthropicBalanceResponse, AnthropicConnectRequest, AnthropicConnectResponse, AnthropicConnectionResponse, AnthropicManualBalanceRequest, AnthropicReportResponse, AnthropicTestResponse

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
        admin_access_status=_admin_status(connection),
        admin_verified_at=connection.anthropic_admin_verified_at,
        last_reporting_sync_at=connection.anthropic_reporting_synced_at,
        manual_balance_amount=connection.anthropic_manual_balance_amount,
        manual_balance_currency=connection.anthropic_manual_balance_currency,
        manual_balance_entered_at=connection.anthropic_manual_balance_entered_at,
    )


def _owned(connection_id: int, db: Session, user: User) -> Connection:
    row = db.query(Connection).filter(Connection.id == connection_id, Connection.user_id == user.id, Connection.organization_id == user.organization_id, Connection.provider == "ANTHROPIC").first()
    if row is None:
        raise HTTPException(status_code=404, detail="Anthropic connection not found.")
    return row


def _credentials(connection: Connection) -> dict[str, str]:
    try:
        values = decrypt_credentials(connection.credentials_encrypted or "")
    except (CredentialStorageError, AttributeError) as exc:
        raise HTTPException(status_code=409, detail="Stored Anthropic credentials are invalid. Reconnect this integration.") from exc
    return {key: value for key, value in values.items() if isinstance(value, str) and value}


def _api_key(connection: Connection) -> str:
    key = _credentials(connection).get("api_key")
    if not key:
        raise HTTPException(status_code=409, detail="Stored Anthropic credentials are invalid. Reconnect this integration.")
    return key


def _admin_key(connection: Connection) -> str | None:
    return _credentials(connection).get("admin_api_key")


def _admin_status(connection: Connection) -> str:
    if not _admin_key(connection):
        return "NOT_CONFIGURED"
    return "VERIFIED" if connection.anthropic_admin_verified_at else "CONFIGURED"


def _balance(connection: Connection) -> dict[str, object]:
    return {
        "status": "MANUAL" if connection.anthropic_manual_balance_amount is not None else "UNSUPPORTED",
        "amount": connection.anthropic_manual_balance_amount,
        "currency": connection.anthropic_manual_balance_currency,
        "entered_at": connection.anthropic_manual_balance_entered_at,
        "source": "manual" if connection.anthropic_manual_balance_amount is not None else "provider_unavailable",
        "console_url": "https://platform.claude.com/settings/billing",
        "message": "Anthropic does not expose an organization prepaid-credit balance through the supported API used here." if connection.anthropic_manual_balance_amount is None else "Manually entered balance; not provider-verified.",
    }


def _default_range() -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    return today.replace(day=1).isoformat(), (today + timedelta(days=1)).isoformat()


def _normalize_usage(report: dict) -> dict:
    rows = report.get("data", [])
    totals = {"requests": 0, "uncached_input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    by_model: dict[str, dict[str, int]] = {}
    normalized_rows = []
    for row in rows if isinstance(rows, list) else []:
        usage = row.get("usage") or {}
        cache_creation = usage.get("cache_creation") or {}
        values = {
            "requests": int(usage.get("requests") or 0),
            "uncached_input_tokens": int(usage.get("uncached_input_tokens") or 0),
            "cache_creation_input_tokens": int(cache_creation.get("ephemeral_1h_input_tokens") or 0) + int(cache_creation.get("ephemeral_5m_input_tokens") or 0),
            "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        for key, value in values.items(): totals[key] += value
        model = (row.get("group") or {}).get("model") or "Other / unclassified"
        model_total = by_model.setdefault(model, {key: 0 for key in totals})
        for key, value in values.items(): model_total[key] += value
        normalized_rows.append({"starting_at": row.get("starting_at"), "ending_at": row.get("ending_at"), "model": model, **values})
    return {"totals": totals, "by_model": [{"model": model, **values} for model, values in by_model.items()], "rows": normalized_rows, "data_refreshed_at": report.get("data_refreshed_at")}


def _normalize_cost(report: dict) -> dict:
    rows = report.get("data", [])
    total = Decimal("0")
    list_total = Decimal("0")
    by_type: dict[str, Decimal] = {}
    normalized_rows = []
    for row in rows if isinstance(rows, list) else []:
        cost = row.get("cost") or {}
        amount_cents = as_decimal(cost.get("amount"))
        list_amount_cents = as_decimal(cost.get("list_amount"))
        total += amount_cents; list_total += list_amount_cents
        group = row.get("group") or {}
        cost_type = group.get("cost_type") or "Other"
        by_type[cost_type] = by_type.get(cost_type, Decimal("0")) + amount_cents
        normalized_rows.append({"starting_at": row.get("starting_at"), "ending_at": row.get("ending_at"), "model": group.get("model"), "cost_type": cost_type, "token_type": group.get("token_type"), "amount": str(amount_cents / 100), "list_amount": str(list_amount_cents / 100), "currency": cost.get("currency") or "USD", "requests": cost.get("requests")})
    return {"total": str(total / 100), "list_total": str(list_total / 100), "currency": "USD", "by_cost_type": [{"cost_type": key, "amount": str(value / 100), "currency": "USD"} for key, value in by_type.items()], "rows": normalized_rows, "data_refreshed_at": report.get("data_refreshed_at")}


def _report_response(connection: Connection, start_date: str, end_date: str, payload: dict | None = None) -> AnthropicReportResponse:
    usage = _normalize_usage(payload.get("usage", {}) if payload else {}) if payload else None
    cost = _normalize_cost(payload.get("cost", {}) if payload else {}) if payload else None
    refreshed = None
    if payload:
        refreshed = payload.get("usage", {}).get("data_refreshed_at") or payload.get("cost", {}).get("data_refreshed_at")
    return AnthropicReportResponse(connection_id=connection.id, admin_access_status=_admin_status(connection), usage_status="AVAILABLE" if usage is not None else "NOT_CONFIGURED", cost_status="AVAILABLE" if cost is not None else "NOT_CONFIGURED", start_date=start_date, end_date=end_date, usage=usage, cost=cost, data_refreshed_at=refreshed, last_synced_at=connection.anthropic_reporting_synced_at, balance=_balance(connection))


@router.post("/connections", response_model=AnthropicConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_anthropic(data: AnthropicConnectRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    api_key = data.secret_value()
    model = _scope_value(data.model)
    if not model:
        raise HTTPException(status_code=422, detail="An Anthropic model is required.")
    try:
        verification = verify_anthropic_api_key(api_key, model)
        existing = db.query(Connection).filter(Connection.user_id == current_user.id, Connection.organization_id == current_user.organization_id, Connection.provider == "ANTHROPIC").first()
        preserved_admin_key = _admin_key(existing) if existing else None
        credentials = {"api_key": api_key, **({"admin_api_key": preserved_admin_key} if preserved_admin_key else {})}
        encrypted = encrypt_credentials(credentials)
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


@router.post("/connections/{connection_id}/admin-credential", response_model=AnthropicAdminCredentialResponse)
def configure_anthropic_admin_credential(connection_id: int, data: AnthropicAdminCredentialRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    try:
        verification = verify_anthropic_reporting_credential(data.secret_value())
        credentials = _credentials(row)
        credentials["admin_api_key"] = data.secret_value()
        row.credentials_encrypted = encrypt_credentials(credentials)
        row.anthropic_admin_verified_at = datetime.utcnow()
        row.anthropic_reporting_cache = None
        row.anthropic_reporting_synced_at = None
        db.commit()
    except (AnthropicIntegrationError, CredentialStorageError) as exc:
        db.rollback()
        raise _http_exception(exc)
    del verification
    return AnthropicAdminCredentialResponse(connection_id=row.id, admin_access_status="VERIFIED", admin_verified_at=row.anthropic_admin_verified_at, message="Anthropic organization reporting access verified. Your standard Messages API key was preserved.")


@router.delete("/connections/{connection_id}/admin-credential")
def remove_anthropic_admin_credential(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    credentials = _credentials(row)
    credentials.pop("admin_api_key", None)
    row.credentials_encrypted = encrypt_credentials(credentials)
    row.anthropic_admin_verified_at = None
    row.anthropic_reporting_cache = None
    row.anthropic_reporting_synced_at = None
    db.commit()
    return {"message": "Anthropic organization reporting credential removed. The standard Messages API connection remains active."}


@router.get("/connections/{connection_id}/reports", response_model=AnthropicReportResponse)
def get_anthropic_reports(connection_id: int, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), force_refresh: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    start_value, end_value = (start_date, end_date) if start_date and end_date else _default_range()
    admin_key = _admin_key(row)
    if not admin_key or not row.anthropic_admin_verified_at:
        return _report_response(row, start_value, end_value)
    cached = None
    try:
        if row.anthropic_reporting_cache:
            cached = json.loads(row.anthropic_reporting_cache)
    except (TypeError, ValueError):
        cached = None
    cache_is_current = bool(cached and cached.get("start_date") == start_value and cached.get("end_date") == end_value and row.anthropic_reporting_synced_at and not force_refresh and (datetime.utcnow() - row.anthropic_reporting_synced_at).total_seconds() < 300)
    if cache_is_current:
        return _report_response(row, start_value, end_value, cached)
    try:
        payload = get_anthropic_usage_and_cost(admin_key, start_value, end_value)
        row.anthropic_reporting_cache = json.dumps(payload)
        row.anthropic_reporting_synced_at = datetime.utcnow()
        db.commit()
        return _report_response(row, start_value, end_value, payload)
    except AnthropicIntegrationError as exc:
        if exc.category in {"authentication", "authorization"}:
            row.anthropic_admin_verified_at = None
            db.commit()
        raise _http_exception(exc)


@router.post("/connections/{connection_id}/balance", response_model=AnthropicBalanceResponse)
def save_anthropic_manual_balance(connection_id: int, data: AnthropicManualBalanceRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    try:
        amount = Decimal(data.amount)
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail="Balance amount must be a valid decimal value.") from exc
    if amount < 0:
        raise HTTPException(status_code=422, detail="Balance amount cannot be negative.")
    row.anthropic_manual_balance_amount = format(amount, "f")
    row.anthropic_manual_balance_currency = data.currency.upper()
    row.anthropic_manual_balance_entered_at = datetime.utcnow()
    db.commit()
    return AnthropicBalanceResponse(connection_id=row.id, balance=_balance(row))


@router.delete("/connections/{connection_id}/balance")
def remove_anthropic_manual_balance(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    row.anthropic_manual_balance_amount = None
    row.anthropic_manual_balance_currency = None
    row.anthropic_manual_balance_entered_at = None
    db.commit()
    return {"message": "Manual Anthropic balance removed."}


@router.delete("/connections/{connection_id}")
def disconnect_anthropic(connection_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = _owned(connection_id, db, current_user)
    db.delete(row)
    db.commit()
    return {"message": "Anthropic Claude integration removed from UniSora."}
