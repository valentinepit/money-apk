"""Нормализация строки мерчанта для сопоставления с правилами категоризации.

Базовая версия (см. docs/plan.md, "Автокатегоризация по названию торговой точки"):
верхний регистр, убрать цифры/коды терминала, свернуть пробелы.
Полноценный словарь и более тонкая нормализация (юридические суффиксы/префиксы
банков и т.п.) появятся на фазе 5 (импорт-пайплайн), когда будут образцы выписок.
"""

import re

_DIGITS_RE = re.compile(r"\d+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_merchant(raw: str | None) -> str:
    if not raw:
        return ""

    value = raw.upper()
    value = _DIGITS_RE.sub("", value)
    value = _WHITESPACE_RE.sub(" ", value).strip()
    return value
