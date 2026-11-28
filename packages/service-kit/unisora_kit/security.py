"""Internal service authentication and verified user context extraction."""
from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

ADMIN_ROLES = {"OWNER", "ADMIN", "ASSET_MANAGER"}
_bearer = HTTPBearer(auto_error=False)

HEADER_USER_ID = "X-User-Id"
HEADER_ORG_ID = "X-Organization-Id"
HEADER_USER_ROLE = "X-User-Role"
HEADER_USER_EMAIL = "X-User-Email"
HEADER_INTERNAL_TOKEN = "X-Internal-Service-Token"


@dataclass(frozen=True)
class RequestContext:
    """Authenticated caller identity propagated from API Gateway or verified JWT."""

    user_id: int
    organization_id: int
    role: str
    email: Optional[str] = None
    request_id: Optional[str] = None
    is_internal_service: bool = False


def create_internal_service_token(
    secret: str,
    service_name: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    role: str | None = None,
) -> str:
    """Create a short-lived HMAC signature authenticating internal gateway/service calls."""
    msg = f"{service_name}:{user_id or ''}:{organization_id or ''}:{role or ''}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{service_name}:{sig}"


def verify_internal_service_token(
    token: str,
    secret: str,
    user_id: int | None = None,
    organization_id: int | None = None,
    role: str | None = None,
) -> bool:
    if ":" not in token:
        return False
    service_name, _ = token.split(":", 1)
    expected = create_internal_service_token(secret, service_name, user_id, organization_id, role)
    return hmac.compare_digest(token, expected)


def _decode_bearer_jwt(token: str, jwt_secret: str, jwt_algorithm: str) -> Optional[dict]:
    try:
        return jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
    except Exception:
        return None


def get_request_context(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    internal_secret: str = "",
):
    """Build a FastAPI dependency resolving RequestContext from gateway headers or Bearer JWT."""

    def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> RequestContext:
        request_id = request.headers.get("X-Request-ID")

        # 1. Verified Gateway / trusted internal service headers
        hdr_uid = request.headers.get(HEADER_USER_ID)
        hdr_oid = request.headers.get(HEADER_ORG_ID)
        hdr_role = request.headers.get(HEADER_USER_ROLE)
        hdr_internal = request.headers.get(HEADER_INTERNAL_TOKEN)

        if hdr_internal and internal_secret:
            uid_int = int(hdr_uid) if hdr_uid and hdr_uid.isdigit() else None
            oid_int = int(hdr_oid) if hdr_oid and hdr_oid.isdigit() else None
            if verify_internal_service_token(hdr_internal, internal_secret, uid_int, oid_int, hdr_role):
                if uid_int is not None and oid_int is not None and hdr_role:
                    return RequestContext(
                        user_id=uid_int,
                        organization_id=oid_int,
                        role=hdr_role,
                        email=request.headers.get(HEADER_USER_EMAIL),
                        request_id=request_id,
                        is_internal_service=True,
                    )

        # 2. Direct Bearer JWT (for standalone service operation & tests)
        if credentials and credentials.credentials:
            payload = _decode_bearer_jwt(credentials.credentials, jwt_secret, jwt_algorithm)
            if payload and payload.get("sub") and payload.get("organization_id"):
                try:
                    return RequestContext(
                        user_id=int(payload["sub"]),
                        organization_id=int(payload["organization_id"]),
                        role=str(payload.get("role") or "MEMBER"),
                        email=payload.get("email"),
                        request_id=request_id,
                    )
                except (TypeError, ValueError):
                    pass

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
        )

    return dependency


def require_admin_role(ctx: RequestContext) -> RequestContext:
    if ctx.role.upper() not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative permission required.",
        )
    return ctx
