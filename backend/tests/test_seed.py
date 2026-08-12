from app.config import Settings
from app.models import Account, Category, User
from app.seed import run_seed


def test_run_seed_creates_user_account_and_default_category(db_session):
    settings = Settings(admin_email="owner@example.com", admin_password="owner-pass")

    run_seed(db_session, settings)

    user = db_session.query(User).filter(User.email == "owner@example.com").one()
    account = db_session.query(Account).filter(Account.user_id == user.id).one()
    category = db_session.query(Category).filter(Category.is_system.is_(True)).one()

    assert account.name
    assert category.name == Category.DEFAULT_CATEGORY_NAME


def test_run_seed_is_idempotent(db_session):
    settings = Settings(admin_email="owner2@example.com", admin_password="owner-pass")

    run_seed(db_session, settings)
    run_seed(db_session, settings)

    users = db_session.query(User).filter(User.email == "owner2@example.com").all()
    accounts = db_session.query(Account).all()
    system_categories = db_session.query(Category).filter(Category.is_system.is_(True)).all()

    assert len(users) == 1
    assert len(accounts) == 1
    assert len(system_categories) == 1
