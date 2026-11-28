"""Base service configuration shared across UniSora microservices."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Environment-driven baseline configuration for a microservice."""

    service_name: str = "unisora-service"
    service_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    jwt_secret_key: str = "dev-insecure-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    internal_service_secret: str = "dev-internal-service-secret-change-me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
