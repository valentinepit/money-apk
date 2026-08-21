"""
TDD-тесты дедупликации при импорте (фаза 6, claude/plan.md): строка выписки,
которая уже есть в базе как транзакция пользователя, не должна попадать в
preview повторно (см. app/services/import_service.py).

Проверяется на уровне сервиса (create_import_session), а не HTTP — так проще
подставить фиктивный парсер с точно контролируемым external_ref, без нужды
подбирать реальный CSV-образец под оба сценария (с номером операции и без).
"""

from datetime import date

import pytest

from app.models import Category, Transaction, TransactionSource, User
from app.normalization import normalize_merchant
from app.parsers.base import BankStatementParser, ParsedTransaction
from app.security import hash_password
from app.services import import_service


class _FakeParser(BankStatementParser):
    name = "fake_parser"

    def __init__(self, lines: list[ParsedTransaction]) -> None:
        self._lines = lines

    @classmethod
    def can_parse(cls, raw_bytes: bytes, file_name: str) -> bool:
        return True

    def parse(self, raw_bytes: bytes) -> list[ParsedTransaction]:
        return self._lines


@pytest.fixture
async def user(db_session) -> User:
    user = User(email="owner@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def default_category(db_session) -> Category:
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    await db_session.flush()
    return category


def _patch_parser(monkeypatch, lines: list[ParsedTransaction]) -> None:
    monkeypatch.setattr(
        import_service, "get_parser_for", lambda raw_bytes, file_name: _FakeParser(lines)
    )


async def test_create_import_session_excludes_line_matching_existing_external_ref(
    monkeypatch, uow, db_session, user, default_category
):
    # Строка с external_ref="RO1986420819L01" уже была импортирована ранее
    # (например тем же самым файлом) — при повторном импорте не должна
    # попасть в preview снова, а вторая (новая) строка — должна.
    existing = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=4.96,
        merchant_raw="AI2SQL",
        merchant_normalized=normalize_merchant("AI2SQL"),
        transaction_date=date(2026, 8, 1),
        source=TransactionSource.import_,
        external_ref="RO1986420819L01",
    )
    db_session.add(existing)
    await db_session.flush()

    lines = [
        ParsedTransaction(
            line_no=1,
            transaction_date=date(2026, 8, 1),
            amount=4.96,
            merchant_raw="AI2SQL",
            external_ref="RO1986420819L01",
        ),
        ParsedTransaction(
            line_no=2,
            transaction_date=date(2026, 8, 2),
            amount=10.00,
            merchant_raw="NEW SHOP",
            external_ref="RO_NEW",
        ),
    ]
    _patch_parser(monkeypatch, lines)

    session = await import_service.create_import_session(uow, user.id, "fake.csv", b"irrelevant")
    assert [row["merchant_raw"] for row in session.parsed_preview] == ["NEW SHOP"]


async def test_create_import_session_excludes_line_matching_existing_date_amount_merchant_without_ref(
    monkeypatch, uow, db_session, user, default_category
):
    # Запасной вариант — банк/формат не даёт external_ref (здесь имитируем
    # это фиктивным парсером; на практике так же ведёт себя ручная
    # транзакция). Совпадение по (дата, сумма, нормализованное название)
    # считается дублем, несовпадение — новой строкой.
    existing = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=15.50,
        merchant_raw="Coffee House",
        merchant_normalized=normalize_merchant("Coffee House"),
        transaction_date=date(2026, 8, 3),
        source=TransactionSource.manual,
        external_ref=None,
    )
    db_session.add(existing)
    await db_session.flush()

    lines = [
        ParsedTransaction(
            line_no=1,
            transaction_date=date(2026, 8, 3),
            amount=15.50,
            merchant_raw="Coffee House",
            external_ref=None,
        ),
        ParsedTransaction(
            line_no=2,
            transaction_date=date(2026, 8, 3),
            amount=15.50,
            merchant_raw="Different Shop",
            external_ref=None,
        ),
    ]
    _patch_parser(monkeypatch, lines)

    session = await import_service.create_import_session(uow, user.id, "fake.csv", b"irrelevant")
    assert [row["merchant_raw"] for row in session.parsed_preview] == ["Different Shop"]


async def test_create_import_session_does_not_exclude_deleted_transactions(
    monkeypatch, uow, db_session, user, default_category
):
    # Мягко удалённая (deleted_at не NULL) транзакция не должна считаться
    # "уже занесённой" — иначе после удаления дубликата его будет невозможно
    # повторно импортировать.
    from datetime import datetime, timezone

    existing = Transaction(
        user_id=user.id,
        category_id=default_category.id,
        amount=4.96,
        merchant_raw="AI2SQL",
        merchant_normalized=normalize_merchant("AI2SQL"),
        transaction_date=date(2026, 8, 1),
        source=TransactionSource.import_,
        external_ref="RO1986420819L01",
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(existing)
    await db_session.flush()

    lines = [
        ParsedTransaction(
            line_no=1,
            transaction_date=date(2026, 8, 1),
            amount=4.96,
            merchant_raw="AI2SQL",
            external_ref="RO1986420819L01",
        ),
    ]
    _patch_parser(monkeypatch, lines)

    session = await import_service.create_import_session(uow, user.id, "fake.csv", b"irrelevant")
    assert [row["merchant_raw"] for row in session.parsed_preview] == ["AI2SQL"]
