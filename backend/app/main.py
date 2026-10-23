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
from app.integrations.openai.routes import router as openai_router
from app.integrations.gemini.routes import router as gemini_router
from app.integrations.azure.routes import router as azure_router
from app.integrations.anthropic.routes import router as anthropic_router
from app.subscriptions.routes import router as subscription_router
from app.analytics.routes import router as analytics_router
from app.alerts.routes import router as alerts_router
from app.database.init_db import init_db


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
    allow_origins=list(dict.fromkeys([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        settings.frontend_url,
    ])),
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
app.include_router(openai_router)
app.include_router(gemini_router)
app.include_router(azure_router)
app.include_router(anthropic_router)
app.include_router(subscription_router)
app.include_router(analytics_router)
app.include_router(alerts_router)


@app.on_event("startup")
def startup():
    init_db()


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
