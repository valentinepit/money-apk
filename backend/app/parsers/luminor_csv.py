"""
Парсер CSV-выписки Luminor (карточные транзакции + прочие операции по счёту).

Формат: semicolon-CSV, кодировка Windows-1252 (не UTF-8 — в заголовке
встречается кавычка, которая как одиночный байт в UTF-8 не декодируется),
каждое поле в кавычках. В отличие от SEB-выписки, первая строка файла —
уже настоящий заголовок таблицы (нет отдельной строки-титула отчёта).

Мерчант "зашит" внутри поля Payment details одной слитной строкой вместе с
маской карты, датой, городом, страной и номером документа без разделителей
(например "************7721EUR12026-08-17MAXIMA LV R770RigaLVA576959") — по
явному решению пользователя (см. claude/plan.md, фаза 5) поле сохраняется в
merchant_raw целиком, без попытки вычленить точное название мерчанта:
разбор эвристикой по образцу из 8 строк был бы слишком хрупким, а словарь
категоризации ниже по пайплайну и так способен найти известный мерчант
(MAXIMA, LIDL и т.п.) по подстроке внутри более длинной строки.
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from app.exceptions import StatementParseError
from app.parsers.base import BankStatementParser, ParsedTransaction

# Набор английских названий колонок, специфичных именно для этого экспорта
# Luminor — не пересекается с латышскими маркерами SEB-парсера.
_HEADER_MARKERS = ("Transaction type", "Orig. currency", "Payment details")

_DEBIT = "D"
_SUPPORTED_CURRENCY = "EUR"  # money-apk считает только в EUR (см. claude/plan.md)


class LuminorCsvParser(BankStatementParser):
    name = "luminor_csv"

    @classmethod
    def can_parse(cls, raw_bytes: bytes, file_name: str) -> bool:
        try:
            head = raw_bytes[:4096].decode("cp1252", errors="ignore")
        except Exception:
            return False
        return all(marker in head for marker in _HEADER_MARKERS)

    def parse(self, raw_bytes: bytes) -> list[ParsedTransaction]:
        try:
            text = raw_bytes.decode("cp1252")
        except UnicodeDecodeError as exc:
            raise StatementParseError("Не удалось прочитать файл в кодировке Windows-1252") from exc

        lines = text.splitlines()
        if not lines:
            raise StatementParseError("Файл пустой или не содержит заголовка таблицы")

        # В отличие от SEB — первая строка уже настоящий заголовок таблицы,
        # пропускать её перед DictReader не нужно.
        reader = csv.DictReader(lines, delimiter=";")
        transactions: list[ParsedTransaction] = []
        line_no = 0
        for row in reader:
            if not row.get("Date"):
                # Пустая строка (например хвостовой перевод строки) — не
                # настоящая строка данных, пропускаем без счёта.
                continue
            line_no += 1

            debit_credit = (row.get("C/D") or "").strip()
            if debit_credit != _DEBIT:
                # Пополнение счёта (кредит) — не трата, приложение считает
                # только расходы (см. claude/plan.md, "Учёт только расходов").
                continue

            currency = (row.get("Orig. currency") or "").strip()
            if currency != _SUPPORTED_CURRENCY:
                raise StatementParseError(
                    f"Строка {line_no}: валюта операции '{currency}' не поддерживается "
                    f"(money-apk считает только в {_SUPPORTED_CURRENCY})"
                )

            transaction_date = self._parse_date(row, line_no)
            amount = self._parse_amount(row, line_no)
            merchant_raw = (row.get("Payment details") or "").strip()
            # Transaction ID — уникальный номер операции от банка, используется
            # для дедупликации при повторном импорте (см. app/parsers/base.py,
            # ParsedTransaction.external_ref).
            external_ref = (row.get("Transaction ID") or "").strip() or None

            transactions.append(
                ParsedTransaction(
                    line_no=line_no,
                    transaction_date=transaction_date,
                    amount=amount,
                    merchant_raw=merchant_raw,
                    external_ref=external_ref,
                )
            )

        return transactions

    @staticmethod
    def _parse_date(row: dict, line_no: int) -> date:
        raw_value = (row.get("Date") or "").strip()
        try:
            return datetime.strptime(raw_value, "%Y%m%d").date()
        except ValueError as exc:
            raise StatementParseError(f"Строка {line_no}: не удалось разобрать дату '{raw_value}'") from exc

    @staticmethod
    def _parse_amount(row: dict, line_no: int) -> float:
        raw_value = (row.get("Amount") or "").strip()
        try:
            return float(raw_value)
        except ValueError as exc:
            raise StatementParseError(f"Строка {line_no}: не удалось разобрать сумму '{raw_value}'") from exc
