from app.normalization import normalize_merchant


def test_normalize_uppercases():
    assert normalize_merchant("rewe") == "REWE"


def test_normalize_strips_digits_and_terminal_codes():
    assert normalize_merchant("REWE SAGT DANKE 123456") == "REWE SAGT DANKE"


def test_normalize_collapses_whitespace():
    assert normalize_merchant("  REWE   MARKT  ") == "REWE MARKT"


def test_normalize_empty_string_stays_empty():
    assert normalize_merchant("") == ""


def test_normalize_none_stays_empty():
    assert normalize_merchant(None) == ""
