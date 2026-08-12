from sqlalchemy import select

from app.config import Settings
from app.models import Category, User
from app.seed import run_seed


async def test_run_seed_creates_user_and_default_category(uow, db_session):
    settings = Settings(admin_email="owner@example.com", admin_password="owner-pass")

    await run_seed(uow, settings)

    user = (await db_session.scalars(select(User).where(User.email == "owner@example.com"))).one()
    category = (await db_session.scalars(select(Category).where(Category.is_system.is_(True)))).one()

    assert user.email == "owner@example.com"
    assert category.name == Category.DEFAULT_CATEGORY_NAME


async def test_run_seed_is_idempotent(uow, db_session):
    settings = Settings(admin_email="owner2@example.com", admin_password="owner-pass")

    await run_seed(uow, settings)
    await run_seed(uow, settings)

    users = (
        await db_session.scalars(select(User).where(User.email == "owner2@example.com"))
    ).all()
    system_categories = (
        await db_session.scalars(select(Category).where(Category.is_system.is_(True)))
    ).all()

    assert len(users) == 1
    assert len(system_categories) == 1
