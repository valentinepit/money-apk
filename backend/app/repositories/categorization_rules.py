import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CategorizationRule


class AbstractCategorizationRuleRepository(ABC):
    @abstractmethod
    async def add(self, rule: CategorizationRule) -> None: ...

    @abstractmethod
    async def get_user_rule(
        self, user_id: uuid.UUID, merchant_pattern: str
    ) -> CategorizationRule | None: ...


class SqlAlchemyCategorizationRuleRepository(AbstractCategorizationRuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, rule: CategorizationRule) -> None:
        self.session.add(rule)

    async def get_user_rule(
        self, user_id: uuid.UUID, merchant_pattern: str
    ) -> CategorizationRule | None:
        stmt = select(CategorizationRule).where(
            CategorizationRule.user_id == user_id,
            CategorizationRule.merchant_pattern == merchant_pattern,
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()
