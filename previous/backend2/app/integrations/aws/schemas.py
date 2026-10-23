from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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


class AWSCostResponse(BaseModel):
    account_id: str
    currency: str
    amount: str
    period_start: str
    period_end_exclusive: str
    granularity: str
