"""Pydantic API contracts for Integration Service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


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
    model_config = ConfigDict(from_attributes=True)
    id: int
    provider: str
    account_id: Optional[str] = None
    status: str
    region: str = "us-east-1"
    created_at: datetime
    updated_at: datetime


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


class OpenAIConnectRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1)
    def secret_value(self) -> str:
        return self.api_key.get_secret_value()


class OpenAIConnectionResponse(BaseModel):
    id: int
    provider: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None


class OpenAIConnectResponse(BaseModel):
    connection: OpenAIConnectionResponse
    model_count: int
    message: str


class OpenAITestResponse(BaseModel):
    connection_id: int
    status: str
    model_count: int
    last_verified_at: datetime
    message: str


class OpenAIUsageDay(BaseModel):
    start_time: int
    end_time: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    requests: Optional[int] = None


class OpenAIModelUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    requests: Optional[int] = None


class OpenAIUsageResponse(BaseModel):
    start_time: int
    end_time: int
    daily: List[OpenAIUsageDay]
    by_model: List[OpenAIModelUsage]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    requests: Optional[int] = None
    synced_at: datetime


class OpenAICostDay(BaseModel):
    start_time: int
    end_time: int
    amount: float
    currency: str


class OpenAIProjectCost(BaseModel):
    project_id: str
    amount: float
    currency: str


class OpenAICostResponse(BaseModel):
    start_time: int
    end_time: int
    daily: List[OpenAICostDay]
    by_project: List[OpenAIProjectCost]
    total: float
    currency: str
    synced_at: datetime


class OpenAISummaryResponse(BaseModel):
    usage: OpenAIUsageResponse
    costs: Optional[OpenAICostResponse] = None
    costs_error: Optional[str] = None


class GeminiConnectRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1)
    def secret_value(self) -> str:
        return self.api_key.get_secret_value()


class GeminiConnectionResponse(BaseModel):
    id: int
    provider: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None


class GeminiConnectResponse(BaseModel):
    connection: GeminiConnectionResponse
    model_count: int
    message: str


class GeminiTestResponse(BaseModel):
    connection_id: int
    status: str
    model_count: int
    last_verified_at: datetime
    message: str


class GeminiGenerateRequest(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    contents: list[dict[str, Any]] = Field(min_length=1)
    generation_config: Optional[dict[str, Any]] = None


class GeminiUsageResponse(BaseModel):
    start_date: str
    end_date: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    by_model: list[dict[str, Any]]
    daily: list[dict[str, Any]]


class AnthropicConnectRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1)
    model: str = Field(min_length=1, max_length=255)
    connection_name: Optional[str] = Field(default=None, max_length=255)
    tier: Optional[str] = Field(default="ENTERPRISE", max_length=50)
    def secret_value(self) -> str:
        return self.api_key.get_secret_value()


class AnthropicUpdateRequest(BaseModel):
    api_key: Optional[SecretStr] = None
    model: Optional[str] = None
    connection_name: Optional[str] = None
    tier: Optional[str] = None
    def secret_value(self) -> Optional[str]:
        return self.api_key.get_secret_value() if self.api_key else None


class AnthropicConnectionResponse(BaseModel):
    id: int
    provider: str
    status: str
    model: str
    connection_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    admin_access_status: str = "VERIFIED"
    admin_verified_at: Optional[datetime] = None
    last_reporting_sync_at: Optional[datetime] = None
    manual_balance_amount: Optional[str] = None
    manual_balance_currency: Optional[str] = None
    manual_balance_entered_at: Optional[datetime] = None


class AnthropicConnectResponse(BaseModel):
    connection: AnthropicConnectionResponse
    message: str


class AnthropicTestResponse(BaseModel):
    connection_id: int
    status: str
    model: str
    last_verified_at: datetime
    message: str


class AnthropicAdminCredentialRequest(BaseModel):
    admin_api_key: SecretStr = Field(min_length=1)
    def secret_value(self) -> str:
        return self.admin_api_key.get_secret_value()


class AnthropicAdminCredentialResponse(BaseModel):
    connection_id: int
    admin_access_status: str
    admin_verified_at: datetime
    message: str


class AnthropicManualBalanceRequest(BaseModel):
    amount: str = Field(min_length=1, max_length=80)
    currency: str = Field(min_length=3, max_length=3)


class AnthropicReportResponse(BaseModel):
    connection_id: int
    admin_access_status: str
    usage_status: str
    cost_status: str
    start_date: str
    end_date: str
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    data_refreshed_at: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    balance: dict[str, Any]


class AnthropicBalanceResponse(BaseModel):
    connection_id: int
    balance: dict[str, Any]


class ProviderConnectRequest(BaseModel):
    model_config = {"extra": "allow"}
    api_key: Optional[str] = None
    token: Optional[str] = None
    bot_token: Optional[str] = None
    access_token: Optional[str] = None
    secret_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    domain: Optional[str] = None
    admin_email: Optional[str] = None
    extra_fields: Optional[Dict[str, Any]] = None


class ProviderConnectionResponse(BaseModel):
    id: int
    provider: str
    provider_tenant_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    profile_data: Optional[Dict[str, Any]] = None


class ProviderConnectResponse(BaseModel):
    connection: ProviderConnectionResponse
    profile_data: Dict[str, Any]
    message: str


class ProviderTestResponse(BaseModel):
    connection_id: int
    provider: str
    status: str
    last_verified_at: datetime
    message: str
    profile_data: Optional[Dict[str, Any]] = None


class ProviderDetailsResponse(BaseModel):
    connection_id: int
    provider: str
    provider_tenant_id: Optional[str] = None
    status: str
    created_at: datetime
    last_verified_at: Optional[datetime] = None
    profile_data: Dict[str, Any]
