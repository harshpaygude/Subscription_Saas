"""Infrastructure security adapters (bcrypt + JWT) for Identity Service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher:
    def hash(self, password: str) -> str:
        return _pwd_context.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return _pwd_context.verify(plain_password, hashed_password)


class JoseTokenIssuer:
    def __init__(self, secret_key: str | None = None, algorithm: str | None = None):
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm or settings.jwt_algorithm

    def create_access_token(self, payload: dict[str, Any], expires_minutes: int = 60) -> str:
        to_encode = dict(payload)
        to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
