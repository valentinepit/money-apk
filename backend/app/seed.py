"""Сид единственного пользователя, счёта по умолчанию и системной категории.

Приложение одно-пользовательское (см. docs/plan.md) — регистрации нет,
учётная запись создаётся здесь из переменных окружения ADMIN_EMAIL/ADMIN_PASSWORD.
Скрипт идемпотентен: повторный запуск не создаёт дублей.
"""

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models import Account, Category, User
from app.security import hash_password

DEFAULT_ACCOUNT_NAME = "Основной счёт"


def run_seed(db: Session, settings: Settings) -> User:
    user = db.query(User).filter(User.email == settings.admin_email).one_or_none()
    if user is None:
        user = User(email=settings.admin_email, password_hash=hash_password(settings.admin_password))
        db.add(user)
        db.flush()

    account = db.query(Account).filter(Account.user_id == user.id).one_or_none()
    if account is None:
        account = Account(user_id=user.id, name=DEFAULT_ACCOUNT_NAME, currency="EUR")
        db.add(account)

    default_category = db.query(Category).filter(Category.is_system.is_(True)).one_or_none()
    if default_category is None:
        default_category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
        db.add(default_category)

    db.commit()
    return user


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        user = run_seed(db, settings)
        print(f"Сид готов: пользователь {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
