import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Category, User
from app.security import create_access_token, hash_password


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def user(db_session) -> User:
    user = User(email="owner@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def auth_headers(user):
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def default_category(db_session) -> Category:
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    db_session.flush()
    return category


def test_list_categories_requires_auth(client):
    response = client.get("/api/v1/categories")
    assert response.status_code == 401


def test_list_categories_excludes_deleted_by_default(client, auth_headers, db_session, user):
    active = Category(user_id=user.id, name="Продукты")
    deleted = Category(user_id=user.id, name="Старая", deleted_at="2026-01-01T00:00:00Z")
    db_session.add_all([active, deleted])
    db_session.flush()

    response = client.get("/api/v1/categories", headers=auth_headers)
    assert response.status_code == 200
    names = {c["name"] for c in response.json()["data"]}
    assert names == {"Продукты"}


def test_create_category(client, auth_headers):
    response = client.post(
        "/api/v1/categories", json={"name": "Транспорт", "icon": "bus"}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["name"] == "Транспорт"
    assert body["icon"] == "bus"
    assert body["is_system"] is False


def test_update_category(client, auth_headers, db_session, user):
    category = Category(user_id=user.id, name="Транспорт")
    db_session.add(category)
    db_session.flush()

    response = client.patch(
        f"/api/v1/categories/{category.id}", json={"name": "Транспорт и авто"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Транспорт и авто"


def test_update_unknown_category_returns_404(client, auth_headers):
    response = client.patch(
        "/api/v1/categories/00000000-0000-0000-0000-000000000000",
        json={"name": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_category_soft_deletes(client, auth_headers, db_session, user):
    category = Category(user_id=user.id, name="Транспорт")
    db_session.add(category)
    db_session.flush()

    response = client.delete(f"/api/v1/categories/{category.id}", headers=auth_headers)
    assert response.status_code == 204

    db_session.expire_all()
    refreshed = db_session.get(Category, category.id)
    assert refreshed.deleted_at is not None


def test_delete_system_category_is_forbidden(client, auth_headers, default_category):
    response = client.delete(f"/api/v1/categories/{default_category.id}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_is_system"
