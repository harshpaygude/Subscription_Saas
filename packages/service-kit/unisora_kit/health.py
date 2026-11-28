"""Standard liveness and readiness endpoints for microservices."""
from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse


def create_health_router(
    service_name: str,
    version: str = "1.0.0",
    readiness_check: Callable[[], bool] | None = None,
) -> APIRouter:
    router = APIRouter(tags=["Health"])

    @router.get("/health")
    async def health():
        return {"status": "healthy", "service": service_name, "version": version}

    @router.get("/ready")
    async def ready():
        ok = True
        if readiness_check is not None:
            try:
                ok = bool(readiness_check())
            except Exception:
                ok = False
        if not ok:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "service": service_name},
            )
        return {"status": "ready", "service": service_name, "version": version}

    return router
