import os

from app.config import Settings


def test_settings_reads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/dbname")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-pass")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg2://user:pass@localhost/dbname"
    assert settings.jwt_secret_key == "test-secret"
    assert settings.admin_email == "admin@example.com"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expires_minutes > 0
