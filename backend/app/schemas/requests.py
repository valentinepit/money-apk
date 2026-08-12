"""Схемы тел запросов (POST/PATCH).

По правилу проекта "POST/PATCH — через Form, GET — через Query" эти классы
не JSON-body — они передаются в роутер как форм-модель через
``Annotated[XxxRequest, Form()]`` (FastAPI парсит
``application/x-www-form-urlencoded`` прямо в Pydantic-модель, см.
https://fastapi.tiangolo.com/tutorial/request-form-models/). Это не
нарушает правило Form: тело всё ещё form-encoded, просто набор полей
сгруппирован в один класс вместо отдельных ``Form(...)`` параметров в
сигнатуре роутера — симметрично тому, как сгруппированы схемы ответов в
``app/schemas/responses.py``.

Семантика PATCH: непереданное поле (значение None после парсинга формы)
трактуется как "не менять" — см. использование ``model_dump(exclude_none=True)``
в соответствующих роутерах.
"""

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CategoryCreate(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None


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
