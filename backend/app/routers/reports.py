from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Category, Transaction, User

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/by-category")
def report_by_category(
    date_from: date,
    date_to: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.deleted_at.is_(None),
            Transaction.transaction_date >= date_from,
            Transaction.transaction_date <= date_to,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
    )
    rows = db.execute(stmt).all()

    data = [
        {
            "category_id": str(row.category_id),
            "category_name": row.category_name,
            "total": float(row.total),
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
