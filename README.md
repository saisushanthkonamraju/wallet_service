# Wallet & Ledger Service

A production-ready REST API for wallet management and transaction ledger, built with **FastAPI** and **PostgreSQL**.

## Problem Statement

Build a wallet service with the following operations and rules:

### Operations
| # | Endpoint | Description |
|---|----------|-------------|
| 1 | `POST /wallets` | Create a wallet for a user |
| 2 | `POST /wallets/{wallet_id}/credit` | Credit money to wallet |
| 3 | `POST /wallets/{wallet_id}/debit` | Debit money from wallet |
| 4 | `GET /wallets/{wallet_id}/balance` | Get wallet balance |
| 5 | `GET /wallets/{wallet_id}/ledger` | Get transaction history |

### Rules
- **Rule 1 — Atomicity**: Every credit/debit updates the wallet balance AND creates a ledger entry in a single DB transaction.
- **Rule 2 — No negative balance**: Debit is rejected with `400` if funds are insufficient. Enforced at both application level and DB `CHECK` constraint.
- **Rule 3 — No caching**: All reads go directly to PostgreSQL — no in-memory state.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (synchronous) |
| Driver | psycopg2-binary |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## Project Structure

```
wallet/
├── app/
│   ├── config.py      # Loads settings from .env
│   ├── database.py    # SQLAlchemy engine, session, Base
│   ├── models.py      # ORM models: Wallet, LedgerEntry
│   ├── schemas.py     # Pydantic request/response schemas
│   ├── service.py     # Business logic (WalletService)
│   └── routes.py      # FastAPI route handlers
├── main.py            # App entrypoint
├── requirements.txt   # Dependencies
├── .env.example       # Environment variable template
└── README.md
```

---

## Setup

### 1. Clone and create virtual environment
```bash
git clone <repo-url>
cd wallet
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env
# Edit .env and fill in your PostgreSQL credentials
```

### 4. Create PostgreSQL database
```sql
CREATE DATABASE wallet_db;
```

### 5. Run the server
```bash
uvicorn app.main:app --reload
```

Tables are **auto-created** on first startup via `Base.metadata.create_all()`.

---

## API Usage

### Interactive Docs
Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger UI.

### Example: Create Wallet
```bash
curl -X POST http://localhost:8000/wallets \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "currency": "USD"}'
```

### Example: Credit
```bash
curl -X POST http://localhost:8000/wallets/{wallet_id}/credit \
  -H "Content-Type: application/json" \
  -d '{"amount": "500.00", "description": "initial top-up"}'
```

### Example: Debit
```bash
curl -X POST http://localhost:8000/wallets/{wallet_id}/debit \
  -H "Content-Type: application/json" \
  -d '{"amount": "200.00", "description": "purchase"}'
```

### Example: Balance
```bash
curl http://localhost:8000/wallets/{wallet_id}/balance
```

### Example: Ledger
```bash
curl http://localhost:8000/wallets/{wallet_id}/ledger
```

---

## Key Design Decisions

- **Row-level locking** (`SELECT ... FOR UPDATE`) on credit/debit prevents race conditions with concurrent requests on the same wallet.
- **`Numeric(18, 4)`** used for all monetary values — exact decimal precision, no float rounding errors.
- **Immutable ledger** — `LedgerEntry` records are never updated or deleted; they are an audit trail.
- **Atomic commit** — `db.commit()` saves both the balance change and ledger entry together; if either fails, both are rolled back.
