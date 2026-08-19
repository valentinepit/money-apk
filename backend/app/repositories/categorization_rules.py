import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CategorizationRule, RuleSource


class AbstractCategorizationRuleRepository(ABC):
    @abstractmethod
    async def add(self, rule: CategorizationRule) -> None: ...

    @abstractmethod
    async def get_user_rule(
        self, user_id: uuid.UUID, merchant_pattern: str
    ) -> CategorizationRule | None: ...

    @abstractmethod
    async def list_visible(
        self, user_id: uuid.UUID, source: RuleSource | None = None
    ) -> list[CategorizationRule]:
        """Правила, видимые пользователю: свои личные + общие системные (user_id is null)."""
        ...

    @abstractmethod
    async def get_visible(self, rule_id: uuid.UUID, user_id: uuid.UUID) -> CategorizationRule | None:
        """Правило, видимое пользователю: своё либо системное (user_id is null)."""
        ...

    @abstractmethod
    async def get_matching_rule(
        self, user_id: uuid.UUID, merchant_pattern: str
    ) -> CategorizationRule | None:
        """Правило для автокатегоризации при импорте: точное совпадение по
        merchant_pattern, личное правило пользователя приоритетнее системного
        словаря (см. docs/plan.md, "Автокатегоризация...")."""
        ...

    @abstractmethod
    async def delete(self, rule: CategorizationRule) -> None: ...


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

    async def list_visible(
        self, user_id: uuid.UUID, source: RuleSource | None = None
    ) -> list[CategorizationRule]:
        stmt = select(CategorizationRule).where(
            (CategorizationRule.user_id == user_id) | (CategorizationRule.user_id.is_(None))
        )
        if source is not None:
            stmt = stmt.where(CategorizationRule.source == source)
        stmt = stmt.order_by(CategorizationRule.merchant_pattern)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_visible(self, rule_id: uuid.UUID, user_id: uuid.UUID) -> CategorizationRule | None:
        stmt = select(CategorizationRule).where(
            CategorizationRule.id == rule_id,
            (CategorizationRule.user_id == user_id) | (CategorizationRule.user_id.is_(None)),
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def get_matching_rule(
        self, user_id: uuid.UUID, merchant_pattern: str
    ) -> CategorizationRule | None:
        stmt = (
            select(CategorizationRule)
            .where(
                CategorizationRule.merchant_pattern == merchant_pattern,
                (CategorizationRule.user_id == user_id) | (CategorizationRule.user_id.is_(None)),
            )
            # user_id IS NULL -> False(=0) для личного правила, True(=1) для
            # системного — личное правило пользователя сортируется первым.
            .order_by(CategorizationRule.user_id.is_(None))
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def delete(self, rule: CategorizationRule) -> None:
        await self.session.delete(rule)
