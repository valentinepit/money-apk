import re
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_DRIVER_RE = re.compile(r"^postgresql(\+\w+)?://")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://money_apk:money_apk_dev@localhost/money_apk_dev"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 365  # долгоживущий токен, без refresh (см. docs/api/api-contract.md)

    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"

    @property
    def async_database_url(self) -> str:
        """URL для асинхронного движка приложения (asyncpg).

        database_url — синхронный (psycopg2), используется только Alembic'ом
        для миграций (см. alembic/env.py). Само приложение работает асинхронно.
        """
        return _DRIVER_RE.sub("postgresql+asyncpg://", self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
