"""TDD-тесты для фабрики парсеров (app/parsers/factory.py)."""

import pytest

from app.exceptions import UnknownStatementFormatError
from app.parsers.factory import get_parser_for
from app.parsers.lv_card_transactions_csv import LvCardTransactionsCsvParser

from tests.parsers.test_lv_card_transactions_csv import SAMPLE_CSV


def test_get_parser_for_returns_matching_parser():
    parser = get_parser_for(SAMPLE_CSV.encode("utf-8-sig"), "kontaparskats.csv")
    assert isinstance(parser, LvCardTransactionsCsvParser)


def test_get_parser_for_raises_on_unknown_format():
    unrelated = "amount,date,merchant\n10.00,2026-01-01,Some Shop\n".encode("utf-8")
    with pytest.raises(UnknownStatementFormatError):
        get_parser_for(unrelated, "export.csv")
