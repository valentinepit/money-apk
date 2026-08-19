"""
TDD-тесты для первого конкретного парсера (фаза 5, импорт-пайплайн).

Формат — CSV-выписка по карте, образец прислан пользователем
(файл обычно называется kontaparskats.csv, "выписка по счёту" на латышском):
semicolon-CSV, UTF-8 с BOM, кавычки у каждого поля, первая строка — заголовок
отчёта (не таблица), вторая — реальные названия колонок, даты DD.MM.YYYY.
"""

import pytest

from app.exceptions import StatementParseError
from app.parsers.base import ParsedTransaction
from app.parsers.lv_card_transactions_csv import LvCardTransactionsCsvParser

SAMPLE_CSV = (
    '"Kartes (**** **** **** 8360)  darījumu pārskats (par periodu: 01.08.2026-19.08.2026)";\n'
    '"MU NR.";"DATUMS";"MAKSĀJUMA VALŪTA";"MAKSĀJUMA SUMMA";"PARTNERA NOSAUKUMS";'
    '"PARTNERA PERS. KODS/ REĢ. NR.";"PARTNERA KONTS";"PARTNERA BANKA";'
    '"PARTNERA BANKAS SWIFT KODS";"MAKSĀJUMA MĒRĶIS";"TRANSAKCIJAS NUMURS";'
    '"DOKUMENTA DATUMS";"TRANSAKCIJAS TIPS";"REFERENCE";"DEBETS/ KREDĪTS";'
    '"SUMMA KONTA VALŪTĀ";"KONTA NR.";"KONTA VALŪTA";\n'
    '"CLR8781850";02.08.2026;"EUR";4.96;"AI2SQL";"";"";"SEB BANKA";"UNLALV2X";'
    '"01/08/2026 08:14 2612.59 KZT(4.82 EUR + komisija 0.14 EUR(3%)) karte...598360 '
    'AI2SQL/JACKSONVILLE/USA #158464";"RO1986420819L01";01.08.2026;'
    '"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";4.96;'
    '"**** **** **** 8360";"EUR";\n'
    '"CLR8828346";17.08.2026;"EUR";236.40;"AIRBNB * HMFXC5QBRJ";"";"";"SEB BANKA";'
    '"UNLALV2X";"16/08/2026 00:00 264.47 USD(229.51 EUR + komisija 6.89 EUR(3%)) '
    'karte...598360 AIRBNB * HMFXC5QBRJ/LUXEMBOURG/LUX #655267";"RO1996664152L01";'
    '16.08.2026;"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";236.40;'
    '"**** **** **** 8360";"EUR";\n'
    '"CLR8832956";18.08.2026;"EUR";25.00;"LMT.LV";"";"";"SEB BANKA";"UNLALV2X";'
    '"16/08/2026 08:48 karte...598360 LMT.LV/80768076/LVA #631727";"RO1997535792L01";'
    '16.08.2026;"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";25.00;'
    '"**** **** **** 8360";"EUR";\n'
)


def _sample_bytes() -> bytes:
    return SAMPLE_CSV.encode("utf-8-sig")


def test_can_parse_recognizes_sample_file():
    assert LvCardTransactionsCsvParser.can_parse(_sample_bytes(), "kontaparskats.csv") is True


def test_can_parse_rejects_unrelated_content():
    unrelated = "amount,date,merchant\n10.00,2026-01-01,Some Shop\n".encode("utf-8")
    assert LvCardTransactionsCsvParser.can_parse(unrelated, "export.csv") is False


def test_parse_extracts_all_debit_rows_in_eur():
    parser = LvCardTransactionsCsvParser()
    result = parser.parse(_sample_bytes())

    assert result == [
        ParsedTransaction(line_no=1, transaction_date=_date(2026, 8, 1), amount=4.96, merchant_raw="AI2SQL"),
        ParsedTransaction(
            line_no=2,
            transaction_date=_date(2026, 8, 16),
            amount=236.40,
            merchant_raw="AIRBNB * HMFXC5QBRJ",
        ),
        ParsedTransaction(line_no=3, transaction_date=_date(2026, 8, 16), amount=25.00, merchant_raw="LMT.LV"),
    ]


def test_parse_uses_document_date_not_processing_date():
    # DOKUMENTA DATUMS (дата самой покупки) отличается от DATUMS (дата
    # обработки банком) у второй и третьей строки образца (16.08 vs 17.08/18.08) —
    # в транзакцию должна попасть именно дата покупки.
    parser = LvCardTransactionsCsvParser()
    result = parser.parse(_sample_bytes())
    assert result[1].transaction_date == _date(2026, 8, 16)
    assert result[2].transaction_date == _date(2026, 8, 16)


def test_parse_skips_credit_rows():
    credit_row_csv = SAMPLE_CSV.replace(
        '"D";4.96;"**** **** **** 8360"', '"K";4.96;"**** **** **** 8360"', 1
    )
    parser = LvCardTransactionsCsvParser()
    result = parser.parse(credit_row_csv.encode("utf-8-sig"))
    assert len(result) == 2
    assert all(t.merchant_raw != "AI2SQL" for t in result)


def test_parse_rejects_non_eur_account_currency():
    non_eur_csv = SAMPLE_CSV.replace('4.96;"**** **** **** 8360";"EUR"', '4.96;"**** **** **** 8360";"USD"', 1)
    parser = LvCardTransactionsCsvParser()
    with pytest.raises(StatementParseError):
        parser.parse(non_eur_csv.encode("utf-8-sig"))


def _date(year: int, month: int, day: int):
    from datetime import date

    return date(year, month, day)
