import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.service import WalletService
from app.schemas import (
    WalletCreate,
    WalletResponse,
    WalletBalanceResponse,
    TransactionRequest,
    LedgerEntryResponse,
    LedgerHistoryResponse,
)

router = APIRouter(prefix="/wallets", tags=["Wallets"])

DBDep = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="1. Create a wallet for a user",
)
def create_wallet(payload: WalletCreate, db: DBDep):
    """
    Creates a new wallet for a user with initial balance 0.00.
    Enforces uniqueness: each user can only have one wallet.
    """
    return WalletService.create_wallet(db, user_id=payload.user_id, currency=payload.currency or "USD")


@router.get(
    "",
    response_model=List[WalletResponse],
    summary="List all wallets / get wallet IDs",
)
def list_wallets(
    db: DBDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    Returns list of wallets including their wallet IDs (UUID) and user_ids.
    """
    return WalletService.get_all_wallets(db, limit=limit, offset=offset)


@router.get(
    "/users/{user_id}",
    response_model=WalletResponse,
    summary="Get wallet by user ID",
)
def get_wallet_by_user(user_id: str, db: DBDep):
    """
    Retrieves the wallet (including wallet_id) for a given user_id.
    """
    return WalletService.get_wallet_by_user_id(db, user_id=user_id)


@router.post(
    "/{wallet_id}/credit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="2. Credit money to wallet",
)
def credit_wallet(wallet_id: uuid.UUID, payload: TransactionRequest, db: DBDep):
    """
    Credits money to the wallet.
    Atomically updates wallet balance and creates an immutable ledger entry.
    """
    _, ledger_entry = WalletService.credit_wallet(
        db, wallet_id=wallet_id, amount=payload.amount, description=payload.description
    )
    return ledger_entry


@router.post(
    "/{wallet_id}/debit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="3. Debit money from wallet",
)
def debit_wallet(wallet_id: uuid.UUID, payload: TransactionRequest, db: DBDep):
    """
    Debits money from the wallet.
    Guarantees balance will never go negative using row-locking and DB check constraints.
    Atomically updates wallet balance and creates an immutable ledger entry.
    """
    _, ledger_entry = WalletService.debit_wallet(
        db, wallet_id=wallet_id, amount=payload.amount, description=payload.description
    )
    return ledger_entry


@router.get(
    "/{wallet_id}/balance",
    response_model=WalletBalanceResponse,
    summary="4. Get wallet balance",
)
def get_wallet_balance(wallet_id: uuid.UUID, db: DBDep):
    """
    Fetches current wallet balance directly from PostgreSQL (no in-memory cache).
    """
    wallet = WalletService.get_wallet_by_id(db, wallet_id=wallet_id)
    return WalletBalanceResponse(
        wallet_id=wallet.id,
        user_id=wallet.user_id,
        balance=wallet.balance,
        currency=wallet.currency,
        updated_at=wallet.updated_at,
    )


@router.get(
    "/{wallet_id}/ledger",
    response_model=LedgerHistoryResponse,
    summary="5. Get transaction history (ledger)",
)
def get_wallet_ledger(
    wallet_id: uuid.UUID,
    db: DBDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    Retrieves the ledger transaction history for the given wallet.
    Returns immutable audit entries ordered chronologically (newest first).
    """
    total, entries = WalletService.get_ledger_history(
        db, wallet_id=wallet_id, limit=limit, offset=offset
    )
    return LedgerHistoryResponse(
        wallet_id=wallet_id,
        total_entries=total,
        entries=entries,
    )
