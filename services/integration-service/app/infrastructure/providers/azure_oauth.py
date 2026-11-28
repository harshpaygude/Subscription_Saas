"""Azure Entra OAuth + PKCE & Service Principal token exchange."""
from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.infrastructure.crypto import TokenCryptoError, decrypt_azure_token, encrypt_azure_token
from app.infrastructure.models import AzureOAuthState


class OAuthError(RuntimeError):
    pass


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorization_url(tenant: str, client_id: str, redirect_uri: str, state: str, challenge: str, scopes: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": f"openid profile offline_access {scopes}",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + "&".join(
        f"{quote(k)}={quote(v)}" for k, v in params.items()
    )


def new_state() -> str:
    return secrets.token_urlsafe(32)


def _client_id():
    return settings.azure_client_id or settings.microsoft_client_id


def _client_secret():
    return settings.azure_client_secret or settings.microsoft_client_secret


def _tenant():
    return settings.azure_tenant or settings.microsoft_tenant_id


def begin(user_id: int, organization_id: int, db: Session):
    if not _client_id() or not _client_secret():
        raise OAuthError("Azure OAuth client credentials are not configured")
    if not settings.azure_token_encryption_key:
        raise OAuthError("AZURE_TOKEN_ENCRYPTION_KEY is required before connecting")
    state = new_state()
    verifier, challenge = pkce_pair()
    now = datetime.now(timezone.utc)
    try:
        db.query(AzureOAuthState).filter(AzureOAuthState.expires_at < now).delete()
        db.add(
            AzureOAuthState(
                user_id=user_id,
                organization_id=organization_id,
                state_hash=hashlib.sha256(state.encode()).hexdigest(),
                encrypted_code_verifier=encrypt_azure_token({"verifier": verifier}),
                expires_at=now + timedelta(minutes=10),
            )
        )
        db.commit()
    except (SQLAlchemyError, TokenCryptoError) as exc:
        db.rollback()
        raise OAuthError("Azure OAuth state could not be persisted") from exc
    return state, authorization_url(_tenant(), _client_id(), settings.azure_redirect_uri, state, challenge, settings.azure_scopes)


def redeem(state: str, callback_state: str | None, code: str, db: Session):
    if not state or state != callback_state:
        raise OAuthError("OAuth state is missing or does not match")
    now = datetime.now(timezone.utc)
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    result = db.execute(
        update(AzureOAuthState)
        .where(AzureOAuthState.state_hash == state_hash, AzureOAuthState.consumed_at.is_(None), AzureOAuthState.expires_at >= now)
        .values(consumed_at=now)
    )
    if result.rowcount != 1:
        db.rollback()
        raise OAuthError("Invalid, expired, or already-used OAuth state")
    db.commit()
    record = db.query(AzureOAuthState).filter_by(state_hash=state_hash).first()
    if record is None:
        raise OAuthError("Invalid OAuth state")
    try:
        verifier = str(decrypt_azure_token(record.encrypted_code_verifier)["verifier"])
    except (TokenCryptoError, KeyError) as exc:
        raise OAuthError("OAuth verifier could not be read") from exc
    try:
        response = httpx.post(
            f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token",
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.azure_redirect_uri,
                "scope": settings.azure_scopes,
                "code_verifier": verifier,
            },
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise OAuthError("Microsoft token exchange failed") from exc
    if response.status_code >= 400:
        raise OAuthError("Microsoft token exchange was rejected")
    payload = response.json()
    if not payload.get("access_token"):
        raise OAuthError("Microsoft token response did not contain an access token")
    payload["expires_at"] = int(now.timestamp()) + int(payload.get("expires_in", 3600))
    return record, payload


def access_token(payload: dict[str, Any]):
    now = int(datetime.now(timezone.utc).timestamp())
    if int(payload.get("expires_at", 0)) > now + 60:
        return str(payload["access_token"]), None
    if payload.get("auth_type") == "service_principal":
        try:
            response = httpx.post(
                f"https://login.microsoftonline.com/{payload['tenant_id']}/oauth2/v2.0/token",
                data={"client_id": payload["client_id"], "client_secret": payload["client_secret"], "grant_type": "client_credentials", "scope": "https://management.azure.com/.default"},
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
    if not refresh:
        raise OAuthError("Azure access has expired; reauthorization is required")
    response = httpx.post(
        f"https://login.microsoftonline.com/{_tenant()}/oauth2/v2.0/token",
        data={"client_id": _client_id(), "client_secret": _client_secret(), "grant_type": "refresh_token", "refresh_token": refresh, "scope": settings.azure_scopes},
        timeout=20,
    )
    if response.status_code >= 400 or not response.json().get("access_token"):
        raise OAuthError("Azure access was revoked; reauthorization is required")
    updated = {**payload, **response.json(), "expires_at": now + int(response.json().get("expires_in", 3600))}
    return str(updated["access_token"]), updated


def service_principal_token(tenant_id: str, client_id: str, client_secret: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials", "scope": "https://management.azure.com/.default"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise OAuthError("Microsoft token service could not be reached") from exc
    if response.status_code >= 400 or not response.json().get("access_token"):
        raise OAuthError("Microsoft service-principal credentials were rejected")
    now = int(datetime.now(timezone.utc).timestamp())
    token = response.json()
    return {"auth_type": "service_principal", "tenant_id": tenant_id, "client_id": client_id, "client_secret": client_secret, **token, "expires_at": now + int(token.get("expires_in", 3600))}
