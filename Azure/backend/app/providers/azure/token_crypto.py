import json

from app.core.config import Settings


class TokenCryptoError(RuntimeError):
    pass


def encrypt(payload: dict[str, object], settings: Settings) -> str:
    if not settings.azure_token_encryption_key:
        raise TokenCryptoError("AZURE_TOKEN_ENCRYPTION_KEY is required")
    try:
        from cryptography.fernet import Fernet
        return Fernet(settings.azure_token_encryption_key.encode()).encrypt(json.dumps(payload).encode()).decode()
    except ImportError as exc:
        raise TokenCryptoError("cryptography package is required for token persistence") from exc
    except Exception as exc:
        raise TokenCryptoError("invalid token encryption configuration") from exc


def decrypt(value: str, settings: Settings) -> dict[str, object]:
    try:
        from cryptography.fernet import Fernet
        return json.loads(Fernet(settings.azure_token_encryption_key.encode()).decrypt(value.encode()))
    except Exception as exc:
        raise TokenCryptoError("stored Azure token cache could not be decrypted") from exc
