import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Transaction, TransactionSource


@dataclass
class TransactionFilters:
    date_from: date | None = None
    date_to: date | None = None
    category_id: uuid.UUID | None = None
    source: TransactionSource | None = None
    q: str | None = None
    include_deleted: bool = False


@dataclass
class CategoryReportRow:
    category_id: uuid.UUID
    category_name: str
    total: float
    count: int


class AbstractTransactionRepository(ABC):
    @abstractmethod
    async def add(self, transaction: Transaction) -> None: ...

    @abstractmethod
    async def get(self, transaction_id: uuid.UUID) -> Transaction | None: ...

    @abstractmethod
    async def get_owned(self, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Transaction | None: ...

    @abstractmethod
    async def list_page(
        self, user_id: uuid.UUID, filters: TransactionFilters, page: int, per_page: int
    ) -> tuple[list[Transaction], int]:
        """Возвращает (страница транзакций, общее количество без учёта пагинации)."""
        ...

    @abstractmethod
    async def report_by_category(
        self, user_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[CategoryReportRow]: ...


class SqlAlchemyTransactionRepository(AbstractTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, transaction: Transaction) -> None:
        self.session.add(transaction)

    async def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        return await self.session.get(Transaction, transaction_id)

    async def get_owned(self, transaction_id: uuid.UUID, user_id: uuid.UUID) -> Transaction | None:
        stmt = select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user_id
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    def _filtered_stmt(self, user_id: uuid.UUID, filters: TransactionFilters):
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if not filters.include_deleted:
            stmt = stmt.where(Transaction.deleted_at.is_(None))
        if filters.date_from is not None:
            stmt = stmt.where(Transaction.transaction_date >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(Transaction.transaction_date <= filters.date_to)
        if filters.category_id is not None:
            stmt = stmt.where(Transaction.category_id == filters.category_id)
        if filters.source is not None:
            stmt = stmt.where(Transaction.source == filters.source)
        if filters.q:
            stmt = stmt.where(Transaction.merchant_raw.ilike(f"%{filters.q}%"))
        return stmt

    async def list_page(
        self, user_id: uuid.UUID, filters: TransactionFilters, page: int, per_page: int
    ) -> tuple[list[Transaction], int]:
        base_stmt = self._filtered_stmt(user_id, filters)

        total = await self.session.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0

        page_stmt = (
            base_stmt.order_by(Transaction.transaction_date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.session.scalars(page_stmt)
        return list(result.all()), total

    async def report_by_category(
        self, user_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[CategoryReportRow]:
        stmt = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .join(Category, Category.id == Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.deleted_at.is_(None),
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        result = await self.session.execute(stmt)
        return [
            CategoryReportRow(
                category_id=row.category_id,
                category_name=row.category_name,
                total=float(row.total),
                count=row.count,
            )
            for row in result.all()
        ]
