from app.models import Category


async def test_uow_commit_persists_within_test_transaction(uow, db_session):
    category = Category(name="Тест", is_system=True)
    await uow.categories.add(category)
    await uow.commit()

    fetched = await db_session.get(Category, category.id)
    assert fetched is not None
    assert fetched.name == "Тест"


async def test_uow_without_commit_does_not_persist(uow, db_session):
    category = Category(name="Без коммита", is_system=True)
    await uow.categories.add(category)
    await uow.session.flush()
    category_id = category.id
    await uow.rollback()

    fetched = await db_session.get(Category, category_id)
    assert fetched is None
