"""Shared authenticated encryption for provider credentials."""
import base64
import hashlib
import json
from typing import Any, Dict

from app.config import settings


class CredentialStorageError(Exception):
    """Raised when provider credentials cannot be safely encrypted or decrypted."""


def _fernet():
    from cryptography.fernet import Fernet

    # Preserve the existing application encryption scheme so AWS credentials
    # and new provider credentials remain decryptable by the same deployment.
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
