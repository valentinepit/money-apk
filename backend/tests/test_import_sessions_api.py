"""
TDD-тесты для эндпоинтов импорт-сессий (фаза 5, `POST/GET/DELETE /api/v1/import-sessions*`).

Контракт — `docs/api/api-contract.md`, раздел "Import". Реальные образцы
выписок (SEB, Luminor) берутся из тестов парсеров — не дублируем контент,
только импортируем готовые `SAMPLE_CSV`.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.deps import get_uow
from app.main import app
from app.models import (
    Category,
    CategorizationRule,
    ImportFileType,
    ImportSession,
    ImportSessionStatus,
    User,
)
from app.normalization import normalize_merchant
from app.security import create_access_token, hash_password
from app.unit_of_work import SqlAlchemyUnitOfWork

from tests.parsers.test_seb_lv_card_transactions_csv import SAMPLE_CSV as SEB_SAMPLE_CSV
from tests.parsers.test_luminor_csv import SAMPLE_CSV as LUMINOR_SAMPLE_CSV


@pytest.fixture
async def client(db_session):
    # Тот же паттерн, что и в остальных *_api тестах — один открытый UoW на
    # весь тест, чтобы __aexit__ отдельных HTTP-запросов не откатывал общий
    # savepoint (см. tests/test_transactions_api.py).
    uow = SqlAlchemyUnitOfWork(session=db_session)
    await uow.__aenter__()

    async def override_get_uow():
        yield uow

    app.dependency_overrides[get_uow] = override_get_uow
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await uow.__aexit__(None, None, None)


@pytest.fixture
async def user(db_session) -> User:
    user = User(email="owner@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def other_user(db_session) -> User:
    user = User(email="other@example.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def auth_headers(user):
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def default_category(db_session) -> Category:
    category = Category(name=Category.DEFAULT_CATEGORY_NAME, is_system=True)
    db_session.add(category)
    await db_session.flush()
    return category


@pytest.fixture
async def groceries_category(db_session, user) -> Category:
    category = Category(user_id=user.id, name="Продукты")
    db_session.add(category)
    await db_session.flush()
    return category


@pytest.fixture
async def uploaded_seb_session(client, auth_headers, default_category) -> dict:
    """Загружает реальный образец SEB (3 расходные строки) через сам эндпоинт."""
    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("kontaparskats.csv", SEB_SAMPLE_CSV.encode("utf-8-sig"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["data"]


async def test_create_import_session_requires_auth(client):
    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")},
    )
    assert response.status_code == 401


async def test_create_import_session_parses_seb_csv_and_returns_preview_with_default_category(
    uploaded_seb_session, default_category
):
    body = uploaded_seb_session
    assert body["import_session"]["status"] == "parsed"
    assert body["import_session"]["bank_parser"] == "seb_lv_card_transactions_csv"

    preview = body["preview"]
    assert len(preview) == 3
    assert {row["merchant_raw"] for row in preview} == {"AI2SQL", "AIRBNB * HMFXC5QBRJ", "LMT.LV"}
    assert all(row["suggested_category_id"] == str(default_category.id) for row in preview)
    assert all(row["suggested_category_source"] == "default" for row in preview)

    ai2sql_row = next(row for row in preview if row["merchant_raw"] == "AI2SQL")
    assert ai2sql_row["amount"] == 4.96
    assert ai2sql_row["transaction_date"] == "2026-08-01"


async def test_create_import_session_suggests_category_from_existing_user_rule(
    client, auth_headers, db_session, user, groceries_category, default_category
):
    rule = CategorizationRule(
        user_id=user.id,
        merchant_pattern=normalize_merchant("AI2SQL"),
        category_id=groceries_category.id,
        source="user_rule",
    )
    db_session.add(rule)
    await db_session.flush()

    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("kontaparskats.csv", SEB_SAMPLE_CSV.encode("utf-8-sig"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    preview = response.json()["data"]["preview"]
    ai2sql_row = next(row for row in preview if row["merchant_raw"] == "AI2SQL")
    assert ai2sql_row["suggested_category_id"] == str(groceries_category.id)
    assert ai2sql_row["suggested_category_source"] == "user_rule"


async def test_create_import_session_with_unrecognized_format_returns_422(client, auth_headers, default_category):
    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("export.csv", b"amount,date,merchant\n10.00,2026-01-01,Some Shop\n", "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()["data"]
    assert body["import_session"]["status"] == "failed"
    assert body["import_session"]["error_message"]
    assert body["import_session"]["bank_parser"] is None
    assert body["preview"] == []


async def test_create_import_session_with_invalid_currency_returns_422(client, auth_headers, default_category):
    broken_csv = SEB_SAMPLE_CSV.replace('4.96;"**** **** **** 8360";"EUR"', '4.96;"**** **** **** 8360";"USD"', 1)

    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("kontaparskats.csv", broken_csv.encode("utf-8-sig"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()["data"]
    assert body["import_session"]["status"] == "failed"
    # Формат распознан (заголовок совпал) — bank_parser заполняется раньше,
    # чем parse() успевает упасть на невалидной валюте.
    assert body["import_session"]["bank_parser"] == "seb_lv_card_transactions_csv"


async def test_create_import_session_parses_luminor_csv(client, auth_headers, default_category):
    response = await client.post(
        "/api/v1/import-sessions",
        files={
            "file": (
                "20260801202608193552_EUR_EN.csv",
                LUMINOR_SAMPLE_CSV.encode("cp1252"),
                "text/csv",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["import_session"]["bank_parser"] == "luminor_csv"
    assert len(body["preview"]) == 7
    assert (
        body["preview"][1]["merchant_raw"]
        == "************7721EUR12026-08-17MAXIMA LV R770RigaLVA576959"
    )


async def test_list_import_sessions_returns_only_own_sessions(
    client, auth_headers, db_session, user, other_user
):
    own = ImportSession(
        user_id=user.id, file_name="a.csv", file_type=ImportFileType.csv, status=ImportSessionStatus.uploaded
    )
    others = ImportSession(
        user_id=other_user.id,
        file_name="b.csv",
        file_type=ImportFileType.csv,
        status=ImportSessionStatus.uploaded,
    )
    db_session.add_all([own, others])
    await db_session.flush()

    response = await client.get("/api/v1/import-sessions", headers=auth_headers)
    assert response.status_code == 200
    file_names = {s["file_name"] for s in response.json()["data"]}
    assert file_names == {"a.csv"}


async def test_get_import_session_detail_includes_preview(uploaded_seb_session, client, auth_headers):
    session_id = uploaded_seb_session["import_session"]["id"]
    response = await client.get(f"/api/v1/import-sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["preview"] == uploaded_seb_session["preview"]


async def test_get_import_session_for_other_user_returns_404(client, auth_headers, db_session, other_user):
    session = ImportSession(
        user_id=other_user.id,
        file_name="b.csv",
        file_type=ImportFileType.csv,
        status=ImportSessionStatus.uploaded,
    )
    db_session.add(session)
    await db_session.flush()

    response = await client.get(f"/api/v1/import-sessions/{session.id}", headers=auth_headers)
    assert response.status_code == 404


async def test_confirm_import_session_creates_transactions_with_suggested_categories(
    client, auth_headers, uploaded_seb_session, default_category
):
    session_id = uploaded_seb_session["import_session"]["id"]
    response = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm",
        json={"transactions": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    created = response.json()["data"]["created_transactions"]
    assert len(created) == 3
    assert {t["merchant_raw"] for t in created} == {"AI2SQL", "AIRBNB * HMFXC5QBRJ", "LMT.LV"}
    assert all(t["category_id"] == str(default_category.id) for t in created)
    assert all(t["source"] == "import" for t in created)

    detail = await client.get(f"/api/v1/import-sessions/{session_id}", headers=auth_headers)
    assert detail.json()["data"]["import_session"]["status"] == "confirmed"


async def test_confirm_import_session_respects_exclude_flag(client, auth_headers, uploaded_seb_session):
    session_id = uploaded_seb_session["import_session"]["id"]
    excluded_line_no = next(
        row["line_no"] for row in uploaded_seb_session["preview"] if row["merchant_raw"] == "AI2SQL"
    )

    response = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm",
        json={"transactions": [{"line_no": excluded_line_no, "exclude": True}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    created = response.json()["data"]["created_transactions"]
    assert len(created) == 2
    assert all(t["merchant_raw"] != "AI2SQL" for t in created)


async def test_confirm_import_session_overrides_category_and_creates_user_rule(
    client, auth_headers, db_session, user, uploaded_seb_session, groceries_category
):
    session_id = uploaded_seb_session["import_session"]["id"]
    ai2sql_line_no = next(
        row["line_no"] for row in uploaded_seb_session["preview"] if row["merchant_raw"] == "AI2SQL"
    )

    response = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm",
        json={"transactions": [{"line_no": ai2sql_line_no, "category_id": str(groceries_category.id)}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    created = response.json()["data"]["created_transactions"]
    ai2sql = next(t for t in created if t["merchant_raw"] == "AI2SQL")
    assert ai2sql["category_id"] == str(groceries_category.id)

    result = await db_session.scalars(
        select(CategorizationRule).where(
            CategorizationRule.user_id == user.id,
            CategorizationRule.merchant_pattern == ai2sql["merchant_normalized"],
        )
    )
    rule = result.one_or_none()
    assert rule is not None
    assert rule.category_id == groceries_category.id


async def test_confirm_already_confirmed_session_returns_409(client, auth_headers, uploaded_seb_session):
    session_id = uploaded_seb_session["import_session"]["id"]
    first = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm", json={"transactions": []}, headers=auth_headers
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm", json={"transactions": []}, headers=auth_headers
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "session_already_confirmed"


async def test_delete_unconfirmed_import_session_removes_it(client, auth_headers, db_session, uploaded_seb_session):
    session_id = uploaded_seb_session["import_session"]["id"]
    response = await client.delete(f"/api/v1/import-sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 204

    remaining = await db_session.get(ImportSession, uuid.UUID(session_id))
    assert remaining is None


async def test_reimporting_same_statement_after_confirm_returns_empty_preview(
    client, auth_headers, uploaded_seb_session, default_category
):
    # Фаза 6 (claude/plan.md): защита от дублей. Подтверждаем первый импорт,
    # затем загружаем тот же файл ещё раз — все три строки уже есть в базе
    # (совпадение по external_ref = TRANSAKCIJAS NUMURS), preview должен
    # оказаться пустым.
    session_id = uploaded_seb_session["import_session"]["id"]
    confirm = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm", json={"transactions": []}, headers=auth_headers
    )
    assert confirm.status_code == 200
    assert len(confirm.json()["data"]["created_transactions"]) == 3

    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("kontaparskats.csv", SEB_SAMPLE_CSV.encode("utf-8-sig"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["data"]["preview"] == []


async def test_reimporting_statement_with_one_new_row_shows_only_the_new_row(
    client, auth_headers, uploaded_seb_session, default_category
):
    # Частичное перекрытие — например следующая выписка снова захватывает
    # хвост предыдущего периода. Уже занесённые строки не показываются,
    # новая — показывается.
    session_id = uploaded_seb_session["import_session"]["id"]
    confirm = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm", json={"transactions": []}, headers=auth_headers
    )
    assert confirm.status_code == 200

    extra_row_csv = SEB_SAMPLE_CSV.replace(
        '"CLR8832956";18.08.2026;"EUR";25.00;"LMT.LV";"";"";"SEB BANKA";"UNLALV2X";'
        '"16/08/2026 08:48 karte...598360 LMT.LV/80768076/LVA #631727";"RO1997535792L01";'
        '16.08.2026;"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";25.00;'
        '"**** **** **** 8360";"EUR";\n',
        '"CLR8832956";18.08.2026;"EUR";25.00;"LMT.LV";"";"";"SEB BANKA";"UNLALV2X";'
        '"16/08/2026 08:48 karte...598360 LMT.LV/80768076/LVA #631727";"RO1997535792L01";'
        '16.08.2026;"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";25.00;'
        '"**** **** **** 8360";"EUR";\n'
        '"CLR8899999";19.08.2026;"EUR";9.99;"NEW SHOP";"";"";"SEB BANKA";"UNLALV2X";'
        '"18/08/2026 12:00 karte...598360 NEW SHOP/RIGA/LVA #999999";"RO9999999999L01";'
        '18.08.2026;"PMNTCCRDOTHR-purchase in POS Dinamo payment card";"";"D";9.99;'
        '"**** **** **** 8360";"EUR";\n',
        1,
    )

    response = await client.post(
        "/api/v1/import-sessions",
        files={"file": ("kontaparskats2.csv", extra_row_csv.encode("utf-8-sig"), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    preview = response.json()["data"]["preview"]
    assert len(preview) == 1
    assert preview[0]["merchant_raw"] == "NEW SHOP"


async def test_delete_confirmed_import_session_returns_409(client, auth_headers, uploaded_seb_session):
    session_id = uploaded_seb_session["import_session"]["id"]
    confirm = await client.post(
        f"/api/v1/import-sessions/{session_id}/confirm", json={"transactions": []}, headers=auth_headers
    )
    assert confirm.status_code == 200

    response = await client.delete(f"/api/v1/import-sessions/{session_id}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "session_already_confirmed"
