# Wallet & Ledger Backend — Optimistic Concurrency Control (OCC)

A production-ready financial wallet and ledger service using **Optimistic Concurrency Control (OCC)** with version checking (`version` column + Compare-and-Swap) and retry handling.

## Concurrency Control Strategy: Optimistic Locking
1. **Version Column**: Every row in `wallets` maintains an integer `version` initialized to `1`.
2. **Lock-Free Read**: Transactions read the wallet balance and `current_version` without holding a database row lock (`SELECT` without `FOR UPDATE`).
3. **Compare-and-Swap (CAS) Atomic Update**:
   ```sql
   UPDATE wallets
   SET balance = :new_balance,
       version = :current_version + 1,
       updated_at = NOW()
   WHERE id = :wallet_id
     AND version = :current_version;
   ```
4. **Conflict Detection & Retry**:
   - If `result.rowcount == 0`, another concurrent transaction updated the wallet first. The session rolls back (`db.rollback()`) and retries with the fresh balance and version.
   - If `result.rowcount == 1`, the update succeeded! The corresponding `LedgerEntry` is inserted and committed atomically in the same transaction.

## Running & Testing
```bash
# 1. Start multi-worker server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4

# 2. Run 50 concurrent debits test
python test_concurrency.py
```
