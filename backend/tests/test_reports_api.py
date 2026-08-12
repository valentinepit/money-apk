import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Category, Transaction, TransactionSource, User
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


def test_report_by_category_sums_and_sorts_desc(client, auth_headers, db_session, user):
    groceries = Category(user_id=user.id, name="Продукты")
    transport = Category(user_id=user.id, name="Транспорт")
    db_session.add_all([groceries, transport])
    db_session.flush()

    rows = [
        (groceries.id, 10, "2026-08-01"),
        (groceries.id, 15, "2026-08-02"),
        (transport.id, 50, "2026-08-03"),
        (groceries.id, 5, "2026-01-01"),  # вне диапазона
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
    db_session.flush()

    response = client.get(
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


def test_report_by_category_excludes_deleted_transactions(client, auth_headers, db_session, user):
    category = Category(user_id=user.id, name="Продукты")
    db_session.add(category)
    db_session.flush()

    db_session.add(
        Transaction(
            user_id=user.id,
            category_id=category.id,
            amount=100,
            merchant_raw="X",
            merchant_normalized="X",
            transaction_date="2026-08-01",
            source=TransactionSource.manual,
            deleted_at="2026-01-01T00:00:00Z",
        )
    )
    db_session.flush()

    response = client.get(
        "/api/v1/reports/by-category?date_from=2026-08-01&date_to=2026-08-31",
        headers=auth_headers,
    )
    assert response.json()["data"] == []
    assert response.json()["meta"]["total_overall"] == 0


def test_report_by_category_requires_date_range(client, auth_headers):
    response = client.get("/api/v1/reports/by-category", headers=auth_headers)
    assert response.status_code == 422
