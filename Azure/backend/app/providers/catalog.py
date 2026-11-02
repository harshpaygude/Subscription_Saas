from dataclasses import dataclass
from enum import StrEnum


class ProviderStatus(StrEnum):
    PLANNED = "planned"
    NOT_CONNECTED = "not_connected"


@dataclass(frozen=True)
class ProviderDefinition:
    key: str
    name: str
    description: str
    status: ProviderStatus = ProviderStatus.PLANNED
    capabilities: tuple[str, ...] = ()


PROVIDERS = (
    ProviderDefinition("aws", "Amazon Web Services", "Connect AWS accounts and subscriptions.", capabilities=("account-discovery",)),
    ProviderDefinition("openai", "OpenAI", "Connect OpenAI organizations and usage data.", capabilities=("organization-discovery",)),
    ProviderDefinition("azure", "Microsoft Azure", "Connect Azure tenants, subscriptions, resources, cost, and usage.", status=ProviderStatus.NOT_CONNECTED, capabilities=("oauth", "tenant-discovery", "subscription-discovery", "resource-inventory", "cost-query")),
)
