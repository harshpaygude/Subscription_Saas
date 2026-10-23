from datetime import datetime
from typing import Optional

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


class AnthropicConnectResponse(BaseModel):
    connection: AnthropicConnectionResponse
    message: str


class AnthropicTestResponse(BaseModel):
    connection_id: int
    status: str
    model: str
    last_verified_at: datetime
    message: str
