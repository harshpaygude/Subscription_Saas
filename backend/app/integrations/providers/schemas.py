from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


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

    def primary_credential(self) -> str:
        """Returns the main secret/token provided."""
        return (
            (self.token or "").strip()
            or (self.bot_token or "").strip()
            or (self.access_token or "").strip()
            or (self.api_key or "").strip()
            or (self.secret_key or "").strip()
            or (self.client_secret or "").strip()
        )


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
