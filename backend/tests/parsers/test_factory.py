"""TDD-тесты для фабрики парсеров (app/parsers/factory.py)."""

import pytest

from app.exceptions import UnknownStatementFormatError
from app.parsers.factory import get_parser_for
from app.parsers.seb_lv_card_transactions_csv import SebLvCardTransactionsCsvParser
from app.parsers.luminor_csv import LuminorCsvParser

from tests.parsers.test_seb_lv_card_transactions_csv import SAMPLE_CSV as SEB_SAMPLE_CSV
from tests.parsers.test_luminor_csv import SAMPLE_CSV as LUMINOR_SAMPLE_CSV


def test_get_parser_for_returns_seb_parser_for_seb_sample():
    parser = get_parser_for(SEB_SAMPLE_CSV.encode("utf-8-sig"), "kontaparskats.csv")
    assert isinstance(parser, SebLvCardTransactionsCsvParser)


def test_get_parser_for_returns_luminor_parser_for_luminor_sample():
    parser = get_parser_for(LUMINOR_SAMPLE_CSV.encode("cp1252"), "20260801202608193552_EUR_EN.csv")
    assert isinstance(parser, LuminorCsvParser)


def test_get_parser_for_raises_on_unknown_format():
    unrelated = "amount,date,merchant\n10.00,2026-01-01,Some Shop\n".encode("utf-8")
    with pytest.raises(UnknownStatementFormatError):
        get_parser_for(unrelated, "export.csv")
