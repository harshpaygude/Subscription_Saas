"""Configuration for Identity & Organization microservice."""
from unisora_kit import BaseServiceSettings


class IdentitySettings(BaseServiceSettings):
    service_name: str = "identity-service"
    database_url: str = "sqlite:///./identity.db"
    access_token_expire_minutes: int = 60

    asset_service_url: str = "http://asset-service:8003"
    subscription_service_url: str = "http://subscription-service:8002"
    lifecycle_service_url: str = "http://lifecycle-service:8004"
    integration_service_url: str = "http://integration-service:8005"
    governance_service_url: str = "http://governance-service:8006"


settings = IdentitySettings()
