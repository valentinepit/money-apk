"""Unit of Work — граница транзакции для сервисного слоя.

Сервис получает UnitOfWork (через FastAPI-зависимость get_uow либо напрямую
в тестах) и работает только с ним и репозиториями, которые он предоставляет.
UoW не коммитит ничего сам — сервис явно вызывает await uow.commit(), когда
операция должна быть сохранена. Если __aexit__ достигнут без commit(),
изменения откатываются (rollback), что оставляет сессию/транзакцию в чистом
состоянии в любом случае (в т.ч. при исключении).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.repositories.categories import AbstractCategoryRepository, SqlAlchemyCategoryRepository
from app.repositories.categorization_rules import (
    AbstractCategorizationRuleRepository,
    SqlAlchemyCategorizationRuleRepository,
)
from app.repositories.transactions import AbstractTransactionRepository, SqlAlchemyTransactionRepository
from app.repositories.users import AbstractUserRepository, SqlAlchemyUserRepository


class AbstractUnitOfWork(ABC):
    categories: AbstractCategoryRepository
    transactions: AbstractTransactionRepository
    categorization_rules: AbstractCategorizationRuleRepository
    users: AbstractUserRepository

    async def __aenter__(self) -> "AbstractUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.rollback()

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """Реализация на асинхронном SQLAlchemy.

    По умолчанию сама создаёт AsyncSession из фабрики (боевой режим — одна
    сессия на HTTP-запрос через зависимость get_uow). В тестах можно передать
    уже открытую session= — тогда UoW не создаёт и не закрывает сессию сам,
    что позволяет тестам использовать общую SAVEPOINT-транзакцию для изоляции
    (см. tests/conftest.py).
    """

    def __init__(self, session_factory=AsyncSessionLocal, session: AsyncSession | None = None) -> None:
        self._session_factory = session_factory
        self._external_session = session

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self.session: AsyncSession = self._external_session or self._session_factory()
        self.categories = SqlAlchemyCategoryRepository(self.session)
        self.transactions = SqlAlchemyTransactionRepository(self.session)
        self.categorization_rules = SqlAlchemyCategorizationRuleRepository(self.session)
        self.users = SqlAlchemyUserRepository(self.session)
        return await super().__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await super().__aexit__(exc_type, exc, tb)
        if self._external_session is None:
            await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
