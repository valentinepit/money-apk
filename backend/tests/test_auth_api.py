import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_uow
from app.main import app
from app.models import User
from app.security import hash_password
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
async def seeded_user(db_session):
    user = User(email="admin@example.com", password_hash=hash_password("admin-pass"))
    db_session.add(user)
    await db_session.flush()
    return user


async def test_login_with_correct_credentials_returns_token(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["token_type"] == "bearer"
    assert isinstance(body["data"]["access_token"], str) and body["data"]["access_token"]


async def test_login_with_wrong_password_returns_401(client, seeded_user):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_login_with_unknown_email_returns_401(client):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert response.status_code == 401


async def test_me_without_token_returns_401(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_valid_token_returns_current_user(client, seeded_user):
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    )
    token = login_response.json()["data"]["access_token"]

    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "admin@example.com"


async def test_me_with_invalid_token_returns_401(client):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401
