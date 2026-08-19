"""
Фабрика парсеров — выбирает нужный класс по содержимому файла (см. base.py).

Какой банк прислал выписку определяется автоматически, а не выбором
пользователя (см. claude/plan.md, "Банки/форматы парсеров"): каждый
зарегистрированный парсер сам проверяет, подходит ли он под файл
(can_parse), и побеждает первый подошедший.
"""

from __future__ import annotations

from app.exceptions import UnknownStatementFormatError
from app.parsers.base import BankStatementParser
from app.parsers.lv_card_transactions_csv import LvCardTransactionsCsvParser

# Добавлять новые парсеры сюда по мере получения образцов выписок других
# банков (см. claude/plan.md, фаза 5). Порядок имеет значение только если
# сигнатуры двух парсеров вдруг пересекутся — выигрывает первый подошедший.
_PARSER_CLASSES: tuple[type[BankStatementParser], ...] = (LvCardTransactionsCsvParser,)


def get_parser_for(raw_bytes: bytes, file_name: str) -> BankStatementParser:
    for parser_cls in _PARSER_CLASSES:
        if parser_cls.can_parse(raw_bytes, file_name):
            return parser_cls()
    raise UnknownStatementFormatError(f"Не удалось определить формат файла '{file_name}'")
