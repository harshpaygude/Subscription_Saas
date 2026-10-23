from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
import httpx
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.config import settings
from app.database.models import AzureOAuthState, User
from .security import authorization_url, new_state, pkce_pair
from .token_crypto import TokenCryptoError, decrypt, encrypt

class OAuthError(RuntimeError): pass
def _client_id(): return settings.azure_client_id or settings.microsoft_client_id
def _client_secret(): return settings.azure_client_secret or settings.microsoft_client_secret
def _tenant(): return settings.azure_tenant or settings.microsoft_tenant_id
def _redirect(): return settings.azure_redirect_uri
def _scopes(): return settings.azure_scopes
def begin(user: User, db: Session):
    if not _client_id() or not _client_secret(): raise OAuthError("Azure OAuth client credentials are not configured")
    if not settings.azure_token_encryption_key: raise OAuthError("AZURE_TOKEN_ENCRYPTION_KEY is required before connecting")
    state = new_state(); verifier, challenge = pkce_pair(); now = datetime.now(timezone.utc)
    try:
        db.query(AzureOAuthState).filter(AzureOAuthState.expires_at < now).delete()
        db.add(AzureOAuthState(user_id=user.id, organization_id=user.organization_id, state_hash=sha256(state.encode()).hexdigest(), encrypted_code_verifier=encrypt({"verifier": verifier}), expires_at=now + timedelta(minutes=10)))
        db.commit()
    except (SQLAlchemyError, TokenCryptoError) as exc:
        db.rollback()
        raise OAuthError("Azure OAuth state could not be persisted") from exc
    return state, authorization_url(_tenant(), _client_id(), _redirect(), state, challenge, _scopes())
def redeem(state: str, callback_state: str | None, code: str, db: Session):
    if not state or state != callback_state: raise OAuthError("OAuth state is missing or does not match")
    now = datetime.now(timezone.utc); state_hash = sha256(state.encode()).hexdigest()
    result = db.execute(update(AzureOAuthState).where(AzureOAuthState.state_hash == state_hash, AzureOAuthState.consumed_at.is_(None), AzureOAuthState.expires_at >= now).values(consumed_at=now))
    if result.rowcount != 1: db.rollback(); raise OAuthError("Invalid, expired, or already-used OAuth state")
    db.commit(); record = db.query(AzureOAuthState).filter_by(state_hash=state_hash).first()
    if record is None: raise OAuthError("Invalid OAuth state")
    try: verifier = str(decrypt(record.encrypted_code_verifier)["verifier"])
    except (TokenCryptoError, KeyError) as exc: raise OAuthError("OAuth verifier could not be read") from exc
    try: response = httpx.post(f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token", data={"client_id": _client_id(), "client_secret": _client_secret(), "grant_type": "authorization_code", "code": code, "redirect_uri": _redirect(), "scope": _scopes(), "code_verifier": verifier}, timeout=20)
    except httpx.HTTPError as exc: raise OAuthError("Microsoft token exchange failed") from exc
    if response.status_code >= 400: raise OAuthError("Microsoft token exchange was rejected")
    payload = response.json()
    if not payload.get("access_token"): raise OAuthError("Microsoft token response did not contain an access token")
    payload["expires_at"] = int(now.timestamp()) + int(payload.get("expires_in", 3600))
    return record, payload
def access_token(payload: dict[str, Any]):
    now = int(datetime.now(timezone.utc).timestamp())
    if int(payload.get("expires_at", 0)) > now + 60: return str(payload["access_token"]), None
    if payload.get("auth_type") == "service_principal":
        try:
            response = httpx.post(
                f"https://login.microsoftonline.com/{payload['tenant_id']}/oauth2/v2.0/token",
                data={
                    "client_id": payload["client_id"],
                    "client_secret": payload["client_secret"],
                    "grant_type": "client_credentials",
                    "scope": "https://management.azure.com/.default",
                },
                timeout=20,
            )
        except (KeyError, httpx.HTTPError) as exc:
            raise OAuthError("Microsoft service-principal credentials are invalid") from exc
        if response.status_code >= 400 or not response.json().get("access_token"):
            raise OAuthError("Microsoft service-principal credentials were rejected")
        refreshed = response.json()
        updated = {**payload, **refreshed, "expires_at": now + int(refreshed.get("expires_in", 3600))}
        return str(updated["access_token"]), updated
    refresh = payload.get("refresh_token")
    if not refresh: raise OAuthError("Azure access has expired; reauthorization is required")
    response = httpx.post(f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token", data={"client_id": _client_id(), "client_secret": _client_secret(), "grant_type": "refresh_token", "refresh_token": refresh, "scope": _scopes()}, timeout=20)
    if response.status_code >= 400 or not response.json().get("access_token"): raise OAuthError("Azure access was revoked; reauthorization is required")
    updated = {**payload, **response.json(), "expires_at": now + int(response.json().get("expires_in", 3600))}; return str(updated["access_token"]), updated


def service_principal_token(tenant_id: str, client_id: str, client_secret: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": "https://management.azure.com/.default",
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise OAuthError("Microsoft token service could not be reached") from exc
    if response.status_code >= 400 or not response.json().get("access_token"):
        raise OAuthError("Microsoft service-principal credentials were rejected")
    now = int(datetime.now(timezone.utc).timestamp())
    token = response.json()
    return {
        "auth_type": "service_principal",
        "tenant_id": tenant_id,
        "client_id": client_id,
        "client_secret": client_secret,
        **token,
        "expires_at": now + int(token.get("expires_in", 3600)),
    }
