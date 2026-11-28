"""Configuration for IT Asset Management microservice."""
from unisora_kit import BaseServiceSettings


class AssetSettings(BaseServiceSettings):
    service_name: str = "asset-service"
    database_url: str = "sqlite:///./assets.db"

    identity_service_url: str = "http://identity-service:8001"
    governance_service_url: str = "http://governance-service:8006"


settings = AssetSettings()
