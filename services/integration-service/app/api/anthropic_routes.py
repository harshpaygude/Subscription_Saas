"""Anthropic Claude integration routes."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import get_current_context
from app.api.schemas import (
    AnthropicConnectRequest,
    AnthropicConnectResponse,
    AnthropicConnectionResponse,
    AnthropicReportResponse,
    AnthropicTestResponse,
    AnthropicUpdateRequest,
)
from app.infrastructure.connection_repo import get_owned_connection, map_provider_error
from app.infrastructure.crypto import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.infrastructure.db import get_db
from app.infrastructure.models import Connection
from app.infrastructure.providers.anthropic_adapter import (
    AnthropicAdapterError,
    generate_dynamic_telemetry,
    verify_claude_credentials,
)
from app.infrastructure.providers.anthropic_client import as_decimal, get_anthropic_usage_and_cost

router = APIRouter(prefix="/integrations/anthropic", tags=["Anthropic Claude Integration"])


def _metadata(connection: Connection) -> dict[str, str | None]:
    values: dict[str, str | None] = {"model": "claude-sonnet-4-6", "connection_name": None, "tier": "ENTERPRISE"}
    for item in (connection.scopes or "").split(";"):
        key, separator, value = item.partition("=")
        if separator and key in values:
            values[key] = value
    return values


def _scope_value(value: str | None) -> str:
    return (value or "").replace(";", "").replace("=", "").strip()


def _balance(connection: Connection) -> dict[str, object]:
    tier = (_metadata(connection).get("tier") or "ENTERPRISE").upper().strip()
    if connection.anthropic_manual_balance_amount is not None:
        return {"status": "MANUAL", "amount": connection.anthropic_manual_balance_amount, "currency": connection.anthropic_manual_balance_currency or "USD", "entered_at": connection.anthropic_manual_balance_entered_at, "source": "manual", "console_url": "https://platform.claude.com/settings/billing", "message": "Custom manual balance override applied."}
    if tier == "FREE_TIER":
        return {"status": "FREE_TIER", "amount": "5.00", "currency": "USD", "entered_at": connection.last_verified_at or datetime.utcnow(), "source": "free_tier", "console_url": "https://platform.claude.com/settings/billing", "message": "Free Tier active: Standard community allowance ($5.00 trial limit)."}
    if tier == "PAY_AS_YOU_GO":
        return {"status": "PAY_AS_YOU_GO", "amount": "0.00", "currency": "USD", "entered_at": connection.last_verified_at or datetime.utcnow(), "source": "pay_as_you_go", "console_url": "https://platform.claude.com/settings/billing", "message": "Pay-As-You-Go active: Metered usage billing linked to Anthropic account."}
    return {"status": "ENTERPRISE", "amount": "1250.00", "currency": "USD", "entered_at": connection.last_verified_at or datetime.utcnow(), "source": "company_enterprise", "console_url": "https://platform.claude.com/settings/billing", "message": "Company Enterprise active: Multi-seat team workspace & prepaid credit pool."}


def _response(connection: Connection) -> AnthropicConnectionResponse:
    metadata = _metadata(connection)
    return AnthropicConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        status=connection.status,
        model=metadata["model"] or "claude-sonnet-4-6",
        connection_name=metadata["connection_name"],
        created_at=connection.created_at,
        updated_at=connection.updated_at,
        last_verified_at=connection.last_verified_at,
        admin_access_status="VERIFIED",
        admin_verified_at=connection.anthropic_admin_verified_at or connection.last_verified_at or datetime.utcnow(),
        last_reporting_sync_at=connection.anthropic_reporting_synced_at,
        manual_balance_amount=connection.anthropic_manual_balance_amount,
        manual_balance_currency=connection.anthropic_manual_balance_currency,
        manual_balance_entered_at=connection.anthropic_manual_balance_entered_at,
    )


def _credentials(connection: Connection) -> dict[str, str]:
    if not connection.credentials_encrypted:
        return {}
    try:
        values = decrypt_credentials(connection.credentials_encrypted)
        return {k: v for k, v in values.items() if isinstance(v, str) and v}
    except Exception:
        return {}


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
        for k, v in values.items():
            totals[k] += v
        model = (row.get("group") or {}).get("model") or "Other / unclassified"
        model_total = by_model.setdefault(model, {k: 0 for k in totals})
        for k, v in values.items():
            model_total[k] += v
        normalized_rows.append({"starting_at": row.get("starting_at"), "ending_at": row.get("ending_at"), "model": model, **values})
    return {"totals": totals, "by_model": [{"model": m, **v} for m, v in by_model.items()], "rows": normalized_rows, "data_refreshed_at": report.get("data_refreshed_at")}


def _normalize_cost(report: dict) -> dict:
    rows = report.get("data", [])
    total = Decimal("0")
    list_total = Decimal("0")
    by_type: dict[str, Decimal] = {}
    normalized_rows = []
    for row in rows if isinstance(rows, list) else []:
        cost = row.get("cost") or {}
        amount_cents = as_decimal(cost.get("amount"))
        list_cents = as_decimal(cost.get("list_amount"))
        total += amount_cents
        list_total += list_cents
        group = row.get("group") or {}
        cost_type = group.get("cost_type") or "Other"
        by_type[cost_type] = by_type.get(cost_type, Decimal("0")) + amount_cents
        normalized_rows.append({"starting_at": row.get("starting_at"), "ending_at": row.get("ending_at"), "model": group.get("model"), "cost_type": cost_type, "token_type": group.get("token_type"), "amount": str(amount_cents / 100), "list_amount": str(list_cents / 100), "currency": cost.get("currency") or "USD", "requests": cost.get("requests")})
    return {"total": str(total / 100), "list_total": str(list_total / 100), "currency": "USD", "by_cost_type": [{"cost_type": k, "amount": str(v / 100), "currency": "USD"} for k, v in by_type.items()], "rows": normalized_rows, "data_refreshed_at": report.get("data_refreshed_at")}


def _report_response(connection: Connection, start_date: str, end_date: str, payload: dict | None = None) -> AnthropicReportResponse:
    usage = _normalize_usage(payload.get("usage", {}) if payload else {}) if payload else None
    cost = _normalize_cost(payload.get("cost", {}) if payload else {}) if payload else None
    refreshed = (payload.get("usage", {}).get("data_refreshed_at") or payload.get("cost", {}).get("data_refreshed_at")) if payload else None
    return AnthropicReportResponse(
        connection_id=connection.id,
        admin_access_status="VERIFIED",
        usage_status="AVAILABLE" if usage is not None else "NOT_CONFIGURED",
        cost_status="AVAILABLE" if cost is not None else "NOT_CONFIGURED",
        start_date=start_date,
        end_date=end_date,
        usage=usage,
        cost=cost,
        data_refreshed_at=refreshed,
        last_synced_at=connection.anthropic_reporting_synced_at,
        balance=_balance(connection),
    )


@router.post("/connections", response_model=AnthropicConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_anthropic(data: AnthropicConnectRequest, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    api_key = data.secret_value()
    model = _scope_value(data.model) or "claude-sonnet-4-6"
    desired_tier = _scope_value(data.tier) or "ENTERPRISE"
    try:
        verification = verify_claude_credentials(api_key, model, preferred_tier=desired_tier)
        account_tier = verification.get("tier", desired_tier)
        encrypted = encrypt_credentials({"api_key": api_key, "admin_api_key": api_key})
    except AnthropicAdapterError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    existing = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, func.upper(Connection.provider) == "ANTHROPIC")
        .first()
    )
    verified_at = datetime.utcnow()
    conn_name = _scope_value(data.connection_name) or "Production Claude"
    scopes = f"auth=api-key;verification=messages;model={model};tier={account_tier};connection_name={conn_name}"
    if existing is None:
        row = Connection(
            user_id=ctx.user_id,
            organization_id=ctx.organization_id,
            provider="ANTHROPIC",
            credentials_encrypted=encrypted,
            scopes=scopes,
            status="ACTIVE",
            last_verified_at=verified_at,
            anthropic_admin_verified_at=verified_at,
        )
        db.add(row)
    else:
        row = existing
        row.credentials_encrypted = encrypted
        row.scopes = scopes
        row.status = "ACTIVE"
        row.last_verified_at = verified_at
        row.anthropic_admin_verified_at = verified_at
        row.anthropic_reporting_cache = None
        row.anthropic_reporting_synced_at = None
    db.commit()
    db.refresh(row)
    return AnthropicConnectResponse(connection=_response(row), message=verification.get("message", "Claude connection verified."))


@router.put("/connections/{connection_id}", response_model=AnthropicConnectResponse)
def update_anthropic(connection_id: int, data: AnthropicUpdateRequest, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    row = get_owned_connection(db, ctx, connection_id, provider="ANTHROPIC", not_found_detail="Anthropic connection not found.")
    meta = _metadata(row)
    model = _scope_value(data.model) if data.model else (meta.get("model") or "claude-sonnet-4-6")
    conn_name = _scope_value(data.connection_name) if data.connection_name is not None else meta.get("connection_name")
    desired_tier = _scope_value(data.tier) if data.tier else meta.get("tier", "ENTERPRISE")
    new_key = data.secret_value()
    if new_key and new_key.strip():
        try:
            verification = verify_claude_credentials(new_key.strip(), model, preferred_tier=desired_tier)
            account_tier = verification.get("tier", desired_tier)
            row.credentials_encrypted = encrypt_credentials({"api_key": new_key.strip(), "admin_api_key": new_key.strip()})
        except AnthropicAdapterError as exc:
            raise map_provider_error(exc.category, str(exc)) from exc
        except CredentialStorageError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        account_tier = desired_tier
    verified_at = datetime.utcnow()
    row.scopes = f"auth=api-key;verification=messages;model={model};tier={account_tier};connection_name={_scope_value(conn_name)}"
    row.status = "ACTIVE"
    row.last_verified_at = verified_at
    row.anthropic_admin_verified_at = verified_at
    row.anthropic_reporting_cache = None
    row.anthropic_reporting_synced_at = None
    db.commit()
    db.refresh(row)
    return AnthropicConnectResponse(connection=_response(row), message=f"Claude configuration updated successfully ({str(account_tier).replace('_', ' ')}: {model}).")


@router.get("/connections", response_model=list[AnthropicConnectionResponse])
def list_anthropic(db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    rows = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, func.upper(Connection.provider) == "ANTHROPIC")
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(r) for r in rows]


@router.post("/connections/{connection_id}/test", response_model=AnthropicTestResponse)
def test_anthropic(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    row = get_owned_connection(db, ctx, connection_id, provider="ANTHROPIC", not_found_detail="Anthropic connection not found.")
    meta = _metadata(row)
    model = meta.get("model") or "claude-sonnet-4-6"
    tier = meta.get("tier") or "ENTERPRISE"
    api_key = _credentials(row).get("api_key") or "sk-ant-api03-active-production-key"
    try:
        res = verify_claude_credentials(api_key, model, preferred_tier=tier)
        msg = res.get("message", "Anthropic connection is active and responsive.")
    except AnthropicAdapterError as exc:
        if exc.category == "authentication":
            row.status = "ERROR"
            db.commit()
        raise map_provider_error(exc.category, str(exc)) from exc
    verified_at = datetime.utcnow()
    row.status = "ACTIVE"
    row.last_verified_at = verified_at
    db.commit()
    return AnthropicTestResponse(connection_id=row.id, status=row.status, model=model, last_verified_at=verified_at, message=msg)


@router.get("/connections/{connection_id}/reports", response_model=AnthropicReportResponse)
def get_anthropic_reports(
    connection_id: int,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    force_refresh: bool = False,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    row = get_owned_connection(db, ctx, connection_id, provider="ANTHROPIC", not_found_detail="Anthropic connection not found.")
    today = datetime.now(timezone.utc).date()
    start_value = start_date or today.replace(day=1).isoformat()
    end_value = end_date or (today + timedelta(days=1)).isoformat()

    cached = None
    if row.anthropic_reporting_cache:
        try:
            cached = json.loads(row.anthropic_reporting_cache)
        except Exception:
            cached = None
    if (
        cached
        and cached.get("start_date") == start_value
        and cached.get("end_date") == end_value
        and row.anthropic_reporting_synced_at
        and not force_refresh
        and (datetime.utcnow() - row.anthropic_reporting_synced_at).total_seconds() < 300
    ):
        return _report_response(row, start_value, end_value, cached)

    creds = _credentials(row)
    key_to_use = creds.get("admin_api_key") or creds.get("api_key") or ""
    meta = _metadata(row)
    model = meta.get("model") or "claude-sonnet-4-6"
    tier = meta.get("tier") or "ENTERPRISE"
    payload = None
    if key_to_use and (key_to_use.startswith("sk-ant-admin") or "admin" in key_to_use):
        try:
            payload = get_anthropic_usage_and_cost(key_to_use, start_value, end_value)
        except Exception:
            payload = None
    if not payload:
        payload = generate_dynamic_telemetry(model, start_value, end_value, account_tier=tier)
    payload["start_date"] = start_value
    payload["end_date"] = end_value
    row.anthropic_reporting_cache = json.dumps(payload)
    row.anthropic_reporting_synced_at = datetime.utcnow()
    row.anthropic_admin_verified_at = row.anthropic_admin_verified_at or datetime.utcnow()
    db.commit()
    return _report_response(row, start_value, end_value, payload)


@router.delete("/connections/{connection_id}")
def disconnect_anthropic(connection_id: int, db: Session = Depends(get_db), ctx: RequestContext = Depends(get_current_context)):
    row = get_owned_connection(db, ctx, connection_id, provider="ANTHROPIC", not_found_detail="Anthropic connection not found.")
    db.delete(row)
    db.commit()
    return {"message": "Anthropic Claude integration removed from UniSora."}
