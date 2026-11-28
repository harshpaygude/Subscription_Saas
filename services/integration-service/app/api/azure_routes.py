"""Microsoft Azure integration routes."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import get_current_context
from app.config import settings
from app.infrastructure.crypto import TokenCryptoError, decrypt_azure_token, encrypt_azure_token
from app.infrastructure.db import get_db
from app.infrastructure.models import AzureConnection, AzureSubscription
from app.infrastructure.providers.azure_client import AzureClient, AzureProviderError
from app.infrastructure.providers.azure_oauth import OAuthError, access_token, begin, redeem, service_principal_token

router = APIRouter(prefix="/integrations/azure", tags=["Azure Integration"])


class SubscriptionSelection(BaseModel):
    subscription_ids: list[str]


class ServicePrincipalRequest(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str | None = None


class AzureConnectionResponse(BaseModel):
    id: int
    provider: str
    connected: bool
    status: str
    last_successful_refresh: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


def _cookie_clear() -> dict[str, str]:
    return {"Set-Cookie": "azure_oauth_state=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"}


def _access(ctx: RequestContext, db: Session):
    row = db.query(AzureConnection).filter(AzureConnection.user_id == ctx.user_id, AzureConnection.organization_id == ctx.organization_id).first()
    if not row or row.status != "CONNECTED" or not row.encrypted_token_cache:
        raise HTTPException(409, "Azure connection is not active; reauthorize first")
    try:
        payload = decrypt_azure_token(row.encrypted_token_cache)
        token, updated = access_token(payload)
    except (TokenCryptoError, OAuthError) as exc:
        row.status = "REAUTH_REQUIRED"
        db.commit()
        raise HTTPException(409, "Azure credentials require reauthorization") from exc
    if updated:
        row.encrypted_token_cache = encrypt_azure_token(updated)
        db.commit()
    return token, row


def _selected(row: AzureConnection, subscription_id: str, db: Session) -> AzureSubscription:
    record = db.query(AzureSubscription).filter(
        AzureSubscription.connection_id == row.id,
        AzureSubscription.subscription_id == subscription_id,
        AzureSubscription.selected.is_(True),
    ).first()
    if not record:
        raise HTTPException(403, "Subscription is not selected for this Azure connection")
    return record


@router.get("/oauth/start")
def azure_oauth_start(response: Response, ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    try:
        state, url = begin(ctx.user_id, ctx.organization_id, db)
    except OAuthError as exc:
        raise HTTPException(503, str(exc)) from exc
    response.set_cookie("azure_oauth_state", state, max_age=600, httponly=True, secure=settings.frontend_url.startswith("https://"), samesite="lax", path="/")
    return {"authorization_url": url}


@router.get("/oauth/callback")
def azure_oauth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    if error or not state or not code:
        raise HTTPException(400, "Microsoft authorization was denied or callback parameters are missing", headers=_cookie_clear())
    try:
        oauth_state, payload = redeem(state, request.cookies.get("azure_oauth_state"), code, db)
    except OAuthError as exc:
        raise HTTPException(400, str(exc), headers=_cookie_clear()) from exc
    connection = db.query(AzureConnection).filter(
        AzureConnection.user_id == oauth_state.user_id,
        AzureConnection.organization_id == oauth_state.organization_id,
    ).first()
    if connection is None:
        connection = AzureConnection(user_id=oauth_state.user_id, organization_id=oauth_state.organization_id)
        db.add(connection)
    connection.status = "CONNECTED"
    connection.encrypted_token_cache = encrypt_azure_token(payload)
    connection.last_successful_refresh = datetime.now(timezone.utc)
    db.commit()
    redirect = RedirectResponse(f"{settings.frontend_url}/dashboard#azure=connected", status_code=303)
    redirect.delete_cookie("azure_oauth_state", path="/")
    return redirect


@router.get("/connection", response_model=AzureConnectionResponse)
def azure_connection(ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    row = db.query(AzureConnection).filter(AzureConnection.user_id == ctx.user_id, AzureConnection.organization_id == ctx.organization_id).first()
    if not row:
        return AzureConnectionResponse(id=0, provider="AZURE", connected=False, status="NOT_CONNECTED")
    return AzureConnectionResponse(
        id=row.id,
        provider="AZURE",
        connected=row.status == "CONNECTED",
        status=row.status,
        last_successful_refresh=row.last_successful_refresh,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/connection/service-principal")
def connect_service_principal(data: ServicePrincipalRequest, ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    tenant_id, client_id = data.tenant_id.strip(), data.client_id.strip()
    if not tenant_id or not client_id or not data.client_secret:
        raise HTTPException(422, "Tenant ID, client ID, and client secret are required")
    try:
        payload = service_principal_token(tenant_id, client_id, data.client_secret)
        available = AzureClient(str(payload["access_token"])).subscriptions()
    except (OAuthError, AzureProviderError) as exc:
        raise HTTPException(502, str(exc)) from exc
    accessible_ids = {item.get("subscriptionId") for item in available}
    if data.subscription_id and data.subscription_id not in accessible_ids:
        raise HTTPException(403, "The service principal cannot access the supplied subscription ID")
    row = db.query(AzureConnection).filter(AzureConnection.user_id == ctx.user_id, AzureConnection.organization_id == ctx.organization_id).first()
    if row is None:
        row = AzureConnection(user_id=ctx.user_id, organization_id=ctx.organization_id)
        db.add(row)
    try:
        encrypted_payload = encrypt_azure_token(payload)
    except TokenCryptoError as exc:
        raise HTTPException(503, "Azure token encryption is not configured. Set AZURE_TOKEN_ENCRYPTION_KEY and retry.") from exc
    row.status = "CONNECTED"
    row.encrypted_token_cache = encrypted_payload
    row.last_successful_refresh = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "provider": "AZURE", "connected": True, "status": row.status, "subscription_id": data.subscription_id, "created_at": row.created_at, "updated_at": row.updated_at, "last_successful_refresh": row.last_successful_refresh, "message": "Microsoft Azure service principal connected successfully."}


@router.post("/connection/test")
def test_connection(ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    token, row = _access(ctx, db)
    try:
        AzureClient(token).subscriptions()
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    row.status = "CONNECTED"
    row.last_successful_refresh = datetime.now(timezone.utc)
    db.commit()
    return {"status": row.status, "last_successful_refresh": row.last_successful_refresh, "message": "Azure connection verified successfully."}


@router.post("/subscriptions/discover")
def discover(ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    token, row = _access(ctx, db)
    try:
        items = AzureClient(token).subscriptions()
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    accessible = {item.get("subscriptionId") for item in items}
    result = []
    for item in items:
        sid = item.get("subscriptionId")
        record = db.query(AzureSubscription).filter_by(connection_id=row.id, subscription_id=sid).first()
        if record is None:
            record = AzureSubscription(connection_id=row.id, subscription_id=sid, display_name=item.get("displayName") or sid, tenant_id=item.get("tenantId"), state=item.get("state"))
            db.add(record)
        else:
            record.display_name = item.get("displayName") or record.display_name
            record.state = item.get("state")
        record.last_seen_at = datetime.now(timezone.utc)
        result.append({"id": sid, "display_name": record.display_name, "state": record.state, "tenant_id": record.tenant_id, "selected": record.selected})
    for record in db.query(AzureSubscription).filter_by(connection_id=row.id).all():
        if record.subscription_id not in accessible:
            record.state = "inaccessible"
            record.selected = False
    row.last_successful_refresh = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "subscriptions": result}


@router.post("/subscriptions")
def select(selection: SubscriptionSelection, ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    token, row = _access(ctx, db)
    try:
        accessible = {item.get("subscriptionId") for item in AzureClient(token).subscriptions()}
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    if not set(selection.subscription_ids) <= accessible:
        raise HTTPException(403, "One or more subscriptions are not accessible")
    for record in db.query(AzureSubscription).filter_by(connection_id=row.id).all():
        record.selected = record.subscription_id in set(selection.subscription_ids)
    db.commit()
    return {"status": "ok", "subscription_ids": selection.subscription_ids}


@router.get("/subscriptions/{subscription_id}/resources")
def resources(subscription_id: str, ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    token, row = _access(ctx, db)
    _selected(row, subscription_id, db)
    try:
        return {"status": "ok", "subscription_id": subscription_id, "resources": AzureClient(token).resources(subscription_id)}
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc


@router.get("/subscriptions/{subscription_id}/cost")
def cost(subscription_id: str, start: date = Query(...), end: date = Query(...), ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    if start >= end:
        raise HTTPException(422, "start must be before end")
    token, row = _access(ctx, db)
    _selected(row, subscription_id, db)
    try:
        return {"status": "ok", "subscription_id": subscription_id, "cost": AzureClient(token).cost(subscription_id, start, end)}
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, "Azure cost data is unavailable for this subscription") from exc


@router.delete("/connection")
def disconnect(ctx: RequestContext = Depends(get_current_context), db: Session = Depends(get_db)):
    row = db.query(AzureConnection).filter(AzureConnection.user_id == ctx.user_id, AzureConnection.organization_id == ctx.organization_id).first()
    if row:
        db.delete(row)
        db.commit()
    return {"status": "disconnected"}
