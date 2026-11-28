"""FastAPI API Gateway application: routing, edge JWT validation, rate limiting, and proxy."""
from __future__ import annotations

from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt

from unisora_kit import (
    CorrelationIdMiddleware,
    configure_logging,
    create_internal_service_token,
    get_correlation_id,
    register_exception_handlers,
)
from app.config import settings
from app.rate_limit import SlidingWindowRateLimiter
from app.routing import RouteRule, build_route_table, resolve_route

configure_logging(settings.service_name, settings.log_level)

app = FastAPI(
    title="UniSora API Gateway",
    version=settings.service_version,
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(["http://localhost:3000", "http://127.0.0.1:3000", settings.frontend_url])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

_route_table: list[RouteRule] = build_route_table(settings)
_rate_limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute)
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=settings.request_timeout_seconds)
    return _http_client


@app.on_event("shutdown")
async def _shutdown():
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


@app.get("/")
async def root():
    return {
        "message": "Subscription Management SaaS",
        "version": settings.service_version,
        "status": "running",
        "architecture": "microservices-gateway",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.service_name}


@app.get("/ready")
async def ready():
    services = {
        "identity-service": settings.identity_service_url,
        "subscription-service": settings.subscription_service_url,
        "asset-service": settings.asset_service_url,
        "lifecycle-service": settings.lifecycle_service_url,
        "integration-service": settings.integration_service_url,
        "governance-service": settings.governance_service_url,
    }
    statuses: dict[str, str] = {}
    client = get_http_client()
    all_ok = True
    for name, base in services.items():
        try:
            resp = await client.get(f"{base.rstrip('/')}/health", timeout=2.0)
            statuses[name] = "healthy" if resp.status_code == 200 else f"unhealthy ({resp.status_code})"
            if resp.status_code != 200:
                all_ok = False
        except Exception:
            statuses[name] = "unreachable"
            all_ok = False
    code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content={"status": "ready" if all_ok else "degraded", "services": statuses})


def _authenticate_edge(request: Request) -> dict[str, str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user_id = payload.get("sub")
    org_id = payload.get("organization_id")
    role = str(payload.get("role") or "MEMBER")
    if not user_id or not org_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    uid_int = int(user_id)
    oid_int = int(org_id)
    headers = {
        "X-User-Id": str(uid_int),
        "X-Organization-Id": str(oid_int),
        "X-User-Role": role,
        "X-Internal-Service-Token": create_internal_service_token(
            settings.internal_service_secret,
            settings.service_name,
            user_id=uid_int,
            organization_id=oid_int,
            role=role,
        ),
    }
    if payload.get("email"):
        headers["X-User-Email"] = str(payload["email"])
    return headers


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_request(full_path: str, request: Request):
    path = f"/{full_path}"
    if path.startswith("/internal"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal endpoints are not publicly accessible.")

    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(client_ip):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Retry shortly.", "code": "rate_limited"})

    rule = resolve_route(path, _route_table)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    forward_headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in {"host", "content-length", "connection", "x-user-id", "x-organization-id", "x-user-role", "x-internal-service-token"}
    }
    forward_headers["X-Request-ID"] = get_correlation_id() or request.headers.get("X-Request-ID", "")

    if rule.require_auth:
        forward_headers.update(_authenticate_edge(request))

    target_url = f"{rule.target_url.rstrip('/')}{path}"
    body = await request.body()
    client = get_http_client()
    try:
        upstream = await client.request(
            method=request.method,
            url=target_url,
            params=request.query_params,
            headers=forward_headers,
            content=body,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": f"Upstream service '{rule.service_name}' is unavailable.", "code": "upstream_unavailable"},
        )

    excluded = {"content-encoding", "transfer-encoding", "content-length", "connection"}
    resp_headers = [(k, v) for k, v in upstream.headers.multi_items() if k.lower() not in excluded]
    response = Response(content=upstream.content, status_code=upstream.status_code, media_type=upstream.headers.get("content-type"))
    for k, v in resp_headers:
        response.headers.append(k, v)
    return response
