"""Configuration for Subscriptions & Licensing microservice."""
from unisora_kit import BaseServiceSettings


class SubscriptionSettings(BaseServiceSettings):
    service_name: str = "subscription-service"
    database_url: str = "sqlite:///./subscriptions.db"

    identity_service_url: str = "http://identity-service:8001"
    asset_service_url: str = "http://asset-service:8003"
    integration_service_url: str = "http://integration-service:8005"
    governance_service_url: str = "http://governance-service:8006"


settings = SubscriptionSettings()
