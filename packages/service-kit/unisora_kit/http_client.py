"""Resilient service-to-service HTTP client propagating correlation IDs and auth context."""
from __future__ import annotations

from typing import Any, Optional

import httpx

from unisora_kit.logging import get_correlation_id
from unisora_kit.security import (
    HEADER_INTERNAL_TOKEN,
    HEADER_ORG_ID,
    HEADER_USER_EMAIL,
    HEADER_USER_ID,
    HEADER_USER_ROLE,
    RequestContext,
    create_internal_service_token,
)


class ServiceClientError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class ServiceHttpClient:
    """Thin HTTP client for synchronous REST communication between microservices."""

    def __init__(
        self,
        *,
        base_url: str,
        caller_service: str,
        internal_secret: str,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.caller_service = caller_service
        self.internal_secret = internal_secret
        self.timeout = timeout

    def _headers(self, ctx: Optional[RequestContext] = None) -> dict[str, str]:
        uid = ctx.user_id if ctx else None
        oid = ctx.organization_id if ctx else None
        role = ctx.role if ctx else None
        headers = {
            "X-Request-ID": (ctx.request_id if ctx and ctx.request_id else get_correlation_id()) or "",
            HEADER_INTERNAL_TOKEN: create_internal_service_token(
                self.internal_secret,
                self.caller_service,
                user_id=uid,
                organization_id=oid,
                role=role,
            ),
        }
        if ctx:
            headers[HEADER_USER_ID] = str(ctx.user_id)
            headers[HEADER_ORG_ID] = str(ctx.organization_id)
            headers[HEADER_USER_ROLE] = ctx.role
            if ctx.email:
                headers[HEADER_USER_EMAIL] = ctx.email
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        ctx: Optional[RequestContext] = None,
        json_body: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = httpx.request(
                method,
                url,
                headers=self._headers(ctx),
                json=json_body,
                params=params,
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ServiceClientError(f"Service request to {self.base_url} failed: {exc}", status_code=503) from exc

        if resp.status_code >= 400:
            detail = "Downstream service error"
            try:
                body = resp.json()
                detail = str(body.get("detail") or detail)
            except Exception:
                pass
            raise ServiceClientError(detail, status_code=resp.status_code)

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()
