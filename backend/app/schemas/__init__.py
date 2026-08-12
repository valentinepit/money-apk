"""Пакет схем: ``requests.py`` (тела Form-запросов) + ``responses.py`` (ответы).

Реэкспортирует всё публичное из обоих модулей, чтобы старые импорты вида
``from app.schemas import CategoryOut`` продолжали работать — но новый код
(роутеры) импортирует явно из ``app.schemas.requests`` / ``app.schemas.responses``.
"""

from app.schemas.requests import (
    CategoryCreate,
    CategoryUpdate,
    LoginRequest,
    TransactionCreate,
    TransactionUpdate,
)
from app.schemas.responses import (
    CategoryDataResponse,
    CategoryListResponse,
    CategoryOut,
    PaginationMeta,
    ReportListResponse,
    ReportMeta,
    ReportRowOut,
    TokenDataResponse,
    TokenResponse,
    TransactionDataResponse,
    TransactionListResponse,
    TransactionOut,
    UserDataResponse,
    UserOut,
)

__all__ = [
    "CategoryCreate",
    "CategoryUpdate",
    "LoginRequest",
    "TransactionCreate",
    "TransactionUpdate",
    "CategoryDataResponse",
    "CategoryListResponse",
    "CategoryOut",
    "PaginationMeta",
    "ReportListResponse",
    "ReportMeta",
    "ReportRowOut",
    "TokenDataResponse",
    "TokenResponse",
    "TransactionDataResponse",
    "TransactionListResponse",
    "TransactionOut",
    "UserDataResponse",
    "UserOut",
]
