import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportSession


class AbstractImportSessionRepository(ABC):
    @abstractmethod
    async def add(self, import_session: ImportSession) -> None: ...

    @abstractmethod
    async def get_owned(
        self, import_session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ImportSession | None: ...

    @abstractmethod
    async def list_owned(self, user_id: uuid.UUID) -> list[ImportSession]: ...

    @abstractmethod
    async def delete(self, import_session: ImportSession) -> None: ...


class SqlAlchemyImportSessionRepository(AbstractImportSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, import_session: ImportSession) -> None:
        self.session.add(import_session)

    async def get_owned(
        self, import_session_id: uuid.UUID, user_id: uuid.UUID
    ) -> ImportSession | None:
        stmt = select(ImportSession).where(
            ImportSession.id == import_session_id, ImportSession.user_id == user_id
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def list_owned(self, user_id: uuid.UUID) -> list[ImportSession]:
        stmt = (
            select(ImportSession)
            .where(ImportSession.user_id == user_id)
            .order_by(ImportSession.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def delete(self, import_session: ImportSession) -> None:
        await self.session.delete(import_session)
