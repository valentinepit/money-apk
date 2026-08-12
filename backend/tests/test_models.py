import uuid

from app.models import (
    Account,
    Category,
    CategorizationRule,
    RuleSource,
    Transaction,
    TransactionSource,
    User,
)


def make_user(db_session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    return user


def test_create_user_account_category(db_session):
    user = make_user(db_session)
    account = Account(user_id=user.id, name="Основной счёт", currency="EUR")
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add_all([account, category])
    db_session.flush()

    assert account.id is not None
    assert category.deleted_at is None
    assert category.is_system is True


def test_transaction_requires_category(db_session):
    user = make_user(db_session)
    account = Account(user_id=user.id, name="Основной счёт", currency="EUR")
    db_session.add(account)
    db_session.flush()

    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=None,
        amount=10,
        merchant_raw="TEST SHOP",
        merchant_normalized="TEST SHOP",
        transaction_date="2026-08-01",
        source=TransactionSource.manual,
    )
    db_session.add(transaction)

    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_transaction_soft_delete_defaults_to_none(db_session):
    user = make_user(db_session)
    account = Account(user_id=user.id, name="Основной счёт", currency="EUR")
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add_all([account, category])
    db_session.flush()

    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        amount=42.50,
        merchant_raw="REWE",
        merchant_normalized="REWE",
        transaction_date="2026-08-05",
        source=TransactionSource.manual,
    )
    db_session.add(transaction)
    db_session.flush()

    assert transaction.deleted_at is None
    assert transaction.source == TransactionSource.manual


def test_categorization_rule_links_merchant_to_category(db_session):
    user = make_user(db_session)
    category = Category(name="Продукты")
    db_session.add(category)
    db_session.flush()

    rule = CategorizationRule(
        user_id=user.id,
        merchant_pattern="REWE",
        category_id=category.id,
        source=RuleSource.user_rule,
    )
    db_session.add(rule)
    db_session.flush()

    assert rule.id is not None
    assert rule.source == RuleSource.user_rule
