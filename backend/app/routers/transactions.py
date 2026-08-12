import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Category, CategorizationRule, RuleSource, Transaction, TransactionSource, User
from app.normalization import normalize_merchant
from app.errors import not_found
from app.schemas import TransactionCreate, TransactionOut, TransactionUpdate

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


def _get_default_category(db: Session) -> Category:
    category = db.scalars(select(Category).where(Category.is_system.is_(True))).one_or_none()
    if category is None:
        raise not_found("Системная категория по умолчанию не сидирована")
    return category


def _get_owned_transaction(db: Session, current_user: User, transaction_id: uuid.UUID) -> Transaction:
    stmt = select(Transaction).where(
        Transaction.id == transaction_id, Transaction.user_id == current_user.id
    )
    transaction = db.scalars(stmt).one_or_none()
    if transaction is None:
        raise not_found("Транзакция не найдена")
    return transaction


def _upsert_user_rule(db: Session, current_user: User, merchant_normalized: str, category_id: uuid.UUID) -> None:
    if not merchant_normalized:
        return

    stmt = select(CategorizationRule).where(
        CategorizationRule.user_id == current_user.id,
        CategorizationRule.merchant_pattern == merchant_normalized,
    )
    rule = db.scalars(stmt).one_or_none()
    if rule is None:
        rule = CategorizationRule(
            user_id=current_user.id,
            merchant_pattern=merchant_normalized,
            category_id=category_id,
            source=RuleSource.user_rule,
        )
        db.add(rule)
    else:
        rule.category_id = category_id


@router.get("")
def list_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: uuid.UUID | None = None,
    source: TransactionSource | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    include_deleted: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Transaction).where(Transaction.user_id == current_user.id)
    if not include_deleted:
        stmt = stmt.where(Transaction.deleted_at.is_(None))
    if date_from is not None:
        stmt = stmt.where(Transaction.transaction_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Transaction.transaction_date <= date_to)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if source is not None:
        stmt = stmt.where(Transaction.source == source)
    if q:
        stmt = stmt.where(Transaction.merchant_raw.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(Transaction.transaction_date.desc()).offset((page - 1) * per_page).limit(per_page)
    transactions = db.scalars(stmt).all()

    total_pages = math.ceil(total / per_page) if total else 0

    return {
        "data": [TransactionOut.model_validate(t).model_dump(mode="json") for t in transactions],
        "meta": {"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
    }


@router.post("", status_code=201)
def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.category_id is not None:
        category_id = payload.category_id
    else:
        category_id = _get_default_category(db).id

    merchant_raw = payload.merchant_raw or ""
    transaction = Transaction(
        user_id=current_user.id,
        category_id=category_id,
        amount=payload.amount,
        merchant_raw=merchant_raw,
        merchant_normalized=normalize_merchant(merchant_raw),
        note=payload.note,
        transaction_date=payload.transaction_date,
        source=TransactionSource.manual,
    )
    db.add(transaction)
    db.commit()
    return {"data": TransactionOut.model_validate(transaction).model_dump(mode="json")}


@router.get("/{transaction_id}")
def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    transaction = _get_owned_transaction(db, current_user, transaction_id)
    return {"data": TransactionOut.model_validate(transaction).model_dump(mode="json")}


@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    transaction = _get_owned_transaction(db, current_user, transaction_id)
    updates = payload.model_dump(exclude_unset=True)

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
        _upsert_user_rule(db, current_user, transaction.merchant_normalized, transaction.category_id)

    db.commit()
    return {"data": TransactionOut.model_validate(transaction).model_dump(mode="json")}


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    transaction = _get_owned_transaction(db, current_user, transaction_id)
    transaction.deleted_at = func.now()
    db.commit()
    return Response(status_code=204)
