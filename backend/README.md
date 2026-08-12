# Backend

FastAPI + PostgreSQL + JWT. Реализует `docs/api/data-model.md` и `docs/api/api-contract.md`.

## Локальная разработка

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env   # заполнить свои значения

# Postgres локально — проще всего через docker-compose (только БД):
docker compose up -d db

alembic upgrade head
python -m app.seed      # создаёт пользователя из ADMIN_EMAIL/ADMIN_PASSWORD, счёт, категорию "Другое"

uvicorn app.main:app --reload
```

Проверить: `curl http://127.0.0.1:8000/health`.

## Тесты (TDD)

Тесты гоняются на реальном Postgres (не SQLite) — так тестовая среда ближе к продовой.

```bash
export TEST_DATABASE_URL=postgresql+psycopg2://money_apk:money_apk_dev@localhost/money_apk_test
pytest
```

Разработка по TDD: сначала пишем тест (красный), потом реализацию (зелёный). См. `docs/api/api-contract.md`, раздел "Процесс разработки".

## Docker

`docker compose up --build` — поднимает Postgres и API локально (см. `docker-compose.yml`).

## Деплой на VPS (заготовка, не выполнялся)

- `docker-compose.prod.yml` — Postgres + API + Caddy (автоматический HTTPS через Let's Encrypt).
- `Caddyfile.example` — скопировать в `Caddyfile`, указать домен.
- `.env.example` — скопировать в `.env` на сервере (не коммитить), заполнить секреты.
- Реальный деплой требует доступа к VPS (SSH/домен) — отдельный шаг с участием пользователя.
