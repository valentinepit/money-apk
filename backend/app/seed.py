"""Сид единственного пользователя и системной категории по умолчанию.

Приложение одно-пользовательское (см. docs/plan.md) — регистрации нет,
учётная запись создаётся здесь из переменных окружения ADMIN_EMAIL/ADMIN_PASSWORD.
Скрипт идемпотентен: повторный запуск не создаёт дублей.
"""

import asyncio

from app.config import Settings, get_settings
from app.models import Category, User
from app.security import hash_password
from app.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork


async def run_seed(uow: AbstractUnitOfWork, settings: Settings) -> User:
    user = await uow.users.get_by_email(settings.admin_email)
    if user is None:
        user = User(email=settings.admin_email, password_hash=hash_password(settings.admin_password))
        await uow.users.add(user)
        await uow.session.flush()

    default_category = await uow.categories.get_default()
    if default_category is None:
        default_category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
        await uow.categories.add(default_category)

    await uow.commit()
    return user


async def _run_seed_with_new_uow() -> User:
    settings = get_settings()
    async with SqlAlchemyUnitOfWork() as uow:
        return await run_seed(uow, settings)


def main() -> None:
    user = asyncio.run(_run_seed_with_new_uow())
    print(f"Сид готов: пользователь {user.email}")


if __name__ == "__main__":
    main()
