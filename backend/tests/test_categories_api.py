from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_uow
from app.main import app
from app.models import Category, User
from app.security import create_access_token, hash_password
from app.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
async def client(db_session):
    # Один и тот же (уже "открытый") UoW отдаётся на каждый HTTP-запрос внутри
    # теста — иначе __aexit__ каждого отдельного запроса делал бы rollback()
    # общего с фикстурами savepoint'а и стирал бы данные, подготовленные для
    # теста (или предыдущим запросом) до того, как дошли до текущего запроса.
    uow = SqlAlchemyUnitOfWork(session=db_session)
    await uow.__aenter__()

    async def override_get_uow():
        yield uow

    app.dependency_overrides[get_uow] = override_get_uow
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await uow.__aexit__(None, None, None)


@pytest.fixture
async def user(db_session) -> User:
    user = User(email="owner@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers(user):
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def default_category(db_session) -> Category:
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    await db_session.flush()
    return category


async def test_list_categories_requires_auth(client):
    response = await client.get("/api/v1/categories")
    assert response.status_code == 401


async def test_list_categories_excludes_deleted_by_default(client, auth_headers, db_session, user):
    active = Category(user_id=user.id, name="Продукты")
    deleted = Category(
        user_id=user.id, name="Старая", deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    db_session.add_all([active, deleted])
    await db_session.flush()

    response = await client.get("/api/v1/categories", headers=auth_headers)
    assert response.status_code == 200
    names = {c["name"] for c in response.json()["data"]}
    assert names == {"Продукты"}


async def test_create_category(client, auth_headers):
    response = await client.post(
        "/api/v1/categories", json={"name": "Транспорт", "icon": "bus"}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["name"] == "Транспорт"
    assert body["icon"] == "bus"
    assert body["is_system"] is False


async def test_update_category(client, auth_headers, db_session, user):
    category = Category(user_id=user.id, name="Транспорт")
    db_session.add(category)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/categories/{category.id}", json={"name": "Транспорт и авто"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Транспорт и авто"


async def test_update_unknown_category_returns_404(client, auth_headers):
    response = await client.patch(
        "/api/v1/categories/00000000-0000-0000-0000-000000000000",
        json={"name": "x"},
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_delete_category_soft_deletes(client, auth_headers, db_session, user):
    category = Category(user_id=user.id, name="Транспорт")
    db_session.add(category)
    await db_session.flush()

    category_id = category.id
    response = await client.delete(f"/api/v1/categories/{category_id}", headers=auth_headers)
    assert response.status_code == 204

    db_session.expire_all()
    refreshed = await db_session.get(Category, category_id)
    assert refreshed.deleted_at is not None


async def test_delete_system_category_is_forbidden(client, auth_headers, default_category):
    response = await client.delete(
        f"/api/v1/categories/{default_category.id}", headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "category_is_system"
