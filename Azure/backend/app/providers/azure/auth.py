from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import httpx
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AzureOAuthState
from app.providers.azure.security import authorization_url, new_state, pkce_pair
from app.providers.azure.token_crypto import TokenCryptoError, decrypt, encrypt


class OAuthError(RuntimeError):
    pass


class OAuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def begin(self, user_id: str, db: Session) -> tuple[str, str]:
        if not self.settings.azure_client_id:
            raise OAuthError("Azure OAuth is not configured")
        if not self.settings.azure_token_encryption_key:
            raise OAuthError("AZURE_TOKEN_ENCRYPTION_KEY is required before connecting")
        state = new_state()
        verifier, challenge = pkce_pair()
        now = datetime.now(UTC)
        try:
            db.query(AzureOAuthState).filter(AzureOAuthState.expires_at < now).delete()
            db.add(AzureOAuthState(state_hash=sha256(state.encode()).hexdigest(), platform_user_id=user_id, encrypted_code_verifier=encrypt({"verifier": verifier}, self.settings), expires_at=now + timedelta(minutes=10)))
            db.commit()
        except (SQLAlchemyError, TokenCryptoError) as exc:
            db.rollback()
            raise OAuthError("OAuth state could not be persisted") from exc
        return state, authorization_url(self.settings.azure_tenant, self.settings.azure_client_id, self.settings.azure_redirect_uri, state, challenge, self.settings.azure_scopes)

    def redeem(self, state: str, callback_state: str | None, code: str, db: Session) -> tuple[str, dict[str, Any]]:
        if not state or state != callback_state:
            raise OAuthError("OAuth state cookie is missing or does not match the callback")
        now = datetime.now(UTC)
        state_hash = sha256(state.encode()).hexdigest()
        # Conditional update makes consumption atomic: concurrent callbacks can
        # never both observe an unconsumed record and proceed.
        try:
            result = db.execute(update(AzureOAuthState).where(AzureOAuthState.state_hash == state_hash, AzureOAuthState.consumed_at.is_(None), AzureOAuthState.expires_at >= now).values(consumed_at=now))
            if result.rowcount != 1:
                db.rollback()
                raise OAuthError("Invalid, expired, or already-used OAuth state")
            # Commit consumption before decrypting or calling Microsoft. A
            # malformed verifier or remote failure must not make state reusable.
            db.commit()
            record = db.query(AzureOAuthState).filter_by(state_hash=state_hash).first()
            if record is None:
                raise OAuthError("Invalid OAuth state")
            verifier = str(decrypt(record.encrypted_code_verifier, self.settings)["verifier"])
        except OAuthError:
            raise
        except (SQLAlchemyError, TokenCryptoError, KeyError, TypeError, ValueError) as exc:
            db.rollback()
            raise OAuthError("OAuth state could not be consumed") from exc
        if not code:
            raise OAuthError("Microsoft did not return an authorization code")
        data = {"client_id": self.settings.azure_client_id, "client_secret": self.settings.azure_client_secret, "grant_type": "authorization_code", "code": code, "redirect_uri": self.settings.azure_redirect_uri, "scope": self.settings.azure_scopes, "code_verifier": verifier}
        try:
            response = httpx.post(f"https://login.microsoftonline.com/{self.settings.azure_tenant}/oauth2/v2.0/token", data=data, timeout=20)
        except httpx.HTTPError as exc:
            raise OAuthError("Microsoft token exchange failed") from exc
        if response.status_code >= 400:
            raise OAuthError("Microsoft token exchange was rejected")
        payload = response.json()
        if not payload.get("access_token"):
            raise OAuthError("Microsoft token response did not contain an access token")
        payload["expires_at"] = int(now.timestamp()) + int(payload.get("expires_in", 3600))
        return record.platform_user_id, payload


def access_token(payload: dict[str, Any], settings: Settings) -> tuple[str, dict[str, Any] | None]:
    """Return a usable token; refresh once when an expiry is known/passed."""
    now = int(datetime.now(UTC).timestamp())
    if int(payload.get("expires_at", 0)) > now + 60:
        return str(payload["access_token"]), None
    refresh = payload.get("refresh_token")
    if not refresh:
        raise OAuthError("Azure access has expired; reauthorization is required")
    try:
        response = httpx.post(f"https://login.microsoftonline.com/{settings.azure_tenant}/oauth2/v2.0/token", data={"client_id": settings.azure_client_id, "client_secret": settings.azure_client_secret, "grant_type": "refresh_token", "refresh_token": refresh, "scope": settings.azure_scopes}, timeout=20)
    except httpx.HTTPError as exc:
        raise OAuthError("Microsoft token renewal failed") from exc
    if response.status_code >= 400 or not response.json().get("access_token"):
        raise OAuthError("Azure access was revoked; reauthorization is required")
    updated = {**payload, **response.json(), "expires_at": now + int(response.json().get("expires_in", 3600))}
    return str(updated["access_token"]), updated
