from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, SecretStr


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
