import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.service import WalletService, AuthService
from app.schemas import (
    UserAuth,
    TokenResponse,
    WalletCreate,
    WalletResponse,
    WalletBalanceResponse,
    TransactionRequest,
    LedgerEntryResponse,
    LedgerHistoryResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
router = APIRouter(prefix="/wallets", tags=["Wallets"])

DBDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[str, Depends(get_current_user)]


# --- Auth Endpoints ---
@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(payload: UserAuth, db: DBDep):
    """Registers a new user with username and password."""
    user = AuthService.register_user(db, username=payload.username, password=payload.password)
    return {"message": f"User '{user.username}' created successfully"}


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get JWT access token",
)
def login(payload: UserAuth, db: DBDep):
    """Authenticates credentials and returns a signed JWT token."""
    token = AuthService.authenticate_user(db, username=payload.username, password=payload.password)
    return TokenResponse(access_token=token)


# --- Wallet Endpoints (Secured with JWT) ---
@router.post(
    "",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="1. Create a wallet for the authenticated user",
)
def create_wallet(payload: WalletCreate, db: DBDep, current_user: UserDep):
    """
    Creates a new wallet for the authenticated user with initial balance 0.00.
    Enforces authorization: cannot create a wallet for another user.
    """
    target_user = payload.user_id if payload.user_id else current_user
    if payload.user_id and payload.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot create wallet for another user",
        )
    return WalletService.create_wallet(db, user_id=target_user, currency=payload.currency or "USD")


@router.get(
    "/my-wallet",
    response_model=WalletResponse,
    summary="Get current user's wallet",
)
def get_my_wallet(db: DBDep, current_user: UserDep):
    """Retrieves the authenticated user's own wallet."""
    return WalletService.get_wallet_by_user_id(db, user_id=current_user, current_user=current_user)


@router.get(
    "/users/{user_id}",
    response_model=WalletResponse,
    summary="Get wallet by user ID (Only own wallet allowed)",
)
def get_wallet_by_user(user_id: str, db: DBDep, current_user: UserDep):
    """
    Retrieves the wallet for a given user_id.
    Enforces authorization: blocked if user_id is not current_user.
    """
    return WalletService.get_wallet_by_user_id(db, user_id=user_id, current_user=current_user)


@router.post(
    "/{wallet_id}/credit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="2. Credit money to wallet",
)
def credit_wallet(wallet_id: uuid.UUID, payload: TransactionRequest, db: DBDep, current_user: UserDep):
    """
    Credits money to the wallet.
    Enforces authorization: user can only credit their own wallet.
    Atomically updates wallet balance and creates an immutable ledger entry.
    """
    _, ledger_entry = WalletService.credit_wallet(
        db,
        wallet_id=wallet_id,
        amount=payload.amount,
        current_user=current_user,
        description=payload.description,
    )
    return ledger_entry


@router.post(
    "/{wallet_id}/debit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="3. Debit money from wallet",
)
def debit_wallet(wallet_id: uuid.UUID, payload: TransactionRequest, db: DBDep, current_user: UserDep):
    """
    Debits money from the wallet.
    Enforces authorization: user can only debit their own wallet.
    Guarantees balance will never go negative using row-locking and DB check constraints.
    Atomically updates wallet balance and creates an immutable ledger entry.
    """
    _, ledger_entry = WalletService.debit_wallet(
        db,
        wallet_id=wallet_id,
        amount=payload.amount,
        current_user=current_user,
        description=payload.description,
    )
    return ledger_entry


@router.get(
    "/{wallet_id}/balance",
    response_model=WalletBalanceResponse,
    summary="4. Get wallet balance",
)
def get_wallet_balance(wallet_id: uuid.UUID, db: DBDep, current_user: UserDep):
    """
    Fetches current wallet balance directly from PostgreSQL.
    Enforces authorization: user can only view their own balance.
    """
    wallet = WalletService.get_wallet_by_id(db, wallet_id=wallet_id, current_user=current_user)
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
    current_user: UserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """
    Retrieves the ledger transaction history for the given wallet.
    Enforces authorization: user can only view their own ledger.
    """
    total, entries = WalletService.get_ledger_history(
        db, wallet_id=wallet_id, current_user=current_user, limit=limit, offset=offset
    )
    return LedgerHistoryResponse(
        wallet_id=wallet_id,
        total_entries=total,
        entries=entries,
    )
