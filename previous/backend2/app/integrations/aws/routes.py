from typing import List

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.models import Connection, User
from app.database.session import get_db
from app.integrations.aws.client import (
    AWSIntegrationError,
    check_cost_access,
    get_aws_identity,
    get_month_to_date_cost,
)
from app.integrations.aws.schemas import (
    AWSConnectResponse,
    AWSConnectionResponse,
    AWSCostResponse,
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register the AWS identity configured for this local backend via AWS CLI/Boto3."""
    try:
        identity = get_aws_identity()
    except AWSIntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    account_id = identity.get("Account")
    if not account_id:
        raise HTTPException(status_code=502, detail="AWS did not return an account ID.")

    connection = (
        db.query(Connection)
        .filter(
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
            Connection.provider_tenant_id == account_id,
        )
        .first()
    )

    if connection is None:
        connection = Connection(
            organization_id=current_user.organization_id,
            provider="AWS",
            provider_tenant_id=account_id,
            access_token=None,
            refresh_token=None,
            scopes="region=us-east-1;auth=aws-cli-default-chain",
            status="ACTIVE",
        )
        db.add(connection)
    else:
        connection.status = "ACTIVE"
        connection.scopes = "region=us-east-1;auth=aws-cli-default-chain"

    db.commit()
    db.refresh(connection)
    cost_access = check_cost_access()
    message = "AWS account connected successfully."
    if not cost_access:
        message += " Identity verification passed, but Cost Explorer access is unavailable; review IAM permissions and Cost Explorer setup."

    return AWSConnectResponse(
        connection=_response(connection),
        identity_arn=identity.get("Arn", ""),
        cost_access=cost_access,
        message=message,
    )


@router.get("/connections", response_model=List[AWSConnectionResponse])
def list_aws_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connections = (
        db.query(Connection)
        .filter(
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
            Connection.organization_id == current_user.organization_id,
            Connection.provider == "AWS",
        )
        .first()
    )
    if connection is None:
        raise HTTPException(status_code=404, detail="AWS connection not found.")

    try:
        identity = get_aws_identity()
        if identity.get("Account") != connection.provider_tenant_id:
            raise HTTPException(
                status_code=409,
                detail="The AWS CLI identity changed. Reconnect the intended AWS account before retrieving costs.",
            )
        costs = get_month_to_date_cost()
    except AWSIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return AWSCostResponse(
        account_id=connection.provider_tenant_id,
        currency=costs["currency"],
        amount=costs["amount"],
        period_start=costs["period_start"],
        period_end_exclusive=costs["period_end_exclusive"],
        granularity="MONTHLY",
    )
