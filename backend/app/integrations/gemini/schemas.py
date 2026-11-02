from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, SecretStr

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
