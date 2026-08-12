import uuid
from datetime import date

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    icon: str | None
    color: str | None
    is_system: bool

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    amount: float
    category_id: uuid.UUID | None = None
    merchant_raw: str | None = None
    note: str | None = None
    transaction_date: date


class TransactionUpdate(BaseModel):
    amount: float | None = None
    category_id: uuid.UUID | None = None
    merchant_raw: str | None = None
    note: str | None = None
    transaction_date: date | None = None


class TransactionOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    amount: float
    currency: str
    merchant_raw: str
    merchant_normalized: str
    note: str | None
    transaction_date: date
    source: str
    import_session_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
