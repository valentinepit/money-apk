from fastapi import APIRouter, Depends

from app.deps import get_current_user, get_uow
from app.errors import unauthorized
from app.exceptions import InvalidCredentialsError
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token
from app.services import auth_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
async def login(credentials: LoginRequest, uow: AbstractUnitOfWork = Depends(get_uow)) -> dict:
    try:
        user = await auth_service.authenticate(uow, credentials.email, credentials.password)
    except InvalidCredentialsError as exc:
        raise unauthorized(exc.message) from exc

    token = create_access_token(subject=str(user.id))
    return {"data": TokenResponse(access_token=token).model_dump()}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {"data": UserOut.model_validate(current_user).model_dump(mode="json")}
