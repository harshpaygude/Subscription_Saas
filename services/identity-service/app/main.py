"""FastAPI entrypoint for Identity & Organization microservice."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from unisora_kit import (
    CorrelationIdMiddleware,
    configure_logging,
    create_health_router,
    register_exception_handlers,
)
from app.api.auth_routes import router as auth_router
from app.api.department_routes import router as department_router
from app.api.employee_routes import router as employee_router
from app.api.internal_routes import router as internal_router
from app.api.organization_routes import router as organization_router
from app.config import settings
from app.infrastructure.db import check_db_ready, init_db

configure_logging(settings.service_name, settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UniSora Identity & Organization Service",
    version=settings.service_version,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
register_exception_handlers(app)

app.include_router(create_health_router(settings.service_name, settings.service_version, check_db_ready))
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(department_router)
app.include_router(employee_router)
app.include_router(internal_router)
