"""Public HTTP routes for Subscriptions and License Assignments."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from unisora_kit import OutboxDispatcher, RequestContext, ServiceHttpClient, require_admin_role
from app.api.deps import (
    commit_with_outbox,
    get_current_context,
    get_license_service,
    get_outbox_dispatcher,
    get_subscription_service,
)
from app.api.schemas import (
    LicenseCreate,
    LicenseResponse,
    ManualSpendCreate,
    ManualSpendResponse,
    SubscriptionAssignmentCreate,
    SubscriptionAssignmentResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.application.license_service import LicenseAssignmentService
from app.application.subscription_bulk_import import (
    generate_subscription_template_bytes,
    process_subscription_bulk_import,
)
from app.application.subscription_service import SubscriptionService
from app.config import settings
from app.infrastructure.adapters import OutboxAuditAdapter
from app.infrastructure.db import get_db
from app.infrastructure.repositories import SqlAlchemyLicenseRepository, SqlAlchemySubscriptionRepository

subscriptions_router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
licenses_router = APIRouter(tags=["License assignments"])


@subscriptions_router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    item = service.create_subscription(
        organization_id=ctx.organization_id, user_id=ctx.user_id, data=payload.model_dump()
    )
    commit_with_outbox(db)
    return item


@subscriptions_router.post("/import-csv")
@subscriptions_router.post("/import")
async def import_subscriptions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    dispatcher: OutboxDispatcher = Depends(get_outbox_dispatcher),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        result = process_subscription_bulk_import(
            organization_id=ctx.organization_id,
            actor_id=ctx.user_id,
            subscriptions=SqlAlchemySubscriptionRepository(db),
            licenses=SqlAlchemyLicenseRepository(db),
            audit=OutboxAuditAdapter(db, dispatcher),
            file_bytes=content,
            filename=file.filename or "subscriptions.csv",
        )
        commit_with_outbox(db)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import error: {exc}") from exc


@subscriptions_router.get("/sample-template")
def get_subscription_template(
    format: str = Query("xlsx", pattern="^(xlsx|csv)$"),
    ctx: RequestContext = Depends(get_current_context),
):
    del ctx
    content, media_type, filename = generate_subscription_template_bytes(fmt=format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@subscriptions_router.post("/seed-demo")
def seed_demo_data(
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    dispatcher: OutboxDispatcher = Depends(get_outbox_dispatcher),
):
    content, _, _ = generate_subscription_template_bytes(fmt="xlsx")
    result = process_subscription_bulk_import(
        organization_id=ctx.organization_id,
        actor_id=ctx.user_id,
        subscriptions=SqlAlchemySubscriptionRepository(db),
        licenses=SqlAlchemyLicenseRepository(db),
        audit=OutboxAuditAdapter(db, dispatcher),
        file_bytes=content,
        filename="UniSora_Demo_Subscriptions.xlsx",
    )
    # Seed demo integration connections via Integration Service HTTP contract (best-effort)
    sample_connections = [
        {"provider_id": "aws", "account_or_tenant_id": "arn:aws:iam::123456789012:root", "notes": "region=us-east-1"},
        {"provider_id": "openai", "account_or_tenant_id": "org-unisora-production-ai"},
        {"provider_id": "anthropic", "account_or_tenant_id": "ant-org-unisora-demo"},
        {"provider_id": "gemini", "account_or_tenant_id": "projects/unisora-demo-studio"},
        {"provider_id": "azure", "account_or_tenant_id": "unisora-cloud.onmicrosoft.com"},
        {"provider_id": "github", "account_or_tenant_id": "unisora-org", "notes": '{"plan": "enterprise", "seats": 50, "verified": true}'},
        {"provider_id": "slack", "account_or_tenant_id": "T07A19B2Z", "notes": '{"team_name": "UniSora HQ", "users_count": 60, "verified": true}'},
        {"provider_id": "stripe", "account_or_tenant_id": "acct_1NZs9k2eZvKYlo2C", "notes": '{"currency": "USD", "balance": 18450.00, "verified": true}'},
    ]
    try:
        ServiceHttpClient(
            base_url=settings.integration_service_url,
            caller_service=settings.service_name,
            internal_secret=settings.internal_service_secret,
        ).request("POST", "/internal/integrations/seed-connections", ctx=ctx, json_body={"connections": sample_connections})
    except Exception:
        pass

    commit_with_outbox(db)
    return {
        "message": f"Demo dataset loaded successfully: {result.get('imported', 0)} SaaS subscriptions seeded.",
        **result,
    }


@subscriptions_router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    provider: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    billing_interval: Optional[str] = None,
    renewal_before: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return service.list_subscriptions(
        ctx.organization_id,
        provider=provider,
        status=status_filter,
        billing_interval=billing_interval,
        renewal_before=renewal_before,
        page=page,
        page_size=page_size,
    )


@subscriptions_router.get("/summary")
def subscription_summary(
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return service.summary(ctx.organization_id)


@subscriptions_router.get("/renewals", response_model=list[SubscriptionResponse])
def upcoming_renewals(
    days: int = Query(30, ge=1, le=366),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return service.upcoming_renewals(ctx.organization_id, days)


@subscriptions_router.get("/spend")
def monthly_spend(
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return service.monthly_spend(ctx.organization_id)


@subscriptions_router.post("/manual-spend", response_model=ManualSpendResponse, status_code=status.HTTP_201_CREATED)
def create_manual_spend(
    payload: ManualSpendCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    item = service.upsert_manual_spend(
        organization_id=ctx.organization_id, user_id=ctx.user_id, data=payload.model_dump()
    )
    commit_with_outbox(db)
    return item


@subscriptions_router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return service.get_subscription(ctx.organization_id, subscription_id)


@subscriptions_router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    item = service.update_subscription(
        organization_id=ctx.organization_id,
        subscription_id=subscription_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    commit_with_outbox(db)
    return item


@subscriptions_router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    item = service.cancel_subscription(
        organization_id=ctx.organization_id, actor_id=ctx.user_id, subscription_id=subscription_id
    )
    commit_with_outbox(db)
    return item


@subscriptions_router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: SubscriptionService = Depends(get_subscription_service),
):
    service.delete_subscription(
        organization_id=ctx.organization_id, actor_id=ctx.user_id, subscription_id=subscription_id
    )
    commit_with_outbox(db)
    return None


@licenses_router.post("/subscriptions/{subscription_id}/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
def create_license(
    subscription_id: int,
    payload: LicenseCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LicenseAssignmentService = Depends(get_license_service),
):
    require_admin_role(ctx)
    item = service.create_license(
        organization_id=ctx.organization_id,
        subscription_id=subscription_id,
        reference=payload.reference,
        capacity=payload.capacity,
    )
    commit_with_outbox(db)
    return item


@licenses_router.get("/subscriptions/{subscription_id}/licenses", response_model=list[LicenseResponse])
def list_licenses(
    subscription_id: int,
    ctx: RequestContext = Depends(get_current_context),
    service: LicenseAssignmentService = Depends(get_license_service),
):
    return service.list_licenses(organization_id=ctx.organization_id, subscription_id=subscription_id)


@licenses_router.post("/subscription-assignments", response_model=SubscriptionAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: SubscriptionAssignmentCreate,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LicenseAssignmentService = Depends(get_license_service),
):
    require_admin_role(ctx)
    assignment = service.assign_license(
        ctx=ctx,
        subscription_id=payload.subscription_id,
        license_id=payload.license_id,
        user_id=payload.user_id,
        notes=payload.notes,
    )
    commit_with_outbox(db)
    return assignment


@licenses_router.get("/subscription-assignments", response_model=list[SubscriptionAssignmentResponse])
def list_assignments(
    subscription_id: int | None = None,
    user_id: int | None = None,
    ctx: RequestContext = Depends(get_current_context),
    service: LicenseAssignmentService = Depends(get_license_service),
):
    return service.list_assignments(
        organization_id=ctx.organization_id, subscription_id=subscription_id, user_id=user_id
    )


@licenses_router.post("/subscription-assignments/{assignment_id}/release", response_model=SubscriptionAssignmentResponse)
def release_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
    service: LicenseAssignmentService = Depends(get_license_service),
):
    require_admin_role(ctx)
    item = service.release_license(ctx=ctx, assignment_id=assignment_id)
    commit_with_outbox(db)
    return item
