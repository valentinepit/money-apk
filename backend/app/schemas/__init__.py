"""Пакет схем: ``requests.py`` (тела Form-запросов) + ``responses.py`` (ответы).

Реэкспортирует всё публичное из обоих модулей, чтобы старые импорты вида
``from app.schemas import CategoryOut`` продолжали работать — но новый код
(роутеры) импортирует явно из ``app.schemas.requests`` / ``app.schemas.responses``.
"""

from app.schemas.requests import (
    CategoryCreate,
    CategoryUpdate,
    ImportSessionConfirmLine,
    ImportSessionConfirmRequest,
    LoginRequest,
    TransactionCreate,
    TransactionUpdate,
)
from app.schemas.responses import (
    CategorizationRuleListResponse,
    CategorizationRuleOut,
    CategoryDataResponse,
    CategoryListResponse,
    CategoryOut,
    ImportConfirmData,
    ImportConfirmResponse,
    ImportPreviewRowOut,
    ImportSessionDetailData,
    ImportSessionDetailResponse,
    ImportSessionListResponse,
    ImportSessionOut,
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
    "ImportSessionConfirmLine",
    "ImportSessionConfirmRequest",
    "LoginRequest",
    "TransactionCreate",
    "TransactionUpdate",
    "CategorizationRuleListResponse",
    "CategorizationRuleOut",
    "CategoryDataResponse",
    "CategoryListResponse",
    "CategoryOut",
    "ImportConfirmData",
    "ImportConfirmResponse",
    "ImportPreviewRowOut",
    "ImportSessionDetailData",
    "ImportSessionDetailResponse",
    "ImportSessionListResponse",
    "ImportSessionOut",
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
