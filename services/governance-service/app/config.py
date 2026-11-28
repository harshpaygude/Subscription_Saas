"""Configuration for Governance (Alerts, Analytics, Audit) microservice."""
from unisora_kit import BaseServiceSettings


class GovernanceSettings(BaseServiceSettings):
    service_name: str = "governance-service"
    database_url: str = "sqlite:///./governance.db"

    identity_service_url: str = "http://identity-service:8001"
    subscription_service_url: str = "http://subscription-service:8002"
    asset_service_url: str = "http://asset-service:8003"


settings = GovernanceSettings()
