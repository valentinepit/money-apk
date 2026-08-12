# Модель данных (черновик v1)

Статус: черновик, обсуждается в ветке `feature/data-model-api-contract`.

## Зафиксированные решения (этот шаг)

- Приложение одно-пользовательское: без публичной регистрации, учётная запись создаётся вручную на сервере (например, через сид/скрипт или переменные окружения при первом деплое). Изоляция данных между пользователями не нужна.
- Учитываются только расходы (траты). Понятие "доход" и знак суммы для дохода не вводим — все суммы транзакций по умолчанию считаются тратой. Если позже понадобится учёт доходов — отдельное решение вне MVP.
- Категории — плоский список, без иерархии (без подкатегорий).
- `category_id` у транзакции — NOT NULL. Если не сработало ни личное правило, ни общий словарь, транзакции присваивается системная категория **"Другое"** (а не null). Это упрощает отчёты и агрегацию — не нужно отдельно обрабатывать отсутствие категории.

## Сущности

### User (пользователь)
Одна запись на весь сервис (single-user), но модель делаем нормальной таблицей — это упрощает будущий переход на multi-user, если понадобится, и не усложняет MVP.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| email | string, unique | используется как логин |
| password_hash | string | bcrypt/argon2 |
| created_at | timestamp | |

### Account (счёт / карта / банк)
Нужен, чтобы привязывать транзакции и импорт-сессии к конкретному счёту/банку — у каждого банка свой формат выписки и свой парсер.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| user_id | FK → User | |
| name | string | название счёта, задаёт пользователь, например "Основная карта N26" |
| bank_name | string, nullable | название банка — влияет на выбор парсера при импорте |
| currency | string, fixed "EUR" | зафиксировано на MVP |
| created_at | timestamp | |
| archived | bool, default false | скрыть неиспользуемый счёт без удаления истории |

### Category (категория)
Плоский список, без родителя/потомков.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| user_id | FK → User, nullable | null = системная категория по умолчанию, задаётся при первом деплое |
| name | string | |
| icon | string, nullable | опционально, для UI |
| color | string, nullable | опционально, для UI/диаграммы |
| is_system | bool | системная (сидированная) или созданная пользователем |
| created_at | timestamp | |

Специальная системная категория **"Другое"** — id известен заранее (сидируется при первом деплое), назначается транзакциям, для которых не сработало ни личное правило, ни общий словарь. Пользователь может переназначить категорию вручную в превью импорта — выбор сохранится как новое личное правило.

### Transaction (транзакция / трата)
Центральная сущность.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| user_id | FK → User | |
| account_id | FK → Account | |
| category_id | FK → Category, NOT NULL | по умолчанию — системная категория "Другое" |
| amount | decimal(12,2) | всегда положительное значение траты, в EUR |
| currency | string, fixed "EUR" | |
| merchant_raw | string | исходная строка мерчанта — как пришла из выписки/введена вручную |
| merchant_normalized | string | нормализованная строка (для сопоставления с правилами/словарём) |
| note | string, nullable | заметка пользователя |
| transaction_date | date | дата операции (не дата создания записи) |
| source | enum: manual \| import | |
| import_session_id | FK → ImportSession, nullable | заполнено, если пришло из импорта |
| created_at | timestamp | |
| updated_at | timestamp | |

### ImportSession (импорт-сессия)
Одна загрузка одного файла выписки.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| user_id | FK → User | |
| account_id | FK → Account | к какому счёту относится выписка |
| file_name | string | |
| file_type | enum: pdf \| csv | |
| bank_parser | string | код/имя парсера, который использовался |
| status | enum: uploaded \| parsed \| failed \| reviewed \| confirmed | |
| error_message | string, nullable | если status = failed |
| created_at | timestamp | |
| confirmed_at | timestamp, nullable | когда пользователь подтвердил импорт транзакций из превью |

### CategorizationRule (правило категоризации)
Хранит и общий словарь, и личные правила пользователя — как записи одной таблицы с разным `source`.

| Поле | Тип | Описание |
|---|---|---|
| id | UUID / int PK | |
| user_id | FK → User, nullable | null = общий системный словарь; не null = личное правило пользователя |
| merchant_pattern | string | нормализованная строка/подстрока для сопоставления с `merchant_normalized` |
| category_id | FK → Category | |
| source | enum: system_dictionary \| user_rule | приоритет: user_rule проверяется раньше system_dictionary |
| created_at | timestamp | |
| updated_at | timestamp | |

## Связи (кратко)

```
User 1───* Account
User 1───* Category
User 1───* Transaction
User 1───* ImportSession
User 1───* CategorizationRule

Account 1───* Transaction
Account 1───* ImportSession

Category 1───* Transaction
Category 1───* CategorizationRule

ImportSession 1───* Transaction
```

## Открытые вопросы для следующего обсуждения

1. Нужны ли пользователю несколько счетов сразу в MVP, или на первом шаге хватит одного счёта по умолчанию (упрощает и API, и экран импорта)?
2. Soft-delete для Transaction/Category (флаг `deleted_at`) или обычное удаление — важно для истории правок при импорте.
