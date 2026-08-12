import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from app.deps import get_current_user, get_uow
from app.errors import not_found
from app.exceptions import NotFoundError
from app.models import TransactionSource, User
from app.repositories.transactions import TransactionFilters
from app.schemas import (
    PaginationMeta,
    TransactionCreate,
    TransactionDataResponse,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdate,
)
from app.services import transaction_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: uuid.UUID | None = None,
    source: TransactionSource | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    include_deleted: bool = False,
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
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionDataResponse:
    try:
        transaction = await transaction_service.create_transaction(
            uow,
            current_user.id,
            amount=payload.amount,
            category_id=payload.category_id,
            merchant_raw=payload.merchant_raw,
            note=payload.note,
            transaction_date=payload.transaction_date,
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
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TransactionDataResponse:
    updates = payload.model_dump(exclude_unset=True)
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
