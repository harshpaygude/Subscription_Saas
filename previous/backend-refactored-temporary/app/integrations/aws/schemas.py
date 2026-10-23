
"""Request and response schemas for the AWS integration."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AWSConnectionSetupRequest(BaseModel):
    """Initial setup information for a customer AWS account."""

    account_id: str = Field(
        pattern=r"^\d{12}$",
        description="The 12-digit AWS account ID.",
    )


class AWSConnectionSetupResponse(BaseModel):
    """Instructions for creating the customer-side IAM role."""

    connection_id: int
    account_id: str
    external_id: str
    trusted_principal_arn: str
    trust_policy: dict
    next_step: str


class AWSConnectionVerifyRequest(BaseModel):
    """Role details submitted after the customer creates an IAM role."""

    role_arn: str = Field(
        min_length=1,
        max_length=512,
        pattern=r"^arn:aws(-us-gov|-cn)?:iam::\d{12}:role/.+$",
    )


class AWSConnectionResponse(BaseModel):
    id: int
    provider: str
    account_id: Optional[str] = None
    status: str
    region: str = "us-east-1"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AWSConnectResponse(BaseModel):
    connection: AWSConnectionResponse
    identity_arn: str
    cost_access: bool
    message: str


class AWSConnectionVerifyResponse(BaseModel):
    connection: AWSConnectionResponse
    identity_arn: str
    cost_access: bool
    message: str


class AWSCostResponse(BaseModel):
    account_id: str
    currency: str
    amount: str
    period_start: str
    period_end_exclusive: str
    granularity: str


class AWSAccountPlanResponse(BaseModel):
    account_id: str
    plan_type: str
    plan_status: str
    credits_remaining: Optional[float] = None
    currency: str = "USD"
    expiration_date: Optional[str] = None
    days_remaining: Optional[int] = None










