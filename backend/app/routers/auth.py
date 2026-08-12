from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import unauthorized
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == credentials.email).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise unauthorized("Неверный email или пароль")

    token = create_access_token(subject=str(user.id))
    return {"data": TokenResponse(access_token=token).model_dump()}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return {"data": UserOut.model_validate(current_user).model_dump(mode="json")}
