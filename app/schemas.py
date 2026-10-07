import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models import LedgerOperation


# --- Wallet Schemas ---
class WalletCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    currency: Optional[str] = Field("USD", min_length=3, max_length=10, description="Currency code (e.g. USD)")


class WalletResponse(BaseModel):
    id: uuid.UUID
    user_id: str
    balance: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletBalanceResponse(BaseModel):
    wallet_id: uuid.UUID
    user_id: str
    balance: Decimal
    currency: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Transaction / Ledger Schemas ---
class TransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=4, description="Transaction amount (must be > 0)")
    description: Optional[str] = Field(None, max_length=255, description="Optional note or reference")


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    operation_type: LedgerOperation
    amount: Decimal
    balance_after: Decimal
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LedgerHistoryResponse(BaseModel):
    wallet_id: uuid.UUID
    total_entries: int
    entries: List[LedgerEntryResponse]
