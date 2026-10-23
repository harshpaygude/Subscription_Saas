
"""Small, provider-neutral contracts used by the integration platform."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    display_name: str
    description: str
    capabilities: List[str]


class ConnectionVerifier(Protocol):
    def verify_connection(self, connection: Any) -> Dict[str, Any]: ...


class UsageReporter(Protocol):
    def get_costs(self, connection: Any) -> Dict[str, Any]: ...


class AccountPlanReporter(Protocol):
    def get_account_plan(self, connection: Any) -> Dict[str, Any]: ...


class IntegrationProvider(ABC):
    """Provider metadata and only the capabilities it actually supports."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        raise NotImplementedError

    def verifier(self) -> Optional[ConnectionVerifier]:
        return None

    def usage_reporter(self) -> Optional[UsageReporter]:
        return None

    def account_plan_reporter(self) -> Optional[AccountPlanReporter]:
        return None
