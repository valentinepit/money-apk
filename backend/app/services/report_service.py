import uuid
from datetime import date

from app.repositories.transactions import CategoryReportRow
from app.unit_of_work import AbstractUnitOfWork


async def report_by_category(
    uow: AbstractUnitOfWork, user_id: uuid.UUID, date_from: date, date_to: date
) -> list[CategoryReportRow]:
    return await uow.transactions.report_by_category(user_id, date_from, date_to)
