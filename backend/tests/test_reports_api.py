from datetime import date, datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import get_uow
from app.main import app
from app.models import Category, Transaction, TransactionSource, User
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


async def test_report_by_category_sums_and_sorts_desc(client, auth_headers, db_session, user):
    groceries = Category(user_id=user.id, name="Продукты")
    transport = Category(user_id=user.id, name="Транспорт")
    db_session.add_all([groceries, transport])
    await db_session.flush()

    rows = [
        (groceries.id, 10, date(2026, 8, 1)),
        (groceries.id, 15, date(2026, 8, 2)),
        (transport.id, 50, date(2026, 8, 3)),
        (groceries.id, 5, date(2026, 1, 1)),  # вне диапазона
    ]
    for category_id, amount, tx_date in rows:
        db_session.add(
            Transaction(
                user_id=user.id,
                category_id=category_id,
                amount=amount,
                merchant_raw="X",
                merchant_normalized="X",
                transaction_date=tx_date,
                source=TransactionSource.manual,
            )
        )
    await db_session.flush()

    response = await client.get(
        "/api/v1/reports/by-category?date_from=2026-08-01&date_to=2026-08-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()

    assert body["meta"]["total_overall"] == 75
    assert [row["category_name"] for row in body["data"]] == ["Транспорт", "Продукты"]
    groceries_row = next(r for r in body["data"] if r["category_name"] == "Продукты")
    assert groceries_row["total"] == 25
    assert groceries_row["count"] == 2


async def test_report_by_category_excludes_deleted_transactions(
    client, auth_headers, db_session, user
):
    category = Category(user_id=user.id, name="Продукты")
    db_session.add(category)
    await db_session.flush()

    db_session.add(
        Transaction(
            user_id=user.id,
            category_id=category.id,
            amount=100,
            merchant_raw="X",
            merchant_normalized="X",
            transaction_date=date(2026, 8, 1),
            source=TransactionSource.manual,
            deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    await db_session.flush()

    response = await client.get(
        "/api/v1/reports/by-category?date_from=2026-08-01&date_to=2026-08-31",
        headers=auth_headers,
    )
    assert response.json()["data"] == []
    assert response.json()["meta"]["total_overall"] == 0


async def test_report_by_category_requires_date_range(client, auth_headers):
    response = await client.get("/api/v1/reports/by-category", headers=auth_headers)
    assert response.status_code == 422
