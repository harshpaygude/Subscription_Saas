"""Authenticated Fernet credential encryption for Integration Service."""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict

from app.config import settings


class CredentialStorageError(Exception):
    """Raised when provider credentials cannot be safely encrypted or decrypted."""


class TokenCryptoError(RuntimeError):
    """Raised when Azure OAuth token cache cannot be encrypted or decrypted."""


def _fernet():
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret_key.encode()).digest())
    return Fernet(key)


def encrypt_credentials(credentials: Dict[str, Any]) -> str:
    try:
        return _fernet().encrypt(json.dumps(credentials).encode()).decode()
    except Exception as exc:
        raise CredentialStorageError("Provider credentials could not be encrypted safely.") from exc


def decrypt_credentials(value: str) -> Dict[str, Any]:
    try:
        return json.loads(_fernet().decrypt(value.encode()).decode())
    except Exception as exc:
        raise CredentialStorageError("Stored provider credentials could not be decrypted safely.") from exc


def encrypt_azure_token(payload: dict[str, object]) -> str:
    if not settings.azure_token_encryption_key:
        raise TokenCryptoError("AZURE_TOKEN_ENCRYPTION_KEY is required")
    try:
        from cryptography.fernet import Fernet
        return Fernet(settings.azure_token_encryption_key.encode()).encrypt(json.dumps(payload).encode()).decode()
    except Exception as exc:
        raise TokenCryptoError("Invalid Azure token encryption configuration") from exc


def decrypt_azure_token(value: str) -> dict[str, object]:
    try:
        from cryptography.fernet import Fernet
        return json.loads(Fernet(settings.azure_token_encryption_key.encode()).decrypt(value.encode()))
    except Exception as exc:
        raise TokenCryptoError("Stored Azure token cache could not be decrypted") from exc
