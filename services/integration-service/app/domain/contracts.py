"""Pure domain entities and ports for Integration Service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol


@dataclass
class ConnectionEntity:
    id: Optional[int]
    organization_id: int
    user_id: Optional[int]
    provider: str
    provider_tenant_id: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    credentials_encrypted: Optional[str]
    expires_at: Optional[datetime]
    scopes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    last_verified_at: Optional[datetime] = None
    anthropic_reporting_cache: Optional[str] = None
    anthropic_reporting_synced_at: Optional[datetime] = None
    anthropic_admin_verified_at: Optional[datetime] = None
    anthropic_manual_balance_amount: Optional[str] = None
    anthropic_manual_balance_currency: Optional[str] = None
    anthropic_manual_balance_entered_at: Optional[datetime] = None


class CredentialCipher(Protocol):
    def encrypt(self, credentials: dict[str, Any]) -> str: ...
    def decrypt(self, value: str) -> dict[str, Any]: ...


class GenericProviderAdapter(Protocol):
    provider_id: str
    def verify(self, data: dict[str, Any]) -> dict[str, Any]: ...
