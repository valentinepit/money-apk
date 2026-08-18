# API-контракт (v1)

Статус: черновик v1, ветка `feature/data-model-api-contract`. Опирается на согласованную модель данных (`docs/api/data-model.md`).

## Общие конвенции

- Base path: `/api/v1`.
- Формат тел запросов: **POST и PATCH — `application/x-www-form-urlencoded`** (FastAPI `Form(...)` прямо в сигнатуре роутера, без отдельной Pydantic-модели тела), **GET-параметры — через `Query(...)`** (тоже явно в сигнатуре, включая обязательные). Это осознанное правило проекта (не JSON body для мутаций) — зафиксировано во всех бэкенд-проектах, не только здесь. Исключение: загрузка файла (`multipart/form-data`, см. Import) и `confirm` импорт-сессии, где тело — вложенный список объектов, который не выражается плоскими form-полями (см. пометку в разделе Import).
- Формат ответов: JSON. Поля — snake_case (соответствует модели данных и Python/FastAPI), camelCase не используем.
- Аутентификация: `Authorization: Bearer <jwt>`. Один долгоживущий access-токен, без refresh-эндпоинта (single-user, личное использование). Отзыв токена — только сменой секрета подписи на сервере (крайний случай).
- Идентификаторы — UUID (строка).
- Даты: `transaction_date` — `YYYY-MM-DD`; таймстемпы (`created_at`, `updated_at`, `confirmed_at`) — RFC 3339 (`2026-08-12T10:15:00Z`).
- Пагинация — offset-based (`page`, `per_page`), т.к. датасет одного пользователя небольшой (см. api-design: offset подходит для admin-панелей и небольших наборов данных).
- Сортировка: `?sort=-transaction_date` (минус — убывание), по умолчанию `-transaction_date` для списка транзакций.
- Ответ-конверт:
  - успех: `{"data": ...}`, для списков дополнительно `{"data": [...], "meta": {"total": N, "page": N, "per_page": N, "total_pages": N}}`.
  - ошибка: `{"error": {"code": "...", "message": "...", "details": [...]}}` (details — опционально, для 422 с полями).
- Стандартные коды: 200/201/204 успех, 400/401/403/404/409/422 клиентские ошибки, 500 серверная (без утечки деталей).
- Soft-delete: все GET-списки по умолчанию возвращают только `deleted_at IS NULL`. Для Transaction/Category можно передать `?include_deleted=true`, если понадобится посмотреть историю.

## Auth

### POST /api/v1/auth/login
Тело (`application/x-www-form-urlencoded`): `email`, `password`.
- 200 `{"data": {"access_token": "...", "token_type": "bearer"}}`
- 401 неверные email/пароль

Регистрации нет — единственный пользователь сидируется на сервере при деплое.

## Categories

| Метод | Путь | Описание |
|---|---|---|
| GET | /api/v1/categories | список (без удалённых по умолчанию); query: `include_deleted` |
| POST | /api/v1/categories | создать; form-поля: `name`, `icon?`, `color?` |
| GET | /api/v1/categories/:id | одна категория |
| PATCH | /api/v1/categories/:id | обновить; form-поля: `name?`, `icon?`, `color?` |
| DELETE | /api/v1/categories/:id | soft-delete |

- Form-поля PATCH не различают "не передано" и "передано как null" — непереданное поле трактуется как "не менять" (нельзя очистить `icon`/`color` до null через API, только оставить прежним или задать новое значение).
- `name` не может быть пустой строкой (`min_length=1`) — как при создании, так и при обновлении (если поле передано).
- `DELETE` системной категории "Другое" → 409 `category_is_system`, запрещено.
- `DELETE` категории, на которую ссылаются активные транзакции — не блокируем: транзакции остаются с этой `category_id`, но т.к. категория помечена `deleted_at`, в UI выбора категорий она не показывается (кроме как "текущая категория" уже проставленной транзакции).

## Transactions

| Метод | Путь | Описание |
|---|---|---|
| GET | /api/v1/transactions | список с фильтрами и пагинацией |
| POST | /api/v1/transactions | создать вручную |
| GET | /api/v1/transactions/:id | одна транзакция |
| PATCH | /api/v1/transactions/:id | частичное обновление |
| DELETE | /api/v1/transactions/:id | soft-delete |

Query-параметры для GET-списка (все через `Query(...)`): `date_from`, `date_to` (по `transaction_date`), `category_id`, `source` (`manual`/`import`), `q` (поиск по `merchant_raw`), `page`, `per_page`, `include_deleted`, `sort`.

POST-тело (`application/x-www-form-urlencoded`): `amount`, `category_id?`, `merchant_raw?`, `note?`, `transaction_date`. `category_id` опционален — если не передан, ставится системная категория "Другое". `source` всегда `manual` для этого эндпоинта. Привязки к счёту нет — сущности Account в модели не существует (см. `docs/api/data-model.md`). `amount` должен быть строго положительным (`gt=0`) — все транзакции являются тратами, ноль и отрицательные значения отклоняются как `validation_error` (422).

PATCH-тело (form): те же поля, частично — как и у категорий, непереданное form-поле трактуется как "не менять" (не как явный null; `amount` также должен быть `> 0`, если передан). **Важно:** если `category_id` меняется и у транзакции есть `merchant_normalized`, сервер создаёт/обновляет личное правило (`CategorizationRule` с `source=user_rule`) — тем самым правки пользователя самообучают категоризацию при будущих импортах.

## Reports

### GET /api/v1/reports/by-category
Query (`Query(...)`, обе обязательные): `date_from`, `date_to`.
- 200 `{"data": [{"category_id": "...", "category_name": "...", "total": 123.45, "count": 7}], "meta": {"date_from": "...", "date_to": "...", "total_overall": 456.78}}`
- Сортировка результата — по `total` по убыванию.

## Categorization rules

| Метод | Путь | Описание |
|---|---|---|
| GET | /api/v1/categorization-rules | список правил, фильтр `?source=user_rule\|system_dictionary` |
| DELETE | /api/v1/categorization-rules/:id | удалить личное правило |

- Видимость (`GET`, а также владение для `DELETE`) скоуплена так же, как у категорий: своё личное правило (`user_id = текущий пользователь`) либо общее системное (`user_id IS NULL`). Правило другого пользователя — как будто не существует (404).
- `DELETE` правила с `source=system_dictionary` → **409** `rule_is_system` (общий словарь не редактируется через API в MVP, только миграцией/сидом) — симметрично `category_is_system` у категорий, а не 403 (это не про права доступа, а про то, что ресурс в принципе не поддерживает такую операцию).
- Реализовано: `GET`/`DELETE /api/v1/categorization-rules[...]` — готово (фаза 3, коммит `d961d02` в `feature/core-endpoints`).

## Import

| Метод | Путь | Описание |
|---|---|---|
| POST | /api/v1/import-sessions | загрузить файл выписки (`multipart/form-data`, поле `file`) |
| GET | /api/v1/import-sessions | список сессий (история импортов) |
| GET | /api/v1/import-sessions/:id | детали сессии + превью/результат |
| POST | /api/v1/import-sessions/:id/confirm | подтвердить импорт — создать транзакции |
| DELETE | /api/v1/import-sessions/:id | отменить неподтверждённую сессию |

Поток:

1. **POST /api/v1/import-sessions** — файл парсится синхронно (объёмы файлов небольшие, отдельного async-пайплайна в MVP не делаем). Результат — `ImportSession` со статусом `parsed` (или `failed`, если парсер не справился) и превью распознанных строк, ещё не сохранённых как `Transaction`:
   ```json
   {
     "data": {
       "import_session": {"id": "...", "status": "parsed", "bank_parser": "n26", ...},
       "preview": [
         {
           "line_no": 1,
           "merchant_raw": "REWE SAGT DANKE",
           "merchant_normalized": "REWE",
           "amount": 23.40,
           "transaction_date": "2026-08-05",
           "suggested_category_id": "...",
           "suggested_category_source": "user_rule"
         }
       ]
     }
   }
   ```
   При `status=failed` → 422, `error_message` в объекте сессии.

2. **POST /api/v1/import-sessions/:id/confirm** — тело содержит финальный список строк (пользователь мог поменять категорию или исключить строку в приложении). **Исключение из правила "POST — через Form":** это вложенный список объектов, который не выражается плоскими form-полями, поэтому здесь тело остаётся JSON (`application/json`) — решить окончательно перед реализацией фазы 5:
   ```json
   {"transactions": [{"line_no": 1, "category_id": "...", "exclude": false}]}
   ```
   Для каждой не исключённой строки создаётся `Transaction` (`source=import`, `import_session_id`). Если `category_id` в подтверждении отличается от `suggested_category_id` — создаётся/обновляется личное правило. После confirm: `ImportSession.status=confirmed`, `confirmed_at=now()`.
   - 200 `{"data": {"created_transactions": [...]}}`
   - 409, если сессия уже `confirmed`.

3. **DELETE /api/v1/import-sessions/:id** — только если сессия не `confirmed` (иначе 409); подтверждённые транзакции уже существуют и удаляются как обычные транзакции по отдельности.

### Дополнение к модели данных

Чтобы хранить превью между "распарсили" и "подтвердили", в `ImportSession` добавляется поле:

| Поле | Тип | Описание |
|---|---|---|
| parsed_preview | JSONB, nullable | результат парсинга до подтверждения; после `confirm` можно оставить как аудит-след или очистить — решим на этапе реализации |

(Обновить `docs/api/data-model.md` этим полем перед началом реализации бэкенда.)

## Коды ошибок (примеры)

| code | HTTP | Когда |
|---|---|---|
| validation_error | 422 | невалидные поля запроса |
| not_found | 404 | ресурс не найден или soft-deleted |
| category_is_system | 409 | попытка удалить системную категорию |
| session_already_confirmed | 409 | confirm/delete уже подтверждённой импорт-сессии |
| unauthorized | 401 | нет/невалиден токен |
| forbidden | 403 | например, изменение системного словаря правил |

## Процесс разработки (зафиксировано)

Начиная с фазы 2 (скелет бэкенда) и далее — **TDD**: тест на эндпоинт/бизнес-правило пишется до реализации (pytest + FastAPI `TestClient`/`httpx`), затем код, который делает тест зелёным. Договорённость закреплена здесь и в `docs/plan.md`.
