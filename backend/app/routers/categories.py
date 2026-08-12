import uuid

from fastapi import APIRouter, Depends, Response

from app.deps import get_current_user, get_uow
from app.errors import conflict, not_found
from app.exceptions import CategoryIsSystemError, NotFoundError
from app.models import User
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import category_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("")
async def list_categories(
    include_deleted: bool = False,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict:
    categories = await category_service.list_categories(uow, current_user.id, include_deleted)
    return {"data": [CategoryOut.model_validate(c).model_dump(mode="json") for c in categories]}


@router.post("", status_code=201)
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict:
    category = await category_service.create_category(
        uow, current_user.id, name=payload.name, icon=payload.icon, color=payload.color
    )
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.get("/{category_id}")
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict:
    try:
        category = await category_service.get_category(uow, current_user.id, category_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.patch("/{category_id}")
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict:
    updates = payload.model_dump(exclude_unset=True)
    try:
        category = await category_service.update_category(uow, current_user.id, category_id, updates)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> Response:
    try:
        await category_service.delete_category(uow, current_user.id, category_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    except CategoryIsSystemError as exc:
        raise conflict(exc.code, exc.message) from exc
    return Response(status_code=204)
