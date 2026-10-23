from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "Subscription Management SaaS"
    app_version: str = "0.1.0"

    database_url: str

    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_tenant: str = "common"
    azure_redirect_uri: str = "http://127.0.0.1:8000/integrations/azure/oauth/callback"
    azure_scopes: str = "https://management.azure.com/user_impersonation"
    azure_token_encryption_key: str = ""
    frontend_url: str = "http://127.0.0.1:3000"
    anthropic_default_model: str = "claude-sonnet-4-6"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(
        # Resolve the environment file from the backend package, rather than
        # from the shell's current directory. This keeps `uvicorn app.main:app`
        # working from either the repository root or the backend directory.
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
