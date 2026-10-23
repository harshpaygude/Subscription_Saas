from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Unified Cloud Platform", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    backend_host: str = Field(default="127.0.0.1", validation_alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, validation_alias="BACKEND_PORT")
    database_url: str = Field(
        default="postgresql+psycopg://platform:platform@localhost:5432/platform",
        validation_alias="DATABASE_URL",
    )
    azure_client_id: str = Field(default="", validation_alias="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(default="", validation_alias="AZURE_CLIENT_SECRET")
    azure_tenant: str = Field(default="common", validation_alias="AZURE_TENANT")
    azure_redirect_uri: str = Field(default="http://localhost:8000/api/azure/oauth/callback", validation_alias="AZURE_REDIRECT_URI")
    azure_scopes: str = Field(default="https://management.azure.com/user_impersonation", validation_alias="AZURE_SCOPES")
    azure_token_encryption_key: str = Field(default="", validation_alias="AZURE_TOKEN_ENCRYPTION_KEY")
    platform_user_header: str = Field(default="X-Platform-User-ID", validation_alias="PLATFORM_USER_HEADER")
    allow_local_platform_user_header: bool = Field(default=True, validation_alias="ALLOW_LOCAL_PLATFORM_USER_HEADER")
    oauth_state_cookie: str = Field(default="azure_oauth_state", validation_alias="AZURE_OAUTH_STATE_COOKIE")
    dev_identity_cookie: str = Field(default="azure_dev_identity", validation_alias="AZURE_DEV_IDENTITY_COOKIE")
    enable_manual_azure_token_input: bool = Field(default=False, validation_alias="ENABLE_MANUAL_AZURE_TOKEN_INPUT")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
