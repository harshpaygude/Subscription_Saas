from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, SecretStr


class AnthropicConnectRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1)
    model: str = Field(min_length=1, max_length=255)
    connection_name: Optional[str] = Field(default=None, max_length=255)

    def secret_value(self) -> str:
        return self.api_key.get_secret_value()


class AnthropicConnectionResponse(BaseModel):
    id: int
    provider: str
    status: str
    model: str
    connection_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    admin_access_status: str = "NOT_CONFIGURED"
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
