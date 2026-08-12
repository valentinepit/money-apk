import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func

from app.exceptions import NotFoundError
from app.models import CategorizationRule, RuleSource, Transaction, TransactionSource
from app.normalization import normalize_merchant
from app.repositories.transactions import TransactionFilters
from app.unit_of_work import AbstractUnitOfWork


@dataclass
class TransactionPage:
    items: list[Transaction]
    total: int


async def _get_default_category_id(uow: AbstractUnitOfWork) -> uuid.UUID:
    category = await uow.categories.get_default()
    if category is None:
        raise NotFoundError("Системная категория по умолчанию не сидирована")
    return category.id


async def list_transactions(
    uow: AbstractUnitOfWork,
    user_id: uuid.UUID,
    filters: TransactionFilters,
    page: int,
    per_page: int,
) -> TransactionPage:
    items, total = await uow.transactions.list_page(user_id, filters, page, per_page)
    return TransactionPage(items=items, total=total)


async def create_transaction(
    uow: AbstractUnitOfWork,
    user_id: uuid.UUID,
    amount: float,
    category_id: uuid.UUID | None,
    merchant_raw: str | None,
    note: str | None,
    transaction_date: date,
) -> Transaction:
    resolved_category_id = (
        category_id if category_id is not None else await _get_default_category_id(uow)
    )
    merchant_raw = merchant_raw or ""
    transaction = Transaction(
        user_id=user_id,
        category_id=resolved_category_id,
        amount=amount,
        merchant_raw=merchant_raw,
        merchant_normalized=normalize_merchant(merchant_raw),
        note=note,
        transaction_date=transaction_date,
        source=TransactionSource.manual,
    )
    await uow.transactions.add(transaction)
    await uow.commit()
    return transaction


async def get_transaction(uow: AbstractUnitOfWork, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction:
    transaction = await uow.transactions.get_owned(transaction_id, user_id)
    if transaction is None:
        raise NotFoundError("Транзакция не найдена")
    return transaction


async def _upsert_user_rule(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, merchant_normalized: str, category_id: uuid.UUID
) -> None:
    if not merchant_normalized:
        return

    rule = await uow.categorization_rules.get_user_rule(user_id, merchant_normalized)
    if rule is None:
        rule = CategorizationRule(
            user_id=user_id,
            merchant_pattern=merchant_normalized,
            category_id=category_id,
            source=RuleSource.user_rule,
        )
        await uow.categorization_rules.add(rule)
    else:
        rule.category_id = category_id


async def update_transaction(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, transaction_id: uuid.UUID, updates: dict
) -> Transaction:
    transaction = await get_transaction(uow, user_id, transaction_id)

    category_changed = "category_id" in updates and updates["category_id"] != transaction.category_id

    if "merchant_raw" in updates:
        transaction.merchant_raw = updates["merchant_raw"] or ""
        transaction.merchant_normalized = normalize_merchant(transaction.merchant_raw)
    for field in ("amount", "note", "transaction_date"):
        if field in updates:
            setattr(transaction, field, updates[field])
    if "category_id" in updates:
        transaction.category_id = updates["category_id"]

    if category_changed:
        await _upsert_user_rule(uow, user_id, transaction.merchant_normalized, transaction.category_id)

    await uow.commit()
    return transaction


async def delete_transaction(uow: AbstractUnitOfWork, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
    transaction = await get_transaction(uow, user_id, transaction_id)
    transaction.deleted_at = func.now()
    await uow.commit()
