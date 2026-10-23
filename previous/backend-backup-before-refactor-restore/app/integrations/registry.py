"""Provider registration without making shared code know provider details."""

from typing import Dict, Iterable, List

from app.integrations.base import IntegrationProvider, ProviderMetadata


class ProviderRegistry:
    def __init__(self, providers: Iterable[IntegrationProvider] = ()):
        self._providers: Dict[str, IntegrationProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: IntegrationProvider) -> None:
        key = provider.provider_id.upper()
        if key in self._providers:
            raise ValueError("Provider already registered: {}".format(key))
        self._providers[key] = provider

    def get(self, provider_id: str) -> IntegrationProvider:
        try:
            return self._providers[provider_id.upper()]
        except KeyError:
            raise KeyError("Unsupported integration provider: {}".format(provider_id))

    def list_metadata(self) -> List[ProviderMetadata]:
        return [provider.metadata for provider in self._providers.values()]
