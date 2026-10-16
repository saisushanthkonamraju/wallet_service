import uuid
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://127.0.0.1:8000"


def run_concurrency_test():
    print("=" * 65)
    print("OPTIMISTIC CONCURRENCY TEST: 50 concurrent debits on balance 100")
    print("=" * 65)

    # 1. Register & Login a user
    suffix = uuid.uuid4().hex[:6]
    username = f"occ_trader_{suffix}"
    password = "trader_password_123"

    reg_resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "password": password},
    )
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"

    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[1] Registered and logged in user: {username}")

    # 2. Create wallet for user
    create_resp = requests.post(
        f"{BASE_URL}/wallets",
        json={"currency": "USD"},
        headers=headers,
    )
    assert create_resp.status_code == 201, f"Failed to create wallet: {create_resp.text}"
    wallet_data = create_resp.json()
    wallet_id = wallet_data["id"]
    print(f"[2] Created wallet: {wallet_id} (Initial Version: {wallet_data.get('version')})")

    # 3. Credit 100.00
    credit_resp = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/credit",
        json={"amount": "100.0000", "description": "Initial balance"},
        headers=headers,
    )
    assert credit_resp.status_code == 200, f"Credit failed: {credit_resp.text}"
    print("[3] Credited 100.0000. Balance is now 100.0000 (Version: 2)")

    # 4. Launch 50 concurrent debits of 10.00 each
    debit_amount = "10.0000"
    num_requests = 50
    print(f"\n[4] Launching {num_requests} concurrent debit requests of {debit_amount} each...")

    results = []

    def send_debit(idx: int):
        resp = requests.post(
            f"{BASE_URL}/wallets/{wallet_id}/debit",
            json={"amount": debit_amount, "description": f"Debit #{idx}"},
            headers=headers,
        )
        return (idx, resp.status_code, resp.json())

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(send_debit, i + 1) for i in range(num_requests)]
        for f in as_completed(futures):
            results.append(f.result())
    elapsed = time.time() - start_time

    print(f"Finished {num_requests} concurrent requests in {elapsed:.2f} seconds.")

    # 5. Check results
    success_200 = [r for r in results if r[1] == 200]
    insufficient_funds_400 = [r for r in results if r[1] == 400]
    unexpected_errors = [r for r in results if r[1] not in (200, 400)]

    print("\n--- RESULTS BREAKDOWN ---")
    print(f"Successful debits (HTTP 200) : {len(success_200)} (Expected: 10)")
    print(f"Rejected debits (HTTP 400)   : {len(insufficient_funds_400)} (Expected: 40)")
    print(f"Unexpected errors            : {len(unexpected_errors)} (Expected: 0)")

    # 6. Verify Final Balance & Version
    bal_resp = requests.get(f"{BASE_URL}/wallets/{wallet_id}/balance", headers=headers)
    assert bal_resp.status_code == 200, bal_resp.text
    bal_data = bal_resp.json()
    final_balance = bal_data["balance"]
    final_version = bal_data.get("version")
    print(f"\nFinal balance from DB: {final_balance} (Expected: 0.0000)")
    print(f"Final version from DB: {final_version} (Expected: 12 -> 1 initial + 1 credit + 10 debits)")

    # 7. Verify Ledger
    ledger_resp = requests.get(f"{BASE_URL}/wallets/{wallet_id}/ledger?limit=100", headers=headers)
    assert ledger_resp.status_code == 200, ledger_resp.text
    ledger_data = ledger_resp.json()
    total_entries = ledger_data["total_entries"]
    debit_entries = [e for e in ledger_data["entries"] if e["operation_type"] == "DEBIT"]
    print(f"Total ledger entries: {total_entries} (Expected: 11 -> 1 CREDIT + 10 DEBITs)")
    print(f"Total debit entries : {len(debit_entries)} (Expected: 10)")

    assert len(success_200) == 10, f"Expected 10 successes, got {len(success_200)}"
    assert len(insufficient_funds_400) == 40, f"Expected 40 rejections, got {len(insufficient_funds_400)}"
    assert len(unexpected_errors) == 0, f"Expected 0 errors, got {unexpected_errors}"
    assert float(final_balance) == 0.0, f"Expected 0.0 balance, got {final_balance}"
    assert total_entries == 11, f"Expected 11 total entries, got {total_entries}"
    assert len(debit_entries) == 10, f"Expected 10 debit entries, got {len(debit_entries)}"
    assert final_version == 12, f"Expected version 12, got {final_version}"

    print("\n" + "=" * 65)
    print("ALL OPTIMISTIC CONCURRENCY & AUTH REQUIREMENTS PASS!")
    print("=" * 65)


if __name__ == "__main__":
    run_concurrency_test()
