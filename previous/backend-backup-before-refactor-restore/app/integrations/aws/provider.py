"""AWS provider adapter for the shared provider registry."""

from app.integrations.base import IntegrationProvider, ProviderMetadata


class AWSProvider(IntegrationProvider):
    @property
    def provider_id(self) -> str:
        return "AWS"

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_id="AWS",
            display_name="Amazon Web Services",
            description="Connect an AWS account for read-only spend and plan data.",
            capabilities=["connection_setup", "costs", "account_plan"],
        )
