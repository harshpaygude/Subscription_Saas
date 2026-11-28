"""Configuration for External Provider Integration microservice."""
from unisora_kit import BaseServiceSettings


class IntegrationSettings(BaseServiceSettings):
    service_name: str = "integration-service"
    database_url: str = "sqlite:///./integrations.db"

    frontend_url: str = "http://127.0.0.1:3000"
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant: str = "common"
    azure_redirect_uri: str = "http://127.0.0.1:8000/integrations/azure/oauth/callback"
    azure_scopes: str = "https://management.azure.com/user_impersonation"
    azure_token_encryption_key: str = ""
    anthropic_default_model: str = "claude-sonnet-4-6"

    governance_service_url: str = "http://governance-service:8006"


settings = IntegrationSettings()
