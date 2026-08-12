import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import conflict, not_found
from app.models import Category, User
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


def _get_owned_category(db: Session, current_user: User, category_id: uuid.UUID) -> Category:
    """Категория принадлежит пользователю либо системная (user_id is null)."""
    stmt = select(Category).where(
        Category.id == category_id,
        (Category.user_id == current_user.id) | (Category.user_id.is_(None)),
    )
    category = db.scalars(stmt).one_or_none()
    if category is None:
        raise not_found("Категория не найдена")
    return category


@router.get("")
def list_categories(
    include_deleted: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Category).where(
        (Category.user_id == current_user.id) | (Category.user_id.is_(None))
    )
    if not include_deleted:
        stmt = stmt.where(Category.deleted_at.is_(None))
    stmt = stmt.order_by(Category.name)

    categories = db.scalars(stmt).all()
    return {"data": [CategoryOut.model_validate(c).model_dump(mode="json") for c in categories]}


@router.post("", status_code=201)
def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    category = Category(
        user_id=current_user.id, name=payload.name, icon=payload.icon, color=payload.color
    )
    db.add(category)
    db.commit()
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.get("/{category_id}")
def get_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    category = _get_owned_category(db, current_user, category_id)
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.patch("/{category_id}")
def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    category = _get_owned_category(db, current_user, category_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(category, field, value)

    db.commit()
    return {"data": CategoryOut.model_validate(category).model_dump(mode="json")}


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    category = _get_owned_category(db, current_user, category_id)

    if category.is_system:
        raise conflict("category_is_system", "Системную категорию нельзя удалить")

    from sqlalchemy import func

    category.deleted_at = func.now()
    db.commit()
    return Response(status_code=204)
