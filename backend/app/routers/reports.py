from datetime import date

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user, get_uow
from app.models import User
from app.schemas.responses import ReportListResponse, ReportMeta, ReportRowOut
from app.services import report_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/by-category", response_model=ReportListResponse)
async def report_by_category(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> ReportListResponse:
    rows = await report_service.report_by_category(uow, current_user.id, date_from, date_to)

    data = [
        ReportRowOut(
            category_id=row.category_id,
            category_name=row.category_name,
            total=row.total,
            count=row.count,
        )
        for row in rows
    ]
    total_overall = sum(row.total for row in data)

    return ReportListResponse(
        data=data,
        meta=ReportMeta(date_from=date_from, date_to=date_to, total_overall=total_overall),
    )
