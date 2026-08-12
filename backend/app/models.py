import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


class TransactionSource(str, enum.Enum):
    manual = "manual"
    import_ = "import"


class ImportFileType(str, enum.Enum):
    pdf = "pdf"
    csv = "csv"


class ImportSessionStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    failed = "failed"
    reviewed = "reviewed"
    confirmed = "confirmed"


class RuleSource(str, enum.Enum):
    system_dictionary = "system_dictionary"
    user_rule = "user_rule"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    accounts: Mapped[list["Account"]] = relationship(back_populates="user")
    categories: Mapped[list["Category"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="accounts")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(back_populates="categories")

    # Хорошо известное имя системной категории по умолчанию (см. docs/api/data-model.md).
    DEFAULT_CATEGORY_NAME = "Другое"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    merchant_raw: Mapped[str] = mapped_column(String(500), nullable=False)
    merchant_normalized: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[TransactionSource] = mapped_column(
        Enum(TransactionSource, native_enum=False, length=20), nullable=False
    )
    import_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("import_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="transactions")
    account: Mapped[Account] = relationship()
    category: Mapped[Category] = relationship()
    import_session: Mapped["ImportSession | None"] = relationship(back_populates="transactions")


class ImportSession(Base):
    __tablename__ = "import_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[ImportFileType] = mapped_column(
        Enum(ImportFileType, native_enum=False, length=10), nullable=False
    )
    bank_parser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ImportSessionStatus] = mapped_column(
        Enum(ImportSessionStatus, native_enum=False, length=20),
        nullable=False,
        default=ImportSessionStatus.uploaded,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_preview: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="import_session")


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    merchant_pattern: Mapped[str] = mapped_column(String(500), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id"), nullable=False)
    source: Mapped[RuleSource] = mapped_column(Enum(RuleSource, native_enum=False, length=20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
