
"""Organization-scoped AWS connection and account-data routes."""

import secrets
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.config import settings
from app.integrations.services import ConnectionService
from app.integrations.aws.identity import AWSBackendIdentity, AWSIdentityError
from app.integrations.aws.client import (
    AWSIntegrationError,
    assume_connection_role,
    check_cost_access,
    get_month_to_date_cost,
    get_account_plan_state,
)
from app.integrations.aws.schemas import (
    AWSConnectionSetupRequest,
    AWSConnectionSetupResponse,
    AWSConnectionVerifyRequest,
    AWSConnectionVerifyResponse,
    AWSConnectionResponse,
    AWSCostResponse,
    AWSAccountPlanResponse,
)

router = APIRouter(
    prefix="/integrations/aws",
    tags=["AWS Integration"],
)

AWS_PROVIDER = "AWS"
AWS_REGION = settings.aws_region


def _response(connection: Connection) -> AWSConnectionResponse:
    """Convert a database connection to its safe API representation."""
    region = AWS_REGION

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


def _get_connection(
    db: Session,
    connection_id: int,
    current_user: User,
) -> Connection:
    """Return a connection only if it belongs to the user's organization."""
    return ConnectionService(db).get_for_organization(
        connection_id, current_user, provider=AWS_PROVIDER
    )


def _require_active_connection(connection: Connection) -> None:
    if connection.status != "ACTIVE" or not connection.aws_role_arn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This AWS connection has not been verified.",
        )

    if not connection.aws_external_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This AWS connection is missing its external ID.",
        )


def _assume_connection(connection: Connection) -> Dict[str, Any]:
    """Create a verified temporary AWS session for one connection."""
    _require_active_connection(connection)

    try:
        result = assume_connection_role(
            role_arn=connection.aws_role_arn,
            external_id=connection.aws_external_id,
            expected_account_id=connection.provider_tenant_id,
            session_name="UniSoraConnection{}".format(connection.id),
        )
    except AWSIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return result


@router.post(
    "/connections/setup",
    response_model=AWSConnectionSetupResponse,
    status_code=status.HTTP_201_CREATED,
)
def setup_aws_connection(
    payload: AWSConnectionSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a pending connection and generate the customer IAM trust policy.

    No AWS customer account is accessed or activated by this endpoint.
    """
    try:
        principal_arn = AWSBackendIdentity().principal_arn()
    except AWSIdentityError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    # The ID is unique to this connection, not shared across customers.
    # Keep generation server-side and guard the database uniqueness boundary
    # as well as the cryptographic randomness boundary.
    external_id = secrets.token_urlsafe(32)
    while db.query(Connection.id).filter(Connection.aws_external_id == external_id).first():
        external_id = secrets.token_urlsafe(32)

    connection = Connection(
        organization_id=current_user.organization_id,
        provider=AWS_PROVIDER,
        provider_tenant_id=payload.account_id,
        aws_role_arn=None,
        aws_external_id=external_id,
        access_token=None,
        refresh_token=None,
        scopes="region={}".format(AWS_REGION),
        status="PENDING",
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": principal_arn,
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "sts:ExternalId": external_id,
                    },
                },
            },
        ],
    }

    return AWSConnectionSetupResponse(
        connection_id=connection.id,
        account_id=payload.account_id,
        external_id=external_id,
        trusted_principal_arn=principal_arn,
        trust_policy=trust_policy,
        next_step=(
            "Create a read-only IAM role in the specified AWS account, "
            "configure its trust policy using these instructions, and "
            "submit the resulting role ARN for verification."
        ),
    )


@router.post(
    "/connections/{connection_id}/verify",
    response_model=AWSConnectionVerifyResponse,
)
def verify_aws_connection(
    connection_id: int,
    payload: AWSConnectionVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify the configured customer role before activating the connection."""
    connection = _get_connection(db, connection_id, current_user)

    if connection.status == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This connection is already active. Disconnect it before "
                "creating a replacement connection."
            ),
        )

    expected_account_id = connection.provider_tenant_id
    role_account_id = payload.role_arn.split(":")[4]

    if role_account_id != expected_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The role ARN belongs to a different AWS account than "
                "the account selected during setup."
            ),
        )

    if not connection.aws_external_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The pending connection has no external ID. Start setup again.",
        )

    try:
        result = assume_connection_role(
            role_arn=payload.role_arn,
            external_id=connection.aws_external_id,
            expected_account_id=expected_account_id,
            session_name="UniSoraConnection{}".format(connection.id),
        )
    except AWSIntegrationError as exc:
        # Leave the connection pending so the user can correct their setup.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Only save the role and activate after STS verification succeeds.
    connection.aws_role_arn = payload.role_arn
    connection.status = "ACTIVE"
    connection.scopes = "region={}".format(AWS_REGION)

    db.commit()
    db.refresh(connection)

    cost_access = check_cost_access(result["session"])

    message = "AWS role verified and account connected successfully."

    if not cost_access:
        message += (
            " Cost Explorer access is unavailable. Review the connected "
            "role's billing permissions and Cost Explorer setup."
        )

    return AWSConnectionVerifyResponse(
        connection=_response(connection),
        identity_arn=result["identity"].get("Arn", ""),
        cost_access=cost_access,
        message=message,
    )


@router.get(
    "/connections",
    response_model=List[AWSConnectionResponse],
)
def list_aws_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List only AWS connections belonging to the current organization."""
    connections = (
        ConnectionService(db).list_for_organization(current_user, provider=AWS_PROVIDER)
    )

    return [_response(connection) for connection in connections]


@router.delete("/connections/{connection_id}")
def disconnect_aws(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an AWS connection owned by the current organization."""
    connection = _get_connection(db, connection_id, current_user)

    ConnectionService(db).disconnect(connection)

    return {"message": "AWS connection removed from UniSora."}


@router.get(
    "/connections/{connection_id}/costs",
    response_model=AWSCostResponse,
)
def aws_month_to_date_costs(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve costs through this connection's verified AWS role."""
    connection = _get_connection(db, connection_id, current_user)
    result = _assume_connection(connection)

    try:
        costs = get_month_to_date_cost(result["session"])
    except AWSIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    return AWSCostResponse(
        account_id=connection.provider_tenant_id,
        currency=costs["currency"],
        amount=costs["amount"],
        period_start=costs["period_start"],
        period_end_exclusive=costs["period_end_exclusive"],
        granularity="MONTHLY",
    )


@router.get(
    "/connections/{connection_id}/account-plan",
    response_model=AWSAccountPlanResponse,
)
def aws_account_plan(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Free Tier information through this connection's AWS role."""
    connection = _get_connection(db, connection_id, current_user)
    result = _assume_connection(connection)

    try:
        plan = get_account_plan_state(result["session"])
    except AWSIntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    if (
        plan.get("account_id")
        and plan["account_id"] != connection.provider_tenant_id
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AWS returned account-plan details for a different account.",
        )

    return AWSAccountPlanResponse(**plan)

