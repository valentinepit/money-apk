"""Схемы тел запросов (POST/PATCH)."""

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    icon: str | None = None
    color: str | None = None


class CategoryUpdate(BaseModel):
    # min_length=1 действует, только если поле вообще передано (не None) —
    # непереданное поле по-прежнему трактуется как "не менять" (см. api-contract.md).
    name: str | None = Field(default=None, min_length=1)
    icon: str | None = None
    color: str | None = None


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    category_id: uuid.UUID | None = None
    merchant_raw: str | None = None
    note: str | None = None
    transaction_date: date


class TransactionUpdate(BaseModel):
    # gt=0 действует, только если amount вообще передан (не None) — см. комментарий выше.
    amount: float | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = None
    merchant_raw: str | None = None
    note: str | None = None
    transaction_date: date | None = None
