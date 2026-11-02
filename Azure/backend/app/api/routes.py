import re
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.db.models import AzureConnection, AzureSubscription
from app.providers.azure.auth import OAuthError, OAuthService, access_token
from app.providers.azure.client import AzureClient, AzureProviderError
from app.providers.azure.manual import manual_tokens
from app.providers.azure.token_crypto import TokenCryptoError, decrypt, encrypt
from app.providers.catalog import PROVIDERS

oauth = OAuthService(get_settings())


def platform_user(request: Request, x_platform_user_id: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if not settings.allow_local_platform_user_header or settings.app_env != "development":
        raise HTTPException(401, "Platform authentication is required")
    user_id = x_platform_user_id or request.cookies.get(settings.dev_identity_cookie)
    if not user_id:
        raise HTTPException(401, "Local development identity is required")
    return user_id


class SubscriptionSelection(BaseModel):
    subscription_ids: list[str]


class DevIdentityRequest(BaseModel):
    user_id: str


class ManualTokenRequest(BaseModel):
    access_token: str

router = APIRouter()


def _clear_oauth_cookie_header() -> str:
    settings = get_settings()
    secure = "; Secure" if settings.app_env not in ("development", "test") else ""
    return f"{settings.oauth_state_cookie}=; Max-Age=0; Path=/api/azure/oauth; HttpOnly; SameSite=Lax{secure}"


def _dev_only() -> None:
    settings = get_settings()
    if settings.app_env != "development" or not settings.allow_local_platform_user_header:
        raise HTTPException(404, "Development-only functionality is disabled")


def _manual_enabled() -> None:
    _dev_only()
    if not get_settings().enable_manual_azure_token_input:
        raise HTTPException(404, "Manual Azure token input is disabled")


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": get_settings().app_name}


@router.get("/api/providers", tags=["providers"])
def list_providers() -> dict[str, list[dict[str, object]]]:
    return {"providers": [provider.__dict__ for provider in PROVIDERS]}


@router.post("/api/dev/session", tags=["development"])
def create_dev_session(payload: DevIdentityRequest, response: Response) -> dict[str, str]:
    _dev_only()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", payload.user_id):
        raise HTTPException(422, "Invalid local development identity")
    response.set_cookie(get_settings().dev_identity_cookie, payload.user_id, max_age=86400, httponly=True, secure=False, samesite="lax", path="/")
    return {"status": "ok", "message": "Local development identity configured"}


@router.delete("/api/dev/session", tags=["development"])
def delete_dev_session(response: Response) -> dict[str, str]:
    _dev_only()
    response.delete_cookie(get_settings().dev_identity_cookie, path="/")
    return {"status": "ok"}


@router.post("/api/azure/dev/manual-token", tags=["development"])
def set_manual_token(payload: ManualTokenRequest, user_id: str = Depends(platform_user)) -> dict[str, str]:
    _manual_enabled()
    if not payload.access_token.strip():
        raise HTTPException(422, "A temporary Azure access token is required")
    manual_tokens.set(user_id, payload.access_token)
    return {"status": "ok", "message": "Temporary token held in backend memory only"}


@router.delete("/api/azure/dev/manual-token", tags=["development"])
def clear_manual_token(user_id: str = Depends(platform_user)) -> dict[str, str]:
    _manual_enabled()
    manual_tokens.clear(user_id)
    return {"status": "cleared"}


@router.get("/api/azure/oauth/start", tags=["azure"])
def azure_oauth_start(user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> RedirectResponse:
    try:
        state, url = oauth.begin(user_id, db)
        redirect = RedirectResponse(url, status_code=307)
        redirect.set_cookie(get_settings().oauth_state_cookie, state, max_age=600, httponly=True, secure=get_settings().app_env not in ("development", "test"), samesite="lax", path="/api/azure/oauth")
        return redirect
    except OAuthError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/api/azure/oauth/callback", tags=["azure"])
def azure_oauth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None, db: Session = Depends(get_db)) -> Response:
    if error:
        if state:
            try:
                oauth.redeem(state, request.cookies.get(get_settings().oauth_state_cookie), "", db)
            except OAuthError:
                pass
        raise HTTPException(400, "Microsoft authorization was denied", headers={"Set-Cookie": _clear_oauth_cookie_header()})
    if not state or not code:
        raise HTTPException(400, "Missing OAuth callback parameters", headers={"Set-Cookie": _clear_oauth_cookie_header()})
    try:
        user_id, token_payload = oauth.redeem(state, request.cookies.get(get_settings().oauth_state_cookie), code, db)
    except OAuthError as exc:
        raise HTTPException(400, str(exc), headers={"Set-Cookie": _clear_oauth_cookie_header()}) from exc
    if not get_settings().azure_token_encryption_key:
        raise HTTPException(503, "AZURE_TOKEN_ENCRYPTION_KEY is required before connecting")
    connection = db.query(AzureConnection).filter_by(platform_user_id=user_id).first()
    if not connection:
        connection = AzureConnection(platform_user_id=user_id, status="connected")
        db.add(connection)
    connection.status = "connected"
    try:
        connection.encrypted_token_cache = encrypt(token_payload, get_settings())
    except TokenCryptoError as exc:
        db.rollback()
        raise HTTPException(503, str(exc), headers={"Set-Cookie": _clear_oauth_cookie_header()}) from exc
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, "Azure connection could not be persisted", headers={"Set-Cookie": _clear_oauth_cookie_header()}) from exc
    result = Response(content='{"status":"connected","message":"Azure connected; discover subscriptions next"}', media_type="application/json")
    result.delete_cookie(get_settings().oauth_state_cookie, path="/api/azure/oauth")
    return result


@router.get("/api/azure/connection", tags=["azure"])
def azure_connection(user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, object]:
    connection = db.query(AzureConnection).filter_by(platform_user_id=user_id).with_for_update().first()
    if not connection:
        return {"connected": False, "status": "not_connected"}
    return {"connected": True, "status": connection.status, "last_successful_refresh": connection.last_successful_refresh}


def _connection(user_id: str, db: Session) -> AzureConnection:
    connection = db.query(AzureConnection).filter_by(platform_user_id=user_id).first()
    if not connection or connection.status != "connected":
        raise HTTPException(409, "Azure connection is not active; reauthorize first")
    if not connection.encrypted_token_cache:
        raise HTTPException(409, "Azure connection requires reauthorization")
    try:
        payload = decrypt(connection.encrypted_token_cache, get_settings())
        token, updated = access_token(payload, get_settings())
        connection._azure_access_token = token
        if updated:
            connection.encrypted_token_cache = encrypt(updated, get_settings())
            db.commit()
    except TokenCryptoError as exc:
        connection.status = "reauthorization_required"
        db.commit()
        raise HTTPException(409, "Azure credentials require reauthorization") from exc
    except OAuthError as exc:
        connection.status = "reauthorization_required"
        db.commit()
        raise HTTPException(409, str(exc)) from exc
    return connection


def _access(user_id: str, db: Session) -> tuple[str, AzureConnection | None]:
    manual = manual_tokens.get(user_id)
    if manual:
        _manual_enabled()
        return manual, None
    connection = _connection(user_id, db)
    return connection._azure_access_token, connection


def _selected_subscription(connection: AzureConnection | None, subscription_id: str, db: Session, user_id: str) -> AzureSubscription | None:
    if not re.fullmatch(r"[0-9a-fA-F-]{20,64}", subscription_id):
        raise HTTPException(422, "Invalid subscription ID")
    if connection is None:
        if subscription_id not in manual_tokens.selected(user_id):
            raise HTTPException(403, "Subscription is not selected for this development token")
        return None
    record = db.query(AzureSubscription).filter_by(connection_id=connection.id, subscription_id=subscription_id, selected=True).first()
    if not record:
        raise HTTPException(403, "Subscription is not selected for this connection")
    return record


@router.post("/api/azure/subscriptions/discover", tags=["azure"])
def discover_subscriptions(user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, object]:
    token, connection = _access(user_id, db)
    client = AzureClient(token)
    try:
        items = client.subscriptions()
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    if connection is None:
        selected = manual_tokens.selected(user_id)
        return {"status": "ok", "mode": "manual_development", "subscriptions": [{"id": item.get("subscriptionId"), "display_name": item.get("displayName"), "state": item.get("state"), "tenant_id": item.get("tenantId"), "selected": item.get("subscriptionId") in selected} for item in items]}
    result = []
    refreshed_at = datetime.now(UTC)
    accessible_ids = {item.get("subscriptionId") for item in items}
    for item in items:
        sid = item.get("subscriptionId")
        record = db.query(AzureSubscription).filter_by(connection_id=connection.id, subscription_id=sid).first()
        if not record:
            record = AzureSubscription(connection_id=connection.id, subscription_id=sid, display_name=item.get("displayName") or sid, tenant_id=item.get("tenantId"), state=item.get("state"))
            db.add(record)
        else:
            record.display_name = item.get("displayName") or record.display_name
            record.state = item.get("state")
        record.last_seen_at = refreshed_at
        result.append({"id": sid, "display_name": item.get("displayName"), "state": item.get("state"), "tenant_id": item.get("tenantId"), "selected": record.selected})
    for record in db.query(AzureSubscription).filter_by(connection_id=connection.id).all():
        if record.subscription_id not in accessible_ids:
            record.state = "inaccessible"
            record.selected = False
    connection.last_successful_refresh = refreshed_at
    db.commit()
    return {"status": "ok", "subscriptions": result}


@router.post("/api/azure/subscriptions", tags=["azure"])
def select_subscriptions(selection: SubscriptionSelection, user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, object]:
    if len(selection.subscription_ids) != len(set(selection.subscription_ids)):
        raise HTTPException(422, "Duplicate subscription IDs are not allowed")
    token, connection = _access(user_id, db)
    client = AzureClient(token)
    try:
        accessible = {x.get("subscriptionId") for x in client.subscriptions()}
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    if not set(selection.subscription_ids) <= accessible:
        raise HTTPException(403, "One or more subscriptions are not accessible through this connection")
    if connection is None:
        manual_tokens.select(user_id, set(selection.subscription_ids))
        return {"status": "ok", "mode": "manual_development", "subscription_ids": selection.subscription_ids}
    records = db.query(AzureSubscription).filter(AzureSubscription.connection_id == connection.id).all()
    for record in records:
        record.selected = record.subscription_id in selection.subscription_ids
    db.commit()
    return {"status": "ok", "subscription_ids": selection.subscription_ids}


@router.get("/api/azure/subscriptions/{subscription_id}/resources", tags=["azure"])
def azure_resources(subscription_id: str, user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, object]:
    token, connection = _access(user_id, db)
    _selected_subscription(connection, subscription_id, db, user_id)
    try:
        resources = AzureClient(token).resources(subscription_id)
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, str(exc)) from exc
    return {"status": "ok", "subscription_id": subscription_id, "resources": resources}


@router.get("/api/azure/subscriptions/{subscription_id}/cost", tags=["azure"])
def azure_cost(subscription_id: str, start: date = Query(...), end: date = Query(...), user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, object]:
    if start >= end:
        raise HTTPException(422, "start must be before end")
    token, connection = _access(user_id, db)
    _selected_subscription(connection, subscription_id, db, user_id)
    try:
        cost = AzureClient(token).cost(subscription_id, start, end)
    except AzureProviderError as exc:
        raise HTTPException(exc.status_code or 502, "Cost data is unavailable for this subscription") from exc
    return {"status": "ok", "subscription_id": subscription_id, "cost": cost}


@router.delete("/api/azure/connection", tags=["azure"])
def disconnect_azure(user_id: str = Depends(platform_user), db: Session = Depends(get_db)) -> dict[str, str]:
    manual_tokens.clear(user_id)
    connection = db.query(AzureConnection).filter_by(platform_user_id=user_id).first()
    if connection:
        db.delete(connection)
        db.commit()
    return {"status": "disconnected"}
