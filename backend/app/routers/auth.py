from typing import Annotated

from fastapi import APIRouter, Depends, Form

from app.deps import get_current_user, get_uow
from app.errors import unauthorized
from app.exceptions import InvalidCredentialsError
from app.models import User
from app.schemas.requests import LoginRequest
from app.schemas.responses import TokenDataResponse, TokenResponse, UserDataResponse, UserOut
from app.security import create_access_token
from app.services import auth_service
from app.unit_of_work import AbstractUnitOfWork

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenDataResponse)
async def login(
    payload: Annotated[LoginRequest, Form()],
    uow: AbstractUnitOfWork = Depends(get_uow),
) -> TokenDataResponse:
    try:
        user = await auth_service.authenticate(uow, payload.email, payload.password)
    except InvalidCredentialsError as exc:
        raise unauthorized(exc.message) from exc

    token = create_access_token(subject=str(user.id))
    return TokenDataResponse(data=TokenResponse(access_token=token))


@router.get("/me", response_model=UserDataResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserDataResponse:
    return UserDataResponse(data=UserOut.model_validate(current_user))
