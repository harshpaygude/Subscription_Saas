from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Subscription Management SaaS"
    app_version: str = "0.1.0"

    database_url: str

    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # The role that UniSora owns in its backend AWS account.  This is the
    # principal customers trust; it is never inferred from a developer's
    # local CLI identity.
    aws_backend_role_arn: str = ""
    aws_region: str = "us-east-1"
    aws_bootstrap_profile: str = ""
    aws_role_session_duration_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
