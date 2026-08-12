import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_user(db_session):
    user = User(email="admin@example.com", password_hash=hash_password("admin-pass"))
    db_session.add(user)
    db_session.flush()
    return user


def test_login_with_correct_credentials_returns_token(client, seeded_user):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["token_type"] == "bearer"
    assert isinstance(body["data"]["access_token"], str) and body["data"]["access_token"]


def test_login_with_wrong_password_returns_401(client, seeded_user):
    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_with_unknown_email_returns_401(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_with_valid_token_returns_current_user(client, seeded_user):
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    )
    token = login_response.json()["data"]["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "admin@example.com"


def test_me_with_invalid_token_returns_401(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401
