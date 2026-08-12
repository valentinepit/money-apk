import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.errors import unauthorized
from app.exceptions import NotFoundError
from app.models import User
from app.security import decode_access_token
from app.services import auth_service
from app.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork

# tokenUrl указывает на реальный эндпоинт логина — используется только для описания схемы в OpenAPI.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_uow() -> AsyncGenerator[AbstractUnitOfWork, None]:
    """UnitOfWork на весь запрос: один и тот же экземпляр возвращается всем
    Depends() в рамках одного запроса (FastAPI кеширует зависимости per-request)."""
    uow = SqlAlchemyUnitOfWork()
    async with uow:
        yield uow


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> User:
    if not token:
        raise unauthorized("Отсутствует токен авторизации")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise unauthorized("Невалидный или просроченный токен") from exc

    try:
        user_id = uuid.UUID(payload.subject)
    except (ValueError, TypeError) as exc:
        raise unauthorized("Невалидный токен") from exc

    try:
        return await auth_service.get_user_by_id(uow, user_id)
    except NotFoundError as exc:
        raise unauthorized("Пользователь не найден") from exc
