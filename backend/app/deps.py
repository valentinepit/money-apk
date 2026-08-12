import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import unauthorized
from app.models import User
from app.security import decode_access_token

# tokenUrl указывает на реальный эндпоинт логина — используется только для описания схемы в OpenAPI.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    db: Session = Depends(get_db),
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

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized("Пользователь не найден")

    return user
