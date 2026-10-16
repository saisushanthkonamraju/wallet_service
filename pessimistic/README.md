# Wallet & Ledger Backend — Pessimistic Concurrency Control

A production-ready financial wallet and ledger service using **Pessimistic Concurrency Control** with PostgreSQL row-level locking (`SELECT ... FOR UPDATE`).

## Concurrency Control Strategy: Pessimistic Locking
1. **Row-Level Lock (`with_for_update()`)**:
   ```sql
   SELECT * FROM wallets WHERE id = :wallet_id FOR UPDATE;
   ```
2. **Serialization at Database Level**: Concurrent requests attempting to credit or debit the same wallet queue up in PostgreSQL until the lock holder commits or rolls back.
3. **Atomic Commit**: Balance mutation and `LedgerEntry` insertion are committed together in a single transaction (`db.commit()`).

## Running & Testing
```bash
# 1. Start multi-worker server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4

# 2. Run 50 concurrent debits test
python test_concurrency.py
```
