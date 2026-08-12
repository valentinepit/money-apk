from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://money_apk:money_apk_dev@localhost/money_apk_dev"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 365  # долгоживущий токен, без refresh (см. docs/api/api-contract.md)

    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
