from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

from app.organizations.routes import (
    router as organization_router,
)

from app.auth.routes import (
    router as auth_router,
)
from app.integrations.aws.routes import router as aws_router


app = FastAPI(
    title=settings.app_name,
    description="Enterprise SaaS subscription, license and spend management platform",
    version=settings.app_version,
)


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ROUTERS
# =========================

app.include_router(
    organization_router
)

app.include_router(
    auth_router
)

app.include_router(aws_router)


# =========================
# ROOT
# =========================

@app.get("/")
async def root():
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


# =========================
# HEALTH
# =========================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
