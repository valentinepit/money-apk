import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category


class AbstractCategoryRepository(ABC):
    @abstractmethod
    async def add(self, category: Category) -> None: ...

    @abstractmethod
    async def get(self, category_id: uuid.UUID) -> Category | None: ...

    @abstractmethod
    async def get_owned(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        """Категория, видимая пользователю: своя либо системная (user_id is null)."""
        ...

    @abstractmethod
    async def list_visible(self, user_id: uuid.UUID, include_deleted: bool = False) -> list[Category]: ...

    @abstractmethod
    async def get_default(self) -> Category | None:
        """Системная категория по умолчанию ("Другое")."""
        ...


class SqlAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, category: Category) -> None:
        self.session.add(category)

    async def get(self, category_id: uuid.UUID) -> Category | None:
        return await self.session.get(Category, category_id)

    async def get_owned(self, category_id: uuid.UUID, user_id: uuid.UUID) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def list_visible(self, user_id: uuid.UUID, include_deleted: bool = False) -> list[Category]:
        stmt = select(Category).where((Category.user_id == user_id) | (Category.user_id.is_(None)))
        if not include_deleted:
            stmt = stmt.where(Category.deleted_at.is_(None))
        stmt = stmt.order_by(Category.name)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_default(self) -> Category | None:
        result = await self.session.scalars(select(Category).where(Category.is_system.is_(True)))
        return result.one_or_none()
