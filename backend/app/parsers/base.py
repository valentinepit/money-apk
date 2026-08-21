"""
Абстракция парсера банковской выписки (фаза 5, импорт-пайплайн).

Каждый банк/формат выписки реализует свой класс-наследник BankStatementParser
и регистрируется в app/parsers/factory.py. Какой парсер применить к
конкретному файлу — определяется автоматически по содержимому (can_parse),
а не выбором пользователя (см. claude/plan.md, раздел "Банки/форматы
парсеров"). Приложение считает только траты (расходы, см. "Учёт только
расходов" в plan.md) — операции пополнения счёта (кредит) парсер должен
отбрасывать сам, а не возвращать их наружу.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ParsedTransaction:
    """Одна распознанная расходная операция — ещё не Transaction в БД.

    line_no — номер строки в исходном файле (считая с 1 от первой строки
    данных, не от заголовка). Нужен, чтобы на экране превью импорта
    пользователь мог сослаться на конкретную строку при подтверждении
    (исключить её или поменять категорию) — см. api-contract.md,
    POST /api/v1/import-sessions/:id/confirm.
    """

    line_no: int
    transaction_date: date
    amount: float
    merchant_raw: str


class BankStatementParser(ABC):
    """Абстрактный парсер одного формата выписки."""

    #: уникальный идентификатор парсера — сохраняется в ImportSession.bank_parser
    name: str

    @classmethod
    @abstractmethod
    def can_parse(cls, raw_bytes: bytes, file_name: str) -> bool:
        """Быстрая проверка по содержимому файла: подходит ли этот парсер.

        Не должна поднимать исключения на "чужих" файлах — на любой
        непредвиденной ошибке (например файл не декодируется в ожидаемой
        кодировке) нужно вернуть False, чтобы фабрика попробовала
        следующий парсер, а не упала.
        """

    @abstractmethod
    def parse(self, raw_bytes: bytes) -> list[ParsedTransaction]:
        """Полный разбор файла.

        Вызывается только после успешного can_parse(), поэтому вправе
        поднять StatementParseError, если содержимое не соответствует
        ожидаемой структуре (битый файл, неожиданная валюта и т.п.).
        """
