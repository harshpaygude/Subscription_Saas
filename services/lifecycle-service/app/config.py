"""Configuration for Employee Lifecycle microservice."""
from unisora_kit import BaseServiceSettings


class LifecycleSettings(BaseServiceSettings):
    service_name: str = "lifecycle-service"
    database_url: str = "sqlite:///./lifecycle.db"

    identity_service_url: str = "http://identity-service:8001"
    subscription_service_url: str = "http://subscription-service:8002"
    asset_service_url: str = "http://asset-service:8003"
    governance_service_url: str = "http://governance-service:8006"


settings = LifecycleSettings()
