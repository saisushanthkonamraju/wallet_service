import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LedgerOperation(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)
    balance = Column(Numeric(18, 4), nullable=False, default=0.0000)
    currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    ledger_entries = relationship(
        "LedgerEntry",
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by="desc(LedgerEntry.created_at)",
    )

    __table_args__ = (
        CheckConstraint("balance >= 0", name="check_wallet_balance_non_negative"),
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(SQLEnum(LedgerOperation, name="ledger_operation_enum"), nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    balance_after = Column(Numeric(18, 4), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    wallet = relationship("Wallet", back_populates="ledger_entries")

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_ledger_amount_positive"),
        Index("ix_ledger_wallet_created_at", "wallet_id", "created_at"),
    )
