"""Схемы тел запросов (POST/PATCH)."""

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
