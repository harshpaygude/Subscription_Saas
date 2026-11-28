"""Configuration for the UniSora API Gateway."""
from unisora_kit import BaseServiceSettings


class GatewaySettings(BaseServiceSettings):
    service_name: str = "api-gateway"
    frontend_url: str = "http://127.0.0.1:3000"
    rate_limit_per_minute: int = 600
    request_timeout_seconds: float = 30.0

    identity_service_url: str = "http://identity-service:8001"
    subscription_service_url: str = "http://subscription-service:8002"
    asset_service_url: str = "http://asset-service:8003"
    lifecycle_service_url: str = "http://lifecycle-service:8004"
    integration_service_url: str = "http://integration-service:8005"
    governance_service_url: str = "http://governance-service:8006"

    # Optional JSON list of extra [{"prefix": "/billing-v2", "service": "billing", "url": "http://billing:8007"}]
    extra_routes_json: str = "[]"


settings = GatewaySettings()
