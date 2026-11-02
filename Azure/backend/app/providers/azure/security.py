import base64
import hashlib
import secrets
from urllib.parse import quote


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorization_url(tenant: str, client_id: str, redirect_uri: str, state: str, challenge: str, scopes: str) -> str:
    params = {
        "client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri,
        "response_mode": "query", "scope": f"openid profile offline_access {scopes}",
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
    }
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + "&".join(
        f"{quote(k)}={quote(v)}" for k, v in params.items()
    )


def new_state() -> str:
    return secrets.token_urlsafe(32)
