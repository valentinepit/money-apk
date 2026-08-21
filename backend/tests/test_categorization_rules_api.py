import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_uow
from app.main import app
from app.models import Category, CategorizationRule, RuleSource, User
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
async def other_user(db_session) -> User:
    user = User(email="other@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers(user):
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def category(db_session, user) -> Category:
    category = Category(user_id=user.id, name="Продукты")
    db_session.add(category)
    await db_session.flush()
    return category


async def test_list_rules_requires_auth(client):
    response = await client.get("/api/v1/categorization-rules")
    assert response.status_code == 401


async def test_list_rules_returns_own_and_system_rules(
    client, auth_headers, db_session, user, other_user, category
):
    own_rule = CategorizationRule(
        user_id=user.id, merchant_pattern="REWE", category_id=category.id, source=RuleSource.user_rule
    )
    system_rule = CategorizationRule(
        user_id=None,
        merchant_pattern="ALDI",
        category_id=category.id,
        source=RuleSource.system_dictionary,
    )
    others_rule = CategorizationRule(
        user_id=other_user.id,
        merchant_pattern="LIDL",
        category_id=category.id,
        source=RuleSource.user_rule,
    )
    db_session.add_all([own_rule, system_rule, others_rule])
    await db_session.flush()

    response = await client.get("/api/v1/categorization-rules", headers=auth_headers)
    assert response.status_code == 200
    patterns = {r["merchant_pattern"] for r in response.json()["data"]}
    assert patterns == {"REWE", "ALDI"}


async def test_list_rules_filters_by_source(client, auth_headers, db_session, user, category):
    own_rule = CategorizationRule(
        user_id=user.id, merchant_pattern="REWE", category_id=category.id, source=RuleSource.user_rule
    )
    system_rule = CategorizationRule(
        user_id=None,
        merchant_pattern="ALDI",
        category_id=category.id,
        source=RuleSource.system_dictionary,
    )
    db_session.add_all([own_rule, system_rule])
    await db_session.flush()

    response = await client.get(
        "/api/v1/categorization-rules?source=user_rule", headers=auth_headers
    )
    assert response.status_code == 200
    patterns = {r["merchant_pattern"] for r in response.json()["data"]}
    assert patterns == {"REWE"}


async def test_delete_own_rule(client, auth_headers, db_session, user, category):
    rule = CategorizationRule(
        user_id=user.id, merchant_pattern="REWE", category_id=category.id, source=RuleSource.user_rule
    )
    db_session.add(rule)
    await db_session.flush()

    rule_id = rule.id
    response = await client.delete(f"/api/v1/categorization-rules/{rule_id}", headers=auth_headers)
    assert response.status_code == 204

    remaining = await db_session.get(CategorizationRule, rule_id)
    assert remaining is None


async def test_delete_unknown_rule_returns_404(client, auth_headers):
    response = await client.delete(
        "/api/v1/categorization-rules/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_delete_other_users_rule_returns_404(
    client, auth_headers, db_session, other_user, category
):
    rule = CategorizationRule(
        user_id=other_user.id,
        merchant_pattern="LIDL",
        category_id=category.id,
        source=RuleSource.user_rule,
    )
    db_session.add(rule)
    await db_session.flush()

    response = await client.delete(f"/api/v1/categorization-rules/{rule.id}", headers=auth_headers)
    assert response.status_code == 404


async def test_delete_system_rule_is_forbidden(client, auth_headers, db_session, category):
    rule = CategorizationRule(
        user_id=None,
        merchant_pattern="ALDI",
        category_id=category.id,
        source=RuleSource.system_dictionary,
    )
    db_session.add(rule)
    await db_session.flush()

    response = await client.delete(f"/api/v1/categorization-rules/{rule.id}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "rule_is_system"
