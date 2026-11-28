"""FastAPI entrypoint for External Provider Integration microservice."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from unisora_kit import (
    CorrelationIdMiddleware,
    configure_logging,
    create_health_router,
    register_exception_handlers,
)
from app.api.anthropic_routes import router as anthropic_router
from app.api.aws_routes import router as aws_router
from app.api.azure_routes import router as azure_router
from app.api.gemini_routes import router as gemini_router
from app.api.generic_routes import internal_router, router as generic_router
from app.api.openai_routes import router as openai_router
from app.config import settings
from app.infrastructure.db import check_db_ready, init_db

configure_logging(settings.service_name, settings.log_level)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UniSora Provider Integration Service",
    version=settings.service_version,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware, service_name=settings.service_name)
register_exception_handlers(app)

app.include_router(create_health_router(settings.service_name, settings.service_version, check_db_ready))
app.include_router(aws_router)
app.include_router(openai_router)
app.include_router(gemini_router)
app.include_router(azure_router)
app.include_router(anthropic_router)
app.include_router(generic_router)
app.include_router(internal_router)
