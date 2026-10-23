from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.aws.client import (
    AWSIntegrationError,
    get_aws_identity,
    get_month_to_date_cost,
    get_account_plan_state,
    encrypt_credentials,
    decrypt_credentials,
    verify_aws_connection,
)
from app.integrations.aws.schemas import (
    AWSConnectResponse,
    AWSConnectRequest,
    AWSConnectionResponse,
    AWSCostResponse,
    AWSAccountPlanResponse,
    AWSVerificationResponse,
)

router = APIRouter(prefix="/integrations/aws", tags=["AWS Integration"])


def _aws_http_exception(exc: AWSIntegrationError) -> HTTPException:
    status_by_category = {
        "configuration": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "region": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "authentication": status.HTTP_401_UNAUTHORIZED,
        "authorization": status.HTTP_403_FORBIDDEN,
        "network": status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    return HTTPException(
        status_code=status_by_category.get(exc.category, status.HTTP_502_BAD_GATEWAY),
        detail=str(exc),
    )


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
    current_user: User = Depends(get_current_user),
):
    """Register an AWS account using credentials supplied by the signed-in user."""
    credentials = credentials_data.credentials()
    try:
        verification = verify_aws_connection(credentials, credentials_data.region)
    except AWSIntegrationError as exc:
        raise _aws_http_exception(exc)

    account_id = verification["account_id"]
    if not account_id:
        raise HTTPException(status_code=502, detail="AWS did not return an account ID.")

    connection = (
        db.query(Connection)
        .filter(
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
            Connection.provider_tenant_id == account_id,
        )
        .first()
    )

    if connection is None:
        connection = Connection(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            provider="AWS",
            provider_tenant_id=account_id,
            access_token=None,
            refresh_token=None,
            credentials_encrypted=encrypt_credentials(credentials),
            scopes=f"region={credentials_data.region};auth=account-credentials",
            status="ACTIVE",
        )
        db.add(connection)
    else:
        connection.status = "ACTIVE"
        connection.credentials_encrypted = encrypt_credentials(credentials)
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
    current_user: User = Depends(get_current_user),
):
    """Verify supplied credentials without persisting them or changing AWS resources."""
    del current_user  # Authentication is required; verification is not user-specific.
    try:
        verification = verify_aws_connection(
            credentials_data.credentials(), credentials_data.region
        )
    except AWSIntegrationError as exc:
        raise _aws_http_exception(exc)

    return AWSVerificationResponse(
        **verification,
        status="VERIFIED" if verification["cost_access"] else "IDENTITY_VERIFIED",
        message=(
            "AWS identity and Cost Explorer access verified."
            if verification["cost_access"]
            else "AWS identity verified, but Cost Explorer access is unavailable."
        ),
    )


@router.get("/connections", response_model=List[AWSConnectionResponse])
def list_aws_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connections = (
        db.query(Connection)
        .filter(
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
        )
        .order_by(Connection.created_at.desc())
        .all()
    )
    return [_response(connection) for connection in connections]


@router.delete("/connections/{connection_id}")
def disconnect_aws(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
        )
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="AWS connection not found.")
    db.delete(connection)
    db.commit()
    return {"message": "AWS connection removed from UniSora."}


@router.get("/connections/{connection_id}/costs", response_model=AWSCostResponse)
def aws_month_to_date_costs(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
        )
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="AWS connection not found.")

    try:
        if not connection.credentials_encrypted:
            raise HTTPException(status_code=409, detail="Reconnect this AWS account with account credentials before loading costs.")
        credentials = decrypt_credentials(connection.credentials_encrypted)
        identity = get_aws_identity(credentials, _response(connection).region)
        if identity.get("Account") != connection.provider_tenant_id:
            raise HTTPException(
                status_code=409,
                detail="The supplied AWS credentials identify a different account. Reconnect the intended AWS account before retrieving costs.",
            )
        costs = get_month_to_date_cost(credentials, _response(connection).region)
    except AWSIntegrationError as exc:
        raise _aws_http_exception(exc)

    return AWSCostResponse(
        account_id=connection.provider_tenant_id,
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
    current_user: User = Depends(get_current_user),
):
    """Return the AWS Free Tier plan status and remaining credits for this connection."""
    connection = (
        db.query(Connection)
        .filter(
            Connection.id == connection_id,
            Connection.user_id == current_user.id,
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
        )
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="AWS connection not found.")

    try:
        if not connection.credentials_encrypted:
            raise HTTPException(status_code=409, detail="Reconnect this AWS account with account credentials before loading account plan details.")
        credentials = decrypt_credentials(connection.credentials_encrypted)
        identity = get_aws_identity(credentials, _response(connection).region)
        if identity.get("Account") != connection.provider_tenant_id:
            raise HTTPException(
                status_code=409,
                detail="The supplied AWS credentials identify a different account. Reconnect the intended AWS account before retrieving account plan details.",
            )
        plan = get_account_plan_state(credentials, _response(connection).region)
    except AWSIntegrationError as exc:
        raise _aws_http_exception(exc)

    if plan.get("account_id") and plan["account_id"] != connection.provider_tenant_id:
        raise HTTPException(status_code=409, detail="AWS returned account plan details for a different account.")
    return AWSAccountPlanResponse(**plan)
