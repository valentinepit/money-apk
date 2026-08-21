"""
TDD-тесты для парсера выписки Luminor (фаза 5, импорт-пайплайн).

Формат — CSV-выписка Luminor (Латвия), образец прислан пользователем
(файл вида 20260801202608193552_EUR_EN.csv): semicolon-CSV, кодировка
Windows-1252 (не UTF-8), кавычки у каждого поля, первая строка — уже
настоящий заголовок таблицы (в отличие от SEB, нет отдельной строки-титула
отчёта), даты YYYYMMDD без разделителей.
"""

from datetime import date

import pytest

from app.exceptions import StatementParseError
from app.parsers.base import ParsedTransaction
from app.parsers.luminor_csv import LuminorCsvParser

SAMPLE_CSV = (
    '"Transaction type";"Date";"Time";"Amount";"Equivalent";"C/D";"Orig. amount";"Orig. currency";'
    '"Document number";"Transaction ID";"Customer\'s code in beneficiary IS";"Payment code";'
    '"Payment details";"Counterparty BIC";"Counterparty Designation of counterparties credit institution";'
    '"Counterparty Account number";"Counterparty Designation";"Counterparty Reg No.";'
    '"Counterparty Customer\'s code in payer IS";"Ultimate Payer Account number";"Ultimate Payer name";'
    '"Ultimate Payer identification value.";"Ultimate Beneficiary Account number";'
    '"Ultimate Beneficiary name";"Ultimate Beneficiary identification value"\r\n'
    '"E39";"20260805";"123925";"6.90";"6.90";"D";"6.90";"EUR";"H262176JAR";"FC5674639244";"";"";'
    '"EUR12026-07-31LTUZACH262176JAR";"";"";"";"Luminor Bank AS";"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"084029";"51.93";"51.93";"D";"51.93";"EUR";"576959";"FC5691039165";"";"";'
    '"************7721EUR12026-08-17MAXIMA LV R770RigaLVA576959";"";"";"";"Luminor Bank AS";'
    '"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"084029";"8.89";"8.89";"D";"8.89";"EUR";"592079";"FC5691039171";"";"";'
    '"************7721EUR12026-08-17MAXIMA LV R770RigaLVA592079";"";"";"";"Luminor Bank AS";'
    '"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"133008";"6.80";"6.80";"D";"6.80";"EUR";"H26230DFL8";"FC5692420152";"";"";'
    '"************7721EUR12026-08-16DUS LUDZALUDZALVALTUZACH26230DFL8";"";"";"";"Luminor Bank AS";'
    '"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"133009";"33.00";"33.00";"D";"33.00";"EUR";"H26230DFLF";"FC5692420158";"";"";'
    '"************7721EUR12026-08-16PAY*Andaluzijas SunsRigaLVALTUZACH26230DFLF";"";"";"";'
    '"Luminor Bank AS";"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"133009";"6.78";"6.78";"D";"6.78";"EUR";"H26230DFLK";"FC5692420172";"";"";'
    '"************7721EUR12026-08-16DUS LUDZALUDZALVALTUZACH26230DFLK";"";"";"";"Luminor Bank AS";'
    '"";"";"";"";"";"";"";""\r\n'
    '"205";"20260818";"133009";"21.28";"21.28";"D";"21.28";"EUR";"H26230DFLP";"FC5692420183";"";"";'
    '"************7721EUR12026-08-16LIDL 143, RIGA, LACPLESARIGALVALTUZACH26230DFLP";"";"";"";'
    '"Luminor Bank AS";"";"";"";"";"";"";"";""\r\n'
)


def _sample_bytes() -> bytes:
    return SAMPLE_CSV.encode("cp1252")


def test_can_parse_recognizes_sample_file():
    assert LuminorCsvParser.can_parse(_sample_bytes(), "20260801202608193552_EUR_EN.csv") is True


def test_can_parse_rejects_unrelated_content():
    unrelated = "amount,date,merchant\n10.00,2026-01-01,Some Shop\n".encode("utf-8")
    assert LuminorCsvParser.can_parse(unrelated, "export.csv") is False


def test_parse_extracts_all_debit_rows_in_eur():
    parser = LuminorCsvParser()
    result = parser.parse(_sample_bytes())

    assert result == [
        ParsedTransaction(
            line_no=1,
            transaction_date=date(2026, 8, 5),
            amount=6.90,
            merchant_raw="EUR12026-07-31LTUZACH262176JAR",
            external_ref="FC5674639244",
        ),
        ParsedTransaction(
            line_no=2,
            transaction_date=date(2026, 8, 18),
            amount=51.93,
            merchant_raw="************7721EUR12026-08-17MAXIMA LV R770RigaLVA576959",
            external_ref="FC5691039165",
        ),
        ParsedTransaction(
            line_no=3,
            transaction_date=date(2026, 8, 18),
            amount=8.89,
            merchant_raw="************7721EUR12026-08-17MAXIMA LV R770RigaLVA592079",
            external_ref="FC5691039171",
        ),
        ParsedTransaction(
            line_no=4,
            transaction_date=date(2026, 8, 18),
            amount=6.80,
            merchant_raw="************7721EUR12026-08-16DUS LUDZALUDZALVALTUZACH26230DFL8",
            external_ref="FC5692420152",
        ),
        ParsedTransaction(
            line_no=5,
            transaction_date=date(2026, 8, 18),
            amount=33.00,
            merchant_raw="************7721EUR12026-08-16PAY*Andaluzijas SunsRigaLVALTUZACH26230DFLF",
            external_ref="FC5692420158",
        ),
        ParsedTransaction(
            line_no=6,
            transaction_date=date(2026, 8, 18),
            amount=6.78,
            merchant_raw="************7721EUR12026-08-16DUS LUDZALUDZALVALTUZACH26230DFLK",
            external_ref="FC5692420172",
        ),
        ParsedTransaction(
            line_no=7,
            transaction_date=date(2026, 8, 18),
            amount=21.28,
            merchant_raw="************7721EUR12026-08-16LIDL 143, RIGA, LACPLESARIGALVALTUZACH26230DFLP",
            external_ref="FC5692420183",
        ),
    ]


def test_parse_keeps_payment_details_verbatim_as_merchant_raw():
    # Явное решение пользователя (см. claude/plan.md, фаза 5): не пытаться
    # вычленить чистое название мерчанта из Payment details — сохранять как есть.
    parser = LuminorCsvParser()
    result = parser.parse(_sample_bytes())
    assert result[1].merchant_raw == "************7721EUR12026-08-17MAXIMA LV R770RigaLVA576959"


def test_parse_extracts_external_ref_from_transaction_id_column():
    # Transaction ID — уникальный номер операции, присваиваемый банком.
    # Используется для дедупликации при повторном импорте той же выписки
    # (см. claude/plan.md, фаза 6; app/services/import_service.py).
    parser = LuminorCsvParser()
    result = parser.parse(_sample_bytes())
    assert [t.external_ref for t in result] == [
        "FC5674639244",
        "FC5691039165",
        "FC5691039171",
        "FC5692420152",
        "FC5692420158",
        "FC5692420172",
        "FC5692420183",
    ]


def test_parse_skips_credit_rows():
    credit_row_csv = SAMPLE_CSV.replace(
        '"6.90";"6.90";"D";"6.90";"EUR"', '"6.90";"6.90";"C";"6.90";"EUR"', 1
    )
    parser = LuminorCsvParser()
    result = parser.parse(credit_row_csv.encode("cp1252"))
    assert len(result) == 6
    assert all("LTUZACH262176JAR" not in t.merchant_raw for t in result)


def test_parse_rejects_non_eur_currency():
    non_eur_csv = SAMPLE_CSV.replace(
        '"6.90";"6.90";"D";"6.90";"EUR"', '"6.90";"6.90";"D";"6.90";"USD"', 1
    )
    parser = LuminorCsvParser()
    with pytest.raises(StatementParseError):
        parser.parse(non_eur_csv.encode("cp1252"))
