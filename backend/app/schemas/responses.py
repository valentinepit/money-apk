"""Схемы ответов (``*Out``, конверты ``*Response``).

Эти классы используются в ``response_model=`` роутеров — FastAPI валидирует
и документирует (OpenAPI) реальную форму ответа, а не просто ``dict``.
Схемы тел запросов (POST/PATCH) — в соседнем модуле ``app/schemas/requests.py``.
"""

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    icon: str | None
    color: str | None
    is_system: bool

    model_config = {"from_attributes": True}


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


class ReportRowOut(BaseModel):
    category_id: uuid.UUID
    category_name: str
    total: float
    count: int


class ReportMeta(BaseModel):
    date_from: date
    date_to: date
    total_overall: float


class CategorizationRuleOut(BaseModel):
    id: uuid.UUID
    merchant_pattern: str
    category_id: uuid.UUID
    source: str

    model_config = {"from_attributes": True}


class TokenDataResponse(BaseModel):
    data: TokenResponse


class UserDataResponse(BaseModel):
    data: UserOut


class CategoryDataResponse(BaseModel):
    data: CategoryOut


class CategoryListResponse(BaseModel):
    data: list[CategoryOut]


class TransactionDataResponse(BaseModel):
    data: TransactionOut


class TransactionListResponse(BaseModel):
    data: list[TransactionOut]
    meta: PaginationMeta


class ReportListResponse(BaseModel):
    data: list[ReportRowOut]
    meta: ReportMeta


class CategorizationRuleListResponse(BaseModel):
    data: list[CategorizationRuleOut]
