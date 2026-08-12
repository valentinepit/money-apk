import uuid

from fastapi import APIRouter, Depends, Form, Query, Response

from app.deps import get_current_user, get_uow
from app.errors import conflict, not_found
from app.exceptions import CategoryIsSystemError, NotFoundError
from app.models import User
from app.schemas import CategoryDataResponse, CategoryListResponse, CategoryOut
from app.services import category_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    include_deleted: bool = Query(False),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> CategoryListResponse:
    categories = await category_service.list_categories(uow, current_user.id, include_deleted)
    return CategoryListResponse(data=[CategoryOut.model_validate(c) for c in categories])


@router.post("", status_code=201, response_model=CategoryDataResponse)
async def create_category(
    name: str = Form(...),
    icon: str | None = Form(None),
    color: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> CategoryDataResponse:
    category = await category_service.create_category(uow, current_user.id, name=name, icon=icon, color=color)
    return CategoryDataResponse(data=CategoryOut.model_validate(category))


@router.get("/{category_id}", response_model=CategoryDataResponse)
async def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> CategoryDataResponse:
    try:
        category = await category_service.get_category(uow, current_user.id, category_id)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return CategoryDataResponse(data=CategoryOut.model_validate(category))


@router.patch("/{category_id}", response_model=CategoryDataResponse)
async def update_category(
    category_id: uuid.UUID,
    name: str | None = Form(None),
    icon: str | None = Form(None),
    color: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> CategoryDataResponse:
    # Form-поля не различают "поле не передано" и "поле передано как null" —
    # трактуем непереданное (None) как "не менять" (см. правило проекта:
    # POST/PATCH — через Form, а не Pydantic-body с exclude_unset).
    updates = {"name": name, "icon": icon, "color": color}
    updates = {field: value for field, value in updates.items() if value is not None}
    try:
        category = await category_service.update_category(uow, current_user.id, category_id, updates)
    except NotFoundError as exc:
        raise not_found(exc.message) from exc
    return CategoryDataResponse(data=CategoryOut.model_validate(category))


@router.delete("/{category_id}", status_code=204, response_model=None)
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
