import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Category,
    CategorizationRule,
    RuleSource,
    Transaction,
    TransactionSource,
    User,
)


async def make_user(db_session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="hash")
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_user_and_category(db_session):
    await make_user(db_session)
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    await db_session.flush()

    assert category.id is not None
    assert category.deleted_at is None
    assert category.is_system is True


async def test_transaction_requires_category(db_session):
    user = await make_user(db_session)

    transaction = Transaction(
        user_id=user.id,
        category_id=None,
        amount=10,
        merchant_raw="TEST SHOP",
        merchant_normalized="TEST SHOP",
        transaction_date=date(2026, 8, 1),
        source=TransactionSource.manual,
    )
    db_session.add(transaction)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_transaction_soft_delete_defaults_to_none(db_session):
    user = await make_user(db_session)
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    await db_session.flush()

    transaction = Transaction(
        user_id=user.id,
        category_id=category.id,
        amount=42.50,
        merchant_raw="REWE",
        merchant_normalized="REWE",
        transaction_date=date(2026, 8, 5),
        source=TransactionSource.manual,
    )
    db_session.add(transaction)
    await db_session.flush()

    assert transaction.deleted_at is None
    assert transaction.source == TransactionSource.manual


async def test_categorization_rule_links_merchant_to_category(db_session):
    user = await make_user(db_session)
    category = Category(name="Продукты")
    db_session.add(category)
    await db_session.flush()

    rule = CategorizationRule(
        user_id=user.id,
        merchant_pattern="REWE",
        category_id=category.id,
        source=RuleSource.user_rule,
    )
    db_session.add(rule)
    await db_session.flush()

    assert rule.id is not None
    assert rule.source == RuleSource.user_rule
