import uuid

from sqlalchemy import func

from app.exceptions import CategoryIsSystemError, NotFoundError
from app.models import Category
from app.unit_of_work import AbstractUnitOfWork


async def list_categories(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, include_deleted: bool = False
) -> list[Category]:
    return await uow.categories.list_visible(user_id, include_deleted=include_deleted)


async def create_category(
    uow: AbstractUnitOfWork,
    user_id: uuid.UUID,
    name: str,
    icon: str | None = None,
    color: str | None = None,
) -> Category:
    category = Category(user_id=user_id, name=name, icon=icon, color=color)
    await uow.categories.add(category)
    await uow.commit()
    return category


async def get_category(uow: AbstractUnitOfWork, user_id: uuid.UUID, category_id: uuid.UUID) -> Category:
    category = await uow.categories.get_owned(category_id, user_id)
    if category is None:
        raise NotFoundError("Категория не найдена")
    return category


async def update_category(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, category_id: uuid.UUID, updates: dict
) -> Category:
    category = await get_category(uow, user_id, category_id)
    for field, value in updates.items():
        setattr(category, field, value)
    await uow.commit()
    return category


async def delete_category(uow: AbstractUnitOfWork, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = await get_category(uow, user_id, category_id)
    if category.is_system:
        raise CategoryIsSystemError()
    category.deleted_at = func.now()
    await uow.commit()
