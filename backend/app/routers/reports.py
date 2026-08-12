from datetime import date

from fastapi import APIRouter, Depends

from app.deps import get_current_user, get_uow
from app.models import User
from app.services import report_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/by-category")
async def report_by_category(
    date_from: date,
    date_to: date,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> dict:
    rows = await report_service.report_by_category(uow, current_user.id, date_from, date_to)

    data = [
        {
            "category_id": str(row.category_id),
            "category_name": row.category_name,
            "total": row.total,
            "count": row.count,
        }
        for row in rows
    ]
    total_overall = sum(row["total"] for row in data)

    return {
        "data": data,
        "meta": {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_overall": total_overall,
        },
    }
