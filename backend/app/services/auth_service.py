import uuid

from app.exceptions import InvalidCredentialsError, NotFoundError
from app.models import User
from app.security import verify_password
from app.unit_of_work import AbstractUnitOfWork


async def authenticate(uow: AbstractUnitOfWork, email: str, password: str) -> User:
    user = await uow.users.get_by_email(email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


async def get_user_by_id(uow: AbstractUnitOfWork, user_id: uuid.UUID) -> User:
    user = await uow.users.get(user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")
    return user
