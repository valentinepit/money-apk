import asyncio
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, make_async_engine
from app.unit_of_work import SqlAlchemyUnitOfWork

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://money_apk:money_apk_dev@localhost/money_apk_test",
)


def _run(coro):
    """Выполняет однократную async-настройку на отдельном временном event loop.

    Схема БД создаётся/удаляется один раз за тестовую сессию — это не связано
    с event loop-ом конкретного теста, поэтому безопасно использовать
    отдельный короткоживущий loop, а не тот, что pytest-asyncio создаёт для
    тестовых функций.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    engine = make_async_engine(TEST_DATABASE_URL)

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    _run(_create())
    yield

    engine = make_async_engine(TEST_DATABASE_URL)

    async def _drop() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    _run(_drop())


@pytest.fixture
async def engine():
    """Отдельный движок на каждый тест — привязан к event loop-у именно этого теста."""
    eng = make_async_engine(TEST_DATABASE_URL)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncSession:
    """Одна внешняя транзакция на подключение + SAVEPOINT для сессии.

    Код под тестом (сервисы/роутеры) может свободно вызывать await session.commit()
    — благодаря join_transaction_mode="create_savepoint" это коммитит только
    SAVEPOINT и сразу открывает новый, а внешняя транзакция на connection
    откатывается в конце теста, изолируя тесты друг от друга.
    См. https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    """
    connection = await engine.connect()
    await connection.begin()
    session = AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        await session.close()
        await connection.rollback()
        await connection.close()


@pytest.fixture
async def uow(db_session: AsyncSession) -> SqlAlchemyUnitOfWork:
    unit = SqlAlchemyUnitOfWork(session=db_session)
    async with unit:
        yield unit
