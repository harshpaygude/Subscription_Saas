from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
cryptography = pytest.importorskip("cryptography")

from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.database import Base
from app.db.models import AzureConnection, AzureSubscription
from app.providers.azure.auth import OAuthError, OAuthService, access_token
from app.providers.azure.token_crypto import TokenCryptoError, decrypt, encrypt


class FakeResponse:
    status_code = 200

    def json(self):
        return {"access_token": "access", "expires_in": 3600, "refresh_token": "refresh"}


class RefreshResponseWithoutRotation(FakeResponse):
    def json(self):
        return {"access_token": "access", "expires_in": 3600}


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        azure_client_id="client-id",
        azure_client_secret="client-secret",
        azure_token_encryption_key=Fernet.generate_key().decode(),
        azure_redirect_uri="http://localhost:8000/api/azure/oauth/callback",
    )


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_token_encryption_fails_closed(settings: Settings) -> None:
    encrypted = encrypt({"access_token": "never-returned"}, settings)
    assert decrypt(encrypted, settings)["access_token"] == "never-returned"
    with pytest.raises(TokenCryptoError):
        decrypt(encrypted, settings.model_copy(update={"azure_token_encryption_key": ""}))


def test_oauth_state_is_single_use_and_cookie_bound(monkeypatch, settings, session_factory) -> None:
    monkeypatch.setattr("app.providers.azure.auth.httpx.post", lambda *args, **kwargs: FakeResponse())
    service = OAuthService(settings)
    first = session_factory()
    state, _ = service.begin("user-a", first)
    first.close()

    callback = session_factory()
    owner, payload = service.redeem(state, state, "authorization-code", callback)
    assert owner == "user-a"
    assert payload["access_token"] == "access"
    callback.close()

    replay = session_factory()
    with pytest.raises(OAuthError):
        service.redeem(state, state, "authorization-code", replay)
    replay.close()


def test_oauth_state_only_one_concurrent_callback_succeeds(monkeypatch, settings, session_factory) -> None:
    monkeypatch.setattr("app.providers.azure.auth.httpx.post", lambda *args, **kwargs: FakeResponse())
    service = OAuthService(settings)
    creator = session_factory()
    state, _ = service.begin("user-a", creator)
    creator.close()

    def redeem_once():
        db = session_factory()
        try:
            service.redeem(state, state, "authorization-code", db)
            return True
        except OAuthError:
            return False
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: redeem_once(), range(2)))
    assert results.count(True) == 1


def test_refresh_preserves_existing_refresh_token_when_not_rotated(monkeypatch, settings) -> None:
    monkeypatch.setattr("app.providers.azure.auth.httpx.post", lambda *args, **kwargs: RefreshResponseWithoutRotation())
    token, updated = access_token({"access_token": "old", "refresh_token": "old-refresh", "expires_at": 0}, settings)
    assert token == "access"
    assert updated is not None
    assert updated["refresh_token"] == "old-refresh"


def test_selected_subscription_is_connection_scoped(session_factory) -> None:
    from fastapi import HTTPException

    from app.api.routes import _selected_subscription

    db = session_factory()
    first = AzureConnection(platform_user_id="user-a", status="connected")
    second = AzureConnection(platform_user_id="user-b", status="connected")
    db.add_all([first, second])
    db.flush()
    db.add(AzureSubscription(connection_id=first.id, subscription_id="12345678-1234-1234-1234-123456789012", display_name="A", selected=True))
    db.commit()
    db.refresh(second)
    with pytest.raises(HTTPException) as error:
        _selected_subscription(second, "12345678-1234-1234-1234-123456789012", db, "user-b")
    assert error.value.status_code == 403
    db.close()


def test_production_rejects_development_identity_header(monkeypatch) -> None:
    from app.api.routes import platform_user

    monkeypatch.setattr("app.api.routes.get_settings", lambda: SimpleNamespace(app_env="production", allow_local_platform_user_header=True))
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        platform_user(SimpleNamespace(cookies={}), "spoofed-user")
    assert error.value.status_code == 401
