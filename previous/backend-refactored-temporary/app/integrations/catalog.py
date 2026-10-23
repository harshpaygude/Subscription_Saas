"""Application-wide provider catalog."""

from app.integrations.registry import ProviderRegistry


def get_provider_registry() -> ProviderRegistry:
    # Imported lazily so importing shared contracts never initializes boto3.
    from app.integrations.aws.provider import AWSProvider

    return ProviderRegistry([AWSProvider()])
