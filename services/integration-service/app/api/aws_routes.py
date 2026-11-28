"""AWS integration routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from unisora_kit import RequestContext
from app.api.deps import get_current_context
from app.api.schemas import (
    AWSAccountPlanResponse,
    AWSConnectRequest,
    AWSConnectResponse,
    AWSConnectionResponse,
    AWSCostResponse,
    AWSVerificationResponse,
)
from app.infrastructure.connection_repo import get_owned_connection, map_provider_error
from app.infrastructure.crypto import CredentialStorageError, decrypt_credentials, encrypt_credentials
from app.infrastructure.db import get_db
from app.infrastructure.models import Connection
from app.infrastructure.providers.aws_client import (
    AWSIntegrationError,
    get_account_plan_state,
    get_aws_identity,
    get_month_to_date_cost,
    verify_aws_connection,
)

router = APIRouter(prefix="/integrations/aws", tags=["AWS Integration"])


def _response(connection: Connection) -> AWSConnectionResponse:
    region = "us-east-1"
    if connection.scopes:
        for item in connection.scopes.split(";"):
            if item.startswith("region="):
                region = item.split("=", 1)[1]
    return AWSConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        account_id=connection.provider_tenant_id,
        status=connection.status,
        region=region,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@router.post("/connections", response_model=AWSConnectResponse, status_code=status.HTTP_201_CREATED)
def connect_aws(
    credentials_data: AWSConnectRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    credentials = credentials_data.credentials()
    try:
        verification = verify_aws_connection(credentials, credentials_data.region)
        encrypted = encrypt_credentials(credentials)
    except AWSIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    account_id = verification["account_id"]
    if not account_id:
        raise HTTPException(status_code=502, detail="AWS did not return an account ID.")

    connection = (
        db.query(Connection)
        .filter(
            Connection.user_id == ctx.user_id,
            Connection.organization_id == ctx.organization_id,
            Connection.provider == "AWS",
            Connection.provider_tenant_id == account_id,
        )
        .first()
    )
    if connection is None:
        connection = Connection(
            user_id=ctx.user_id,
            organization_id=ctx.organization_id,
            provider="AWS",
            provider_tenant_id=account_id,
            credentials_encrypted=encrypted,
            scopes=f"region={credentials_data.region};auth=account-credentials",
            status="ACTIVE",
        )
        db.add(connection)
    else:
        connection.status = "ACTIVE"
        connection.credentials_encrypted = encrypted
        connection.scopes = f"region={credentials_data.region};auth=account-credentials"

    db.commit()
    db.refresh(connection)
    cost_access = verification["cost_access"]
    message = "AWS account connected successfully."
    if not cost_access:
        message += " Identity verification passed, but Cost Explorer access is unavailable; review IAM permissions and Cost Explorer setup."
    return AWSConnectResponse(
        connection=_response(connection),
        identity_arn=verification["identity_arn"],
        cost_access=cost_access,
        message=message,
    )


@router.post("/verify", response_model=AWSVerificationResponse)
def verify_aws(
    credentials_data: AWSConnectRequest,
    ctx: RequestContext = Depends(get_current_context),
):
    del ctx
    try:
        verification = verify_aws_connection(credentials_data.credentials(), credentials_data.region)
    except AWSIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    return AWSVerificationResponse(
        **verification,
        status="VERIFIED" if verification["cost_access"] else "IDENTITY_VERIFIED",
        message="AWS identity and Cost Explorer access verified." if verification["cost_access"] else "AWS identity verified, but Cost Explorer access is unavailable.",
    )


@router.get("/connections", response_model=List[AWSConnectionResponse])
def list_aws_connections(
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    rows = (
        db.query(Connection)
        .filter(Connection.user_id == ctx.user_id, Connection.organization_id == ctx.organization_id, Connection.provider == "AWS")
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(r) for r in rows]


@router.delete("/connections/{connection_id}")
def disconnect_aws(
    connection_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    connection = get_owned_connection(db, ctx, connection_id, provider="AWS", not_found_detail="AWS connection not found.")
    db.delete(connection)
    db.commit()
    return {"message": "AWS connection removed from UniSora."}


@router.get("/connections/{connection_id}/costs", response_model=AWSCostResponse)
def aws_month_to_date_costs(
    connection_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    connection = get_owned_connection(db, ctx, connection_id, provider="AWS", not_found_detail="AWS connection not found.")
    if not connection.credentials_encrypted:
        raise HTTPException(status_code=409, detail="Reconnect this AWS account with account credentials before loading costs.")
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted)
        region = _response(connection).region
        identity = get_aws_identity(credentials, region)
        if identity.get("Account") != connection.provider_tenant_id:
            raise HTTPException(status_code=409, detail="The supplied AWS credentials identify a different account. Reconnect the intended AWS account before retrieving costs.")
        costs = get_month_to_date_cost(credentials, region)
    except AWSIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AWSCostResponse(
        account_id=connection.provider_tenant_id or "",
        currency=costs["currency"],
        amount=costs["amount"],
        period_start=costs["period_start"],
        period_end_exclusive=costs["period_end_exclusive"],
        granularity="MONTHLY",
    )


@router.get("/connections/{connection_id}/account-plan", response_model=AWSAccountPlanResponse)
def aws_account_plan(
    connection_id: int,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_current_context),
):
    connection = get_owned_connection(db, ctx, connection_id, provider="AWS", not_found_detail="AWS connection not found.")
    if not connection.credentials_encrypted:
        raise HTTPException(status_code=409, detail="Reconnect this AWS account with account credentials before loading account plan details.")
    try:
        credentials = decrypt_credentials(connection.credentials_encrypted)
        region = _response(connection).region
        identity = get_aws_identity(credentials, region)
        if identity.get("Account") != connection.provider_tenant_id:
            raise HTTPException(status_code=409, detail="The supplied AWS credentials identify a different account. Reconnect the intended AWS account before retrieving account plan details.")
        plan = get_account_plan_state(credentials, region)
    except AWSIntegrationError as exc:
        raise map_provider_error(exc.category, str(exc)) from exc
    except CredentialStorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if plan.get("account_id") and plan["account_id"] != connection.provider_tenant_id:
        raise HTTPException(status_code=409, detail="AWS returned account plan details for a different account.")
    return AWSAccountPlanResponse(**plan)
