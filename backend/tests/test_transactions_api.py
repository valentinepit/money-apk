import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Category, CategorizationRule, RuleSource, Transaction, TransactionSource, User
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
def other_user(db_session) -> User:
    user = User(email="other@example.com", password_hash=hash_password("pass"))
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


@pytest.fixture
def groceries_category(db_session, user) -> Category:
    category = Category(user_id=user.id, name="Продукты")
    db_session.add(category)
    db_session.flush()
    return category


def test_create_transaction_without_category_defaults_to_other(
    client, auth_headers, default_category
):
    response = client.post(
        "/api/v1/transactions",
        json={"amount": 12.5, "merchant_raw": "REWE 123", "transaction_date": "2026-08-05"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["category_id"] == str(default_category.id)
    assert body["merchant_normalized"] == "REWE"
    assert body["amount"] == 12.5


def test_create_transaction_with_category(client, auth_headers, groceries_category):
    response = client.post(
        "/api/v1/transactions",
        json={
            "amount": 5,
            "category_id": str(groceries_category.id),
            "transaction_date": "2026-08-05",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["data"]["category_id"] == str(groceries_category.id)


def test_list_transactions_excludes_deleted_and_paginates(
    client, auth_headers, db_session, user, default_category
):
    for i in range(3):
        db_session.add(
            Transaction(
                user_id=user.id,
                category_id=default_category.id,
                amount=1 + i,
                merchant_raw="SHOP",
                merchant_normalized="SHOP",
                transaction_date=f"2026-08-0{i + 1}",
                source=TransactionSource.manual,
            )
        )
    deleted = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=99,
        merchant_raw="OLD",
        merchant_normalized="OLD",
        transaction_date="2026-08-01",
        source=TransactionSource.manual,
        deleted_at="2026-01-01T00:00:00Z",
    )
    db_session.add(deleted)
    db_session.flush()

    response = client.get("/api/v1/transactions?per_page=2&page=1", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 3
    assert body["meta"]["total_pages"] == 2
    assert len(body["data"]) == 2


def test_list_transactions_filters_by_date_range(
    client, auth_headers, db_session, user, default_category
):
    in_range = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=1,
        merchant_raw="IN",
        merchant_normalized="IN",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    out_of_range = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=2,
        merchant_raw="OUT",
        merchant_normalized="OUT",
        transaction_date="2026-01-01",
        source=TransactionSource.manual,
    )
    db_session.add_all([in_range, out_of_range])
    db_session.flush()

    response = client.get(
        "/api/v1/transactions?date_from=2026-08-01&date_to=2026-08-31", headers=auth_headers
    )
    assert response.status_code == 200
    merchants = {t["merchant_raw"] for t in response.json()["data"]}
    assert merchants == {"IN"}


def test_transactions_are_scoped_to_current_user(
    client, auth_headers, db_session, user, other_user, default_category
):
    mine = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=1,
        merchant_raw="MINE",
        merchant_normalized="MINE",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    theirs = Transaction(
        user_id=other_user.id,
        category_id=default_category.id,
        amount=1,
        merchant_raw="THEIRS",
        merchant_normalized="THEIRS",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    db_session.add_all([mine, theirs])
    db_session.flush()

    response = client.get("/api/v1/transactions", headers=auth_headers)
    merchants = {t["merchant_raw"] for t in response.json()["data"]}
    assert merchants == {"MINE"}


def test_update_transaction_category_creates_user_rule(
    client, auth_headers, db_session, user, default_category, groceries_category
):
    transaction = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=10,
        merchant_raw="REWE 42",
        merchant_normalized="REWE",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    db_session.add(transaction)
    db_session.flush()

    response = client.patch(
        f"/api/v1/transactions/{transaction.id}",
        json={"category_id": str(groceries_category.id)},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["category_id"] == str(groceries_category.id)

    rule = (
        db_session.query(CategorizationRule)
        .filter(
            CategorizationRule.user_id == user.id,
            CategorizationRule.merchant_pattern == "REWE",
        )
        .one()
    )
    assert rule.category_id == groceries_category.id
    assert rule.source == RuleSource.user_rule


def test_update_transaction_category_upserts_existing_rule(
    client, auth_headers, db_session, user, default_category, groceries_category
):
    existing_rule = CategorizationRule(
        user_id=user.id,
        merchant_pattern="REWE",
        category_id=default_category.id,
        source=RuleSource.user_rule,
    )
    db_session.add(existing_rule)

    transaction = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=10,
        merchant_raw="REWE 42",
        merchant_normalized="REWE",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    db_session.add(transaction)
    db_session.flush()

    client.patch(
        f"/api/v1/transactions/{transaction.id}",
        json={"category_id": str(groceries_category.id)},
        headers=auth_headers,
    )

    rules = (
        db_session.query(CategorizationRule)
        .filter(
            CategorizationRule.user_id == user.id,
            CategorizationRule.merchant_pattern == "REWE",
        )
        .all()
    )
    assert len(rules) == 1
    assert rules[0].category_id == groceries_category.id


def test_delete_transaction_soft_deletes(client, auth_headers, db_session, user, default_category):
    transaction = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=10,
        merchant_raw="SHOP",
        merchant_normalized="SHOP",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    db_session.add(transaction)
    db_session.flush()

    response = client.delete(f"/api/v1/transactions/{transaction.id}", headers=auth_headers)
    assert response.status_code == 204

    db_session.expire_all()
    refreshed = db_session.get(Transaction, transaction.id)
    assert refreshed.deleted_at is not None


def test_get_unknown_transaction_returns_404(client, auth_headers):
    response = client.get(
        "/api/v1/transactions/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404
