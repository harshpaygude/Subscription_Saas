"""FastAPI entrypoint for Asset Management microservice."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from unisora_kit import (
    CorrelationIdMiddleware,
    configure_logging,
    create_health_router,
    register_exception_handlers,
)
from app.api.internal_routes import router as internal_router
from app.api.routes import router as asset_router
from app.config import settings
from app.infrastructure.db import check_db_ready, init_db

configure_logging(settings.service_name, settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UniSora IT Asset Management Service",
    version=settings.service_version,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
register_exception_handlers(app)

app.include_router(create_health_router(settings.service_name, settings.service_version, check_db_ready))
app.include_router(asset_router)
app.include_router(internal_router)
