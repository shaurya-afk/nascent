from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    groq_api_key: str = ""
    database_url: str = ""
    alembic_database_url: str = ""

    github_app_id: int = Field(alias="GITHUB_APP_ID")
    github_client_id: str = Field(alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(alias="GITHUB_CLIENT_SECRET")
    github_private_key: str = Field(alias="GITHUB_PRIVATE_KEY")

    secret_key: str = Field(alias="SECRET_KEY")
    frontend_url: str = Field(alias="FRONTEND_URL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
