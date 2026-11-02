from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, SecretStr, field_validator


class AWSConnectRequest(BaseModel):
    access_key_id: SecretStr = Field(min_length=1)
    secret_access_key: SecretStr = Field(min_length=1)
    session_token: Optional[SecretStr] = None
    region: str = Field(default="us-east-1", min_length=1, max_length=64)

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: str) -> str:
        return value.strip().lower()

    def credentials(self) -> dict[str, str]:
        values = {
            "access_key_id": self.access_key_id.get_secret_value().strip(),
            "secret_access_key": self.secret_access_key.get_secret_value(),
        }
        if self.session_token is not None:
            values["session_token"] = self.session_token.get_secret_value()
        return values


class AWSVerificationResponse(BaseModel):
    account_id: str
    identity_arn: str
    region: str
    cost_access: bool
    status: str
    message: str


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


class AWSAccountPlanResponse(BaseModel):
    account_id: str
    plan_type: str
    plan_status: str
    credits_remaining: Optional[float] = None
    currency: str = "USD"
    expiration_date: Optional[str] = None
    days_remaining: Optional[int] = None
    original_amount: Optional[float] = None
    retrieved_at: datetime
    data_status: str = "AVAILABLE"
