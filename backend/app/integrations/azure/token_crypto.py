import json
from app.config import settings

class TokenCryptoError(RuntimeError): pass
def encrypt(payload: dict[str, object]) -> str:
    if not settings.azure_token_encryption_key: raise TokenCryptoError("AZURE_TOKEN_ENCRYPTION_KEY is required")
    try:
        from cryptography.fernet import Fernet
        return Fernet(settings.azure_token_encryption_key.encode()).encrypt(json.dumps(payload).encode()).decode()
    except Exception as exc: raise TokenCryptoError("Invalid Azure token encryption configuration") from exc
def decrypt(value: str) -> dict[str, object]:
    try:
        from cryptography.fernet import Fernet
        return json.loads(Fernet(settings.azure_token_encryption_key.encode()).decrypt(value.encode()))
    except Exception as exc: raise TokenCryptoError("Stored Azure token cache could not be decrypted") from exc
