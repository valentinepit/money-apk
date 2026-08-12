import uuid
from datetime import date, datetime, timezone

import pytest

from app.exceptions import (
    CategoryIsSystemError,
    InvalidCredentialsError,
    NotFoundError,
)
from app.models import Category, CategorizationRule, RuleSource, Transaction, TransactionSource, User
from app.repositories.transactions import TransactionFilters
from app.security import hash_password
from app.services import auth_service, category_service, report_service, transaction_service


async def make_user(uow, email="owner@example.com") -> User:
    user = User(email=email, password_hash=hash_password("pass"))
    await uow.users.add(user)
    await uow.session.flush()
    return user


async def make_default_category(uow) -> Category:
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    await uow.categories.add(category)
    await uow.session.flush()
    return category


# --- auth_service ---


async def test_authenticate_with_correct_credentials_returns_user(uow):
    user = await make_user(uow)
    await uow.commit()

    result = await auth_service.authenticate(uow, "owner@example.com", "pass")
    assert result.id == user.id


async def test_authenticate_with_wrong_password_raises(uow):
    await make_user(uow)
    await uow.commit()

    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(uow, "owner@example.com", "wrong")


async def test_authenticate_with_unknown_email_raises(uow):
    with pytest.raises(InvalidCredentialsError):
        await auth_service.authenticate(uow, "nobody@example.com", "whatever")


async def test_get_user_by_id_unknown_raises_not_found(uow):
    with pytest.raises(NotFoundError):
        await auth_service.get_user_by_id(uow, uuid.uuid4())


# --- category_service ---


async def test_create_category_persists(uow):
    user = await make_user(uow)
    category = await category_service.create_category(uow, user.id, name="Транспорт", icon="bus")
    assert category.id is not None
    assert category.icon == "bus"


async def test_list_categories_excludes_deleted_by_default(uow):
    user = await make_user(uow)
    await category_service.create_category(uow, user.id, name="Активная")
    deleted = await category_service.create_category(uow, user.id, name="Старая")
    deleted.deleted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await uow.commit()

    categories = await category_service.list_categories(uow, user.id)
    assert {c.name for c in categories} == {"Активная"}


async def test_delete_system_category_raises_conflict(uow):
    user = await make_user(uow)
    default_category = await make_default_category(uow)
    await uow.commit()

    with pytest.raises(CategoryIsSystemError):
        await category_service.delete_category(uow, user.id, default_category.id)


async def test_delete_category_soft_deletes(uow, db_session):
    user = await make_user(uow)
    category = await category_service.create_category(uow, user.id, name="Транспорт")

    await category_service.delete_category(uow, user.id, category.id)

    await db_session.refresh(category)
    assert category.deleted_at is not None


async def test_get_unknown_category_raises_not_found(uow):
    user = await make_user(uow)
    with pytest.raises(NotFoundError):
        await category_service.get_category(uow, user.id, uuid.uuid4())


# --- transaction_service ---


async def test_create_transaction_without_category_defaults_to_system_category(uow):
    user = await make_user(uow)
    default_category = await make_default_category(uow)
    await uow.commit()

    transaction = await transaction_service.create_transaction(
        uow,
        user.id,
        amount=12.5,
        category_id=None,
        merchant_raw="REWE 123",
        note=None,
        transaction_date=date(2026, 8, 5),
    )
    assert transaction.category_id == default_category.id
    assert transaction.merchant_normalized == "REWE"


async def test_update_transaction_category_creates_user_rule(uow, db_session):
    user = await make_user(uow)
    default_category = await make_default_category(uow)
    groceries = Category(user_id=user.id, name="Продукты")
    await uow.categories.add(groceries)
    await uow.commit()

    transaction = await transaction_service.create_transaction(
        uow,
        user.id,
        amount=10,
        category_id=default_category.id,
        merchant_raw="REWE 42",
        note=None,
        transaction_date=date(2026, 8, 5),
    )

    await transaction_service.update_transaction(
        uow, user.id, transaction.id, {"category_id": groceries.id}
    )

    from sqlalchemy import select

    rule = (
        await db_session.scalars(
            select(CategorizationRule).where(
                CategorizationRule.user_id == user.id,
                CategorizationRule.merchant_pattern == "REWE",
            )
        )
    ).one()
    assert rule.category_id == groceries.id
    assert rule.source == RuleSource.user_rule


async def test_list_transactions_paginates(uow):
    user = await make_user(uow)
    default_category = await make_default_category(uow)
    await uow.commit()

    for i in range(3):
        await transaction_service.create_transaction(
            uow,
            user.id,
            amount=1 + i,
            category_id=default_category.id,
            merchant_raw="SHOP",
            note=None,
            transaction_date=date(2026, 8, i + 1),
        )

    page = await transaction_service.list_transactions(
        uow, user.id, TransactionFilters(), page=1, per_page=2
    )
    assert page.total == 3
    assert len(page.items) == 2


async def test_delete_transaction_soft_deletes(uow, db_session):
    user = await make_user(uow)
    default_category = await make_default_category(uow)
    await uow.commit()

    transaction = await transaction_service.create_transaction(
        uow,
        user.id,
        amount=10,
        category_id=default_category.id,
        merchant_raw="SHOP",
        note=None,
        transaction_date=date(2026, 8, 5),
    )

    await transaction_service.delete_transaction(uow, user.id, transaction.id)

    await db_session.refresh(transaction)
    assert transaction.deleted_at is not None


# --- report_service ---


async def test_report_by_category_sums_and_sorts_desc(uow):
    user = await make_user(uow)
    groceries = Category(user_id=user.id, name="Продукты")
    transport = Category(user_id=user.id, name="Транспорт")
    await uow.categories.add(groceries)
    await uow.categories.add(transport)
    await uow.session.flush()

    rows = [
        (groceries.id, 10, date(2026, 8, 1)),
        (groceries.id, 15, date(2026, 8, 2)),
        (transport.id, 50, date(2026, 8, 3)),
        (groceries.id, 5, date(2026, 1, 1)),  # вне диапазона
    ]
    for category_id, amount, tx_date in rows:
        await uow.transactions.add(
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
    await uow.commit()

    report = await report_service.report_by_category(
        uow, user.id, date(2026, 8, 1), date(2026, 8, 31)
    )

    assert [row.category_name for row in report] == ["Транспорт", "Продукты"]
    groceries_row = next(r for r in report if r.category_name == "Продукты")
    assert groceries_row.total == 25
    assert groceries_row.count == 2
