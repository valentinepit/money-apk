"""Схемы ответов (``*Out``, конверты ``*Response``).

Эти классы используются в ``response_model=`` роутеров — FastAPI валидирует
и документирует (OpenAPI) реальную форму ответа, а не просто ``dict``.
Схемы тел запросов (POST/PATCH) — в соседнем модуле ``app/schemas/requests.py``.
"""

import uuid
from datetime import date, datetime

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


class ImportSessionOut(BaseModel):
    id: uuid.UUID
    file_name: str
    file_type: str
    bank_parser: str | None
    status: str
    error_message: str | None
    created_at: datetime
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}


class ImportPreviewRowOut(BaseModel):
    """Одна строка превью распознанного файла (см. api-contract.md, "Import").

    Строится не из ORM-объекта, а из словаря внутри ImportSession.parsed_preview
    (JSONB) — from_attributes не нужен, pydantic валидирует обычный dict.
    """

    line_no: int
    merchant_raw: str
    merchant_normalized: str
    amount: float
    transaction_date: date
    suggested_category_id: uuid.UUID
    suggested_category_source: str


class ImportSessionDetailData(BaseModel):
    import_session: ImportSessionOut
    preview: list[ImportPreviewRowOut]


class ImportConfirmData(BaseModel):
    created_transactions: list[TransactionOut]


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


class ImportSessionDetailResponse(BaseModel):
    data: ImportSessionDetailData


class ImportSessionListResponse(BaseModel):
    data: list[ImportSessionOut]


class ImportConfirmResponse(BaseModel):
    data: ImportConfirmData
