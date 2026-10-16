# Wallet & Ledger Backend Service

A production-ready, highly concurrent financial wallet and transaction ledger service built with **Python**, **FastAPI**, and **PostgreSQL**.

---

## Table of Contents
- [Overview & Phases](#overview--phases)
  - [Phase 1: Core Wallet & Ledger](#phase-1-core-wallet--ledger)
  - [Phase 2: Concurrency & Consistency](#phase-2-concurrency--consistency)
  - [Phase 3: JWT Authentication & Authorization](#phase-3-jwt-authentication--authorization)
- [Tech Stack](#tech-stack)
- [Project Architecture & Directory Structure](#project-architecture--directory-structure)
- [Environment Configuration](#environment-configuration)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Key Engineering Decisions](#key-engineering-decisions)
- [Testing & Verification](#testing--verification)

---

## Overview & Phases

### Phase 1: Core Wallet & Ledger
- **Wallet per User**: 1:1 relationship between user and wallet.
- **Operations Supported**:
  - `POST /wallets`: Create a wallet for a user.
  - `POST /wallets/{wallet_id}/credit`: Credit money to wallet.
  - `POST /wallets/{wallet_id}/debit`: Debit money from wallet.
  - `GET /wallets/{wallet_id}/balance`: Get real-time wallet balance.
  - `GET /wallets/{wallet_id}/ledger`: Get immutable transaction history.
- **Core Rules**:
  - **Rule 1 (Atomicity)**: Every balance update and ledger entry insertion are committed together in a single database transaction.
  - **Rule 2 (Non-negative Balance)**: Debits that exceed the current balance are rejected with `HTTP 400 Insufficient funds`. Double-enforced at the application level and via PostgreSQL `CHECK (balance >= 0)`.
  - **Rule 3 (Direct Database Reads)**: All reads query PostgreSQL directly—no in-memory caching or state.

---

### Phase 2: Concurrency & Consistency
- **Scenario Handled**: A wallet with balance `100.00` receives **50 concurrent debit requests** of `10.00` each simultaneously across multiple workers.
- **Behavior**:
  - Exactly **10 debits succeed** ($10 \times 10 = 100$).
  - Exactly **40 debits are rejected** with `HTTP 400 Insufficient funds`.
  - Final balance is strictly **`0.0000`** (never negative).
  - Total debit ledger entries in PostgreSQL equals **exactly 10**.
- **Mechanisms**:
  - **Pessimistic Row-Level Locking (`SELECT ... FOR UPDATE`)**: Synchronizes concurrent requests at the database engine level across multiple processes.
  - **Connection Pool Tuning**: `pool_size=25, max_overflow=35, pool_timeout=30` accommodates high-concurrency traffic without connection starvation.

---

### Phase 3: JWT Authentication & Authorization
- **Authentication**:
  - `POST /auth/register`: Creates a user with `bcrypt`-salted password hashing.
  - `POST /auth/login`: Validates credentials and issues a signed, stateless JSON Web Token (JWT) using `HS256`.
- **Token Validation**:
  - All wallet APIs require `Authorization: Bearer <token>`.
  - Handled via FastAPI's `HTTPBearer` and `get_current_user` dependency.
  - Missing, forged, or expired tokens are rejected with `HTTP 401 Unauthorized`.
- **Resource Ownership Authorization**:
  - Users can only access and modify their own wallet.
  - Attempts to credit, debit, view balance, or inspect the ledger of another user's wallet are blocked with `HTTP 403 Forbidden`.

---

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Framework** | FastAPI (Python 3.10+) | High performance, automatic OpenAPI documentation, clean dependency injection. |
| **Database** | PostgreSQL | ACID compliance, native row-level locking (`FOR UPDATE`), check constraints, and native UUID support. |
| **ORM** | SQLAlchemy (Synchronous) | Reliable connection pooling, clean session lifecycle, and robust transaction management. |
| **DB Driver** | `psycopg2-binary` | Battle-tested, blocking C-extension driver for PostgreSQL. |
| **Authentication** | PyJWT | Lightweight, stateless JWT encoding/decoding. |
| **Password Hashing** | `bcrypt` | Adaptive, slow hashing with automatic per-password salting to prevent rainbow table attacks. |
| **Validation** | Pydantic v2 | Strict schema validation, request payload checking, and response serialization. |
| **ASGI Server** | Uvicorn | High-throughput server with multi-worker process management. |

---

## Project Architecture & Directory Structure

```
wallet/
├── app/
│   ├── __init__.py
│   ├── config.py         # Environment variables & JWT configuration (Strictly from .env)
│   ├── database.py       # SQLAlchemy engine, connection pooling, Base, and get_db()
│   ├── models.py         # ORM models: User, Wallet, LedgerEntry with constraints & indexes
│   ├── schemas.py        # Pydantic schemas for request validation & response formatting
│   ├── auth.py           # Bcrypt password hashing & PyJWT token creation/validation
│   ├── service.py        # Business logic: row locking, atomicity, and ownership checks
│   ├── routes.py         # FastAPI HTTP endpoints for /auth and /wallets
│   └── main.py           # Application entrypoint & table auto-creation
├── .env                  # Secrets & DB credentials (Git-ignored)
├── .env.example          # Environment variable template
├── .gitignore            # Excludes .env, venv, and __pycache__
├── requirements.txt      # Project dependencies
└── README.md             # Documentation
```

---

## Environment Configuration

Create a `.env` file in the project root directory:

```env
DATABASE_URL=postgresql+psycopg2://postgres:Sai12345$@localhost:5432/wallet_db
APP_ENV=development
JWT_SECRET=supersecretkey_for_jwt_signing_12345
```

> **Security Note:** Both `DATABASE_URL` and `JWT_SECRET` are read using `os.environ[...]` in `config.py`. If either is missing, the application **fails fast** on startup with a loud `KeyError`.

---

## Installation & Setup

### 1. Clone the repository and navigate to the project
```bash
git clone <repository-url>
cd wallet
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create the PostgreSQL Database
Make sure PostgreSQL is running on your machine, then create the database:
```sql
CREATE DATABASE wallet_db;
```

---

## Running the Application

### Development Mode (Single Worker with Auto-Reload)
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Multi-Worker Mode (For Concurrency Testing)
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

> **Note on Database Tables:** SQLAlchemy automatically creates all tables (`users`, `wallets`, `ledger_entries`) and constraints on first startup via `Base.metadata.create_all(bind=engine)` in `main.py`.

---

## API Reference

Once the server is running, open **Swagger UI** in your browser:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

### Authentication Endpoints
| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/auth/register` | Register a new user with username and password | No |
| `POST` | `/auth/login` | Authenticate and receive a JWT access token | No |

### Wallet Endpoints (Secured with JWT)
| Method | Endpoint | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/wallets` | Create a wallet for the authenticated user | **Yes (Bearer)** |
| `GET` | `/wallets/my-wallet` | Get the authenticated user's wallet | **Yes (Bearer)** |
| `POST` | `/wallets/{wallet_id}/credit` | Credit money to own wallet (Atomic + Row Locked) | **Yes (Bearer)** |
| `POST` | `/wallets/{wallet_id}/debit` | Debit money from own wallet (Atomic + Overdraft Check) | **Yes (Bearer)** |
| `GET` | `/wallets/{wallet_id}/balance` | Get real-time balance directly from DB | **Yes (Bearer)** |
| `GET` | `/wallets/{wallet_id}/ledger` | Get chronologically sorted transaction history | **Yes (Bearer)** |
| `GET` | `/wallets/users/{user_id}` | Lookup wallet by username (Own user only) | **Yes (Bearer)** |

---

## Key Engineering Decisions

### 1. Concurrency Control with Pessimistic Row Locking
- When crediting or debiting, `service.py` executes:
  ```python
  wallet = db.query(Wallet).filter(Wallet.id == wallet_id).with_for_update().first()
  ```
  This generates `SELECT ... FOR UPDATE` in PostgreSQL.
- It serializes concurrent transactions on the exact wallet row at the database level.
- Multi-process Uvicorn workers queue up cleanly in PostgreSQL, ensuring that transactions always read the latest committed balance.

### 2. Double-Layer Protection Against Negative Balance
1. **Application Layer**: `if wallet.balance < amount: raise HTTPException(400, "Insufficient funds")`
2. **Database Layer**: `CheckConstraint("balance >= 0", name="check_wallet_balance_non_negative")`
   Even if an application-level bug occurred, PostgreSQL physically rejects transactions that result in negative balances.

### 3. Exact Monetary Representation (`Numeric(18, 4)`)
- Balances and transaction amounts use SQLAlchemy `Numeric(18, 4)`, mapping to Python `Decimal` and PostgreSQL `NUMERIC`.
- Floating-point types (`float`) are completely avoided to prevent binary rounding inaccuracies in financial accounting.

### 4. Stateless JWT Authentication & Ownership Checks
- JWT tokens are signed using `HS256` and verified in memory via `PyJWT`.
- The user ID is stored in the token's standard `sub` claim.
- Before executing any operation on `/wallets/{wallet_id}/...`, the service layer runs `_verify_ownership(wallet, current_user)`, blocking cross-user tampering with `HTTP 403 Forbidden`.

---

## Testing & Verification

### Interactive Swagger UI Testing
1. Visit `http://127.0.0.1:8000/docs`.
2. Register a user via `POST /auth/register`.
3. Log in via `POST /auth/login` and copy the `access_token`.
4. Click the green **Authorize 🔓** button at the top of Swagger, paste the token, and click **Authorize**.
5. All wallet endpoints are now unlocked and authenticated!

### Automated Test Suites
You can run automated test scripts using Python:
```bash
# 1. Run Phase 3 Auth & Authorization verification (Tests 401s, 403s, and own wallet ops)
python test_auth.py

# 2. Run Phase 2 Concurrency verification (50 concurrent debits on balance 100)
python test_concurrency.py
```
