"""
Парсер CSV-выписки по карте SEB (Латвия) — образец прислан пользователем,
файл обычно называется kontaparskats.csv, "выписка по счёту" на латышском.

Формат: semicolon-CSV, UTF-8 с BOM, каждое поле в кавычках. Первая строка
файла — заголовок отчёта ("Kartes (...) darījumu pārskats...", не строка
таблицы), реальные названия колонок — во второй строке. Суммы через точку,
даты DD.MM.YYYY.
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from app.exceptions import StatementParseError
from app.parsers.base import BankStatementParser, ParsedTransaction

# Набор латышских названий колонок, который вряд ли встретится в выписке
# другого банка/формата — достаточно для однозначного автоопределения.
_HEADER_MARKERS = ("MU NR.", "PARTNERA NOSAUKUMS", "DEBETS/ KREDĪTS")

_DEBIT = "D"
_SUPPORTED_CURRENCY = "EUR"  # money-apk считает только в EUR (см. claude/plan.md)


class SebLvCardTransactionsCsvParser(BankStatementParser):
    name = "seb_lv_card_transactions_csv"

    @classmethod
    def can_parse(cls, raw_bytes: bytes, file_name: str) -> bool:
        try:
            head = raw_bytes[:4096].decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        return all(marker in head for marker in _HEADER_MARKERS)

    def parse(self, raw_bytes: bytes) -> list[ParsedTransaction]:
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise StatementParseError("Не удалось прочитать файл как UTF-8") from exc

        # Пропускаем первую строку (заголовок отчёта, не таблицы) — реальные
        # названия колонок для csv.DictReader находятся во второй строке файла.
        lines = text.splitlines()
        if len(lines) < 2:
            raise StatementParseError("Файл пустой или не содержит заголовка таблицы")

        reader = csv.DictReader(lines[1:], delimiter=";")
        transactions: list[ParsedTransaction] = []
        line_no = 0
        for row in reader:
            if not row.get("MU NR."):
                # Пустая строка (например хвостовой перевод строки в конце
                # файла) — не настоящая строка данных, пропускаем без счёта.
                continue
            line_no += 1

            debit_credit = (row.get("DEBETS/ KREDĪTS") or "").strip()
            if debit_credit != _DEBIT:
                # Пополнение счёта (кредит) — не трата, приложение считает
                # только расходы (см. claude/plan.md, "Учёт только расходов").
                continue

            currency = (row.get("KONTA VALŪTA") or "").strip()
            if currency != _SUPPORTED_CURRENCY:
                raise StatementParseError(
                    f"Строка {line_no}: валюта счёта '{currency}' не поддерживается "
                    f"(money-apk считает только в {_SUPPORTED_CURRENCY})"
                )

            transaction_date = self._parse_date(row, line_no)
            amount = self._parse_amount(row, line_no)
            merchant_raw = (row.get("PARTNERA NOSAUKUMS") or "").strip()
            # TRANSAKCIJAS NUMURS — уникальный номер операции от банка,
            # используется для дедупликации при повторном импорте (см.
            # app/parsers/base.py, ParsedTransaction.external_ref).
            external_ref = (row.get("TRANSAKCIJAS NUMURS") or "").strip() or None

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
        # DOKUMENTA DATUMS — дата самой операции (совпадает с датой внутри
        # текстового описания MAKSĀJUMA MĒRĶIS); DATUMS — дата обработки
        # банком, обычно на день-два позже. Транзакции нужна дата операции.
        raw_value = (row.get("DOKUMENTA DATUMS") or "").strip()
        try:
            return datetime.strptime(raw_value, "%d.%m.%Y").date()
        except ValueError as exc:
            raise StatementParseError(f"Строка {line_no}: не удалось разобрать дату '{raw_value}'") from exc

    @staticmethod
    def _parse_amount(row: dict, line_no: int) -> float:
        raw_value = (row.get("SUMMA KONTA VALŪTĀ") or "").strip()
        try:
            return float(raw_value)
        except ValueError as exc:
            raise StatementParseError(f"Строка {line_no}: не удалось разобрать сумму '{raw_value}'") from exc
