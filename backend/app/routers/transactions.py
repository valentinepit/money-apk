import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Response

from app.deps import get_current_user, get_uow
from app.errors import not_found
from app.exceptions import NotFoundError
from app.models import TransactionSource, User
from app.repositories.transactions import TransactionFilters
from app.schemas import (
    PaginationMeta,
    TransactionDataResponse,
    TransactionListResponse,
    TransactionOut,
)
from app.services import transaction_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    source: TransactionSource | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    include_deleted: bool = Query(False),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionListResponse:
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        source=source,
        q=q,
        include_deleted=include_deleted,
    )
    result = await transaction_service.list_transactions(uow, current_user.id, filters, page, per_page)

    total_pages = math.ceil(result.total / per_page) if result.total else 0
    return TransactionListResponse(
        data=[TransactionOut.model_validate(t) for t in result.items],
        meta=PaginationMeta(total=result.total, page=page, per_page=per_page, total_pages=total_pages),
    )


@router.post("", status_code=201, response_model=TransactionDataResponse)
async def create_transaction(
    amount: float = Form(...),
    category_id: uuid.UUID | None = Form(None),
    merchant_raw: str | None = Form(None),
    note: str | None = Form(None),
    transaction_date: date = Form(...),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionDataResponse:
    try:
        transaction = await transaction_service.create_transaction(
            uow,
            current_user.id,
            amount=amount,
            category_id=category_id,
            merchant_raw=merchant_raw,
            note=note,
            transaction_date=transaction_date,
        )
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return TransactionDataResponse(data=TransactionOut.model_validate(transaction))


@router.get("/{transaction_id}", response_model=TransactionDataResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionDataResponse:
    try:
        transaction = await transaction_service.get_transaction(uow, current_user.id, transaction_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return TransactionDataResponse(data=TransactionOut.model_validate(transaction))


@router.patch("/{transaction_id}", response_model=TransactionDataResponse)
async def update_transaction(
    transaction_id: uuid.UUID,
    amount: float | None = Form(None),
    category_id: uuid.UUID | None = Form(None),
    merchant_raw: str | None = Form(None),
    note: str | None = Form(None),
    transaction_date: date | None = Form(None),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionDataResponse:
    # Form-поля не различают "поле не передано" и "поле передано как null" —
    # непереданное (None) трактуем как "не менять" (см. правило проекта:
    # POST/PATCH — через Form, а не Pydantic-body с exclude_unset).
    updates = {
        "amount": amount,
        "category_id": category_id,
        "merchant_raw": merchant_raw,
        "note": note,
        "transaction_date": transaction_date,
    }
    updates = {field: value for field, value in updates.items() if value is not None}
    try:
        transaction = await transaction_service.update_transaction(
            uow, current_user.id, transaction_id, updates
        )
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return TransactionDataResponse(data=TransactionOut.model_validate(transaction))


@router.delete("/{transaction_id}", status_code=204, response_model=None)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Response:
    try:
        await transaction_service.delete_transaction(uow, current_user.id, transaction_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return Response(status_code=204)
