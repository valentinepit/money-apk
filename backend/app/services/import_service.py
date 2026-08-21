"""Сервис импорт-сессий (фаза 5): загрузка файла → парсинг → превью → подтверждение.

Роутер (app/routers/import_sessions.py) — тонкий HTTP-слой, вся логика здесь.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func

from app.exceptions import (
    ImportSessionNotConfirmableError,
    NotFoundError,
    SessionAlreadyConfirmedError,
    StatementParseError,
    UnknownStatementFormatError,
)
from app.models import (
    ImportFileType,
    ImportSession,
    ImportSessionStatus,
    Transaction,
    TransactionSource,
)
from app.normalization import normalize_merchant
from app.parsers.factory import get_parser_for
from app.services.transaction_service import upsert_user_rule
from app.unit_of_work import AbstractUnitOfWork


@dataclass
class ConfirmLineUpdate:
    """Правка пользователя по одной строке превью при подтверждении импорта."""

    line_no: int
    category_id: uuid.UUID | None
    exclude: bool


def _detect_file_type(file_name: str) -> ImportFileType:
    return ImportFileType.pdf if file_name.lower().endswith(".pdf") else ImportFileType.csv


async def _get_default_category_id(uow: AbstractUnitOfWork) -> uuid.UUID:
    # Небольшое дублирование с transaction_service._get_default_category_id —
    # осознанно: обе функции приватны своим модулям, а тянуть отдельный общий
    # модуль ради одной строки пока не оправдано.
    category = await uow.categories.get_default()
    if category is None:
        raise NotFoundError("Системная категория по умолчанию не сидирована")
    return category.id


async def _suggest_category(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, merchant_normalized: str
) -> tuple[uuid.UUID, str]:
    rule = await uow.categorization_rules.get_matching_rule(user_id, merchant_normalized)
    if rule is not None:
        source = "user_rule" if rule.user_id is not None else "system_dictionary"
        return rule.category_id, source

    category_id = await _get_default_category_id(uow)
    return category_id, "default"


async def create_import_session(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, file_name: str, raw_bytes: bytes
) -> ImportSession:
    session = ImportSession(
        user_id=user_id,
        file_name=file_name,
        file_type=_detect_file_type(file_name),
        status=ImportSessionStatus.uploaded,
    )

    try:
        parser = get_parser_for(raw_bytes, file_name)
    except UnknownStatementFormatError as exc:
        session.status = ImportSessionStatus.failed
        session.error_message = exc.message
        await uow.import_sessions.add(session)
        await uow.commit()
        return session

    # bank_parser проставляем до parse() — если разбор содержимого упадёт
    # (например неожиданная валюта), формат всё равно был распознан по
    # заголовку (см. tests/test_import_sessions_api.py, invalid-currency).
    session.bank_parser = parser.name

    try:
        parsed_lines = parser.parse(raw_bytes)
    except StatementParseError as exc:
        session.status = ImportSessionStatus.failed
        session.error_message = exc.message
        await uow.import_sessions.add(session)
        await uow.commit()
        return session

    # Защита от дублей при повторном импорте (см. claude/plan.md, фаза 6):
    # строки, для которых уже есть транзакция пользователя, не попадают в
    # preview повторно. Основной способ — совпадение external_ref (номер
    # операции, присвоенный банком); запасной — для строк без external_ref
    # (банк/формат не предоставляет такого номера) — совпадение по
    # (дата, сумма, нормализованное название продавца).
    refs = {line.external_ref for line in parsed_lines if line.external_ref}
    existing_refs = await uow.transactions.find_existing_external_refs(user_id, refs)

    fallback_keys = {
        (line.transaction_date, line.amount, normalize_merchant(line.merchant_raw))
        for line in parsed_lines
        if not line.external_ref
    }
    existing_fallback_keys = await uow.transactions.find_existing_date_amount_merchant(
        user_id, fallback_keys
    )

    preview = []
    for line in parsed_lines:
        merchant_normalized = normalize_merchant(line.merchant_raw)

        if line.external_ref:
            if line.external_ref in existing_refs:
                continue
        elif (line.transaction_date, line.amount, merchant_normalized) in existing_fallback_keys:
            continue

        category_id, source = await _suggest_category(uow, user_id, merchant_normalized)
        preview.append(
            {
                "line_no": line.line_no,
                "merchant_raw": line.merchant_raw,
                "merchant_normalized": merchant_normalized,
                "amount": line.amount,
                "transaction_date": line.transaction_date.isoformat(),
                "suggested_category_id": str(category_id),
                "suggested_category_source": source,
                # Сохраняем в preview, чтобы при подтверждении (см.
                # confirm_import_session ниже) перенести на саму Transaction —
                # иначе следующий импорт той же выписки не сможет опознать
                # дубль по external_ref (см. claude/plan.md, фаза 6).
                "external_ref": line.external_ref,
            }
        )

    session.status = ImportSessionStatus.parsed
    session.parsed_preview = preview
    await uow.import_sessions.add(session)
    await uow.commit()
    return session


async def list_import_sessions(uow: AbstractUnitOfWork, user_id: uuid.UUID) -> list[ImportSession]:
    return await uow.import_sessions.list_owned(user_id)


async def get_import_session(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, session_id: uuid.UUID
) -> ImportSession:
    session = await uow.import_sessions.get_owned(session_id, user_id)
    if session is None:
        raise NotFoundError("Импорт-сессия не найдена")
    return session


async def confirm_import_session(
    uow: AbstractUnitOfWork,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    line_updates: list[ConfirmLineUpdate],
) -> list[Transaction]:
    session = await get_import_session(uow, user_id, session_id)

    if session.status == ImportSessionStatus.confirmed:
        raise SessionAlreadyConfirmedError()
    if session.parsed_preview is None:
        raise ImportSessionNotConfirmableError()

    updates_by_line = {update.line_no: update for update in line_updates}

    created: list[Transaction] = []
    for row in session.parsed_preview:
        update = updates_by_line.get(row["line_no"])
        if update is not None and update.exclude:
            continue

        suggested_category_id = uuid.UUID(row["suggested_category_id"])
        category_id = suggested_category_id
        if update is not None and update.category_id is not None:
            category_id = update.category_id

        merchant_normalized = row["merchant_normalized"]

        transaction = Transaction(
            user_id=user_id,
            category_id=category_id,
            amount=row["amount"],
            merchant_raw=row["merchant_raw"],
            merchant_normalized=merchant_normalized,
            transaction_date=date.fromisoformat(row["transaction_date"]),
            source=TransactionSource.import_,
            import_session_id=session.id,
            external_ref=row.get("external_ref"),
        )
        await uow.transactions.add(transaction)
        created.append(transaction)

        if category_id != suggested_category_id:
            await upsert_user_rule(uow, user_id, merchant_normalized, category_id)

    session.status = ImportSessionStatus.confirmed
    session.confirmed_at = func.now()
    await uow.commit()
    return created


async def delete_import_session(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, session_id: uuid.UUID
) -> None:
    session = await get_import_session(uow, user_id, session_id)
    if session.status == ImportSessionStatus.confirmed:
        raise SessionAlreadyConfirmedError()
    await uow.import_sessions.delete(session)
    await uow.commit()
