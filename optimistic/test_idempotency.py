import uuid
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://127.0.0.1:8000"


def run_idempotency_test(mode_name="OPTIMISTIC"):
    print("=" * 70)
    print(f"RUNNING IDEMPOTENCY TESTS ({mode_name})")
    print("=" * 70)

    # 1. Register & Login
    suffix = uuid.uuid4().hex[:6]
    username = f"opt_idem_user_{suffix}"
    password = "secret_password_123"

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

    # 2. Create wallet
    create_resp = requests.post(
        f"{BASE_URL}/wallets",
        json={"currency": "USD"},
        headers=headers,
    )
    assert create_resp.status_code == 201, f"Create wallet failed: {create_resp.text}"
    wallet_id = create_resp.json()["id"]
    print(f"[2] Created wallet: {wallet_id}")

    # 3. Test Credit Idempotency
    credit_key = f"credit-key-{uuid.uuid4()}"
    credit_headers = {**headers, "Idempotency-Key": credit_key}
    
    print("\n[3] Testing Credit Idempotency...")
    # First credit: +50.00
    c1 = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/credit",
        json={"amount": "50.0000", "description": "Initial credit with key"},
        headers=credit_headers,
    )
    assert c1.status_code == 200, f"Credit 1 failed: {c1.text}"
    c1_entry = c1.json()
    assert float(c1_entry["balance_after"]) == 50.0
    assert c1_entry["idempotency_key"] == credit_key

    # Replay credit: same key!
    c2 = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/credit",
        json={"amount": "50.0000", "description": "Duplicate credit attempt"},
        headers=credit_headers,
    )
    assert c2.status_code == 200, f"Credit 2 replay failed: {c2.text}"
    c2_entry = c2.json()
    assert c2_entry["id"] == c1_entry["id"], "Idempotent replay did not return original entry ID!"
    assert float(c2_entry["balance_after"]) == 50.0

    # Verify balance is still 50, NOT 100
    bal = requests.get(f"{BASE_URL}/wallets/{wallet_id}/balance", headers=headers).json()
    assert float(bal["balance"]) == 50.0, f"Balance was double credited! Expected 50.0, got {bal['balance']}"
    print(" -> Credit Idempotency PASSED! Balance remains 50.0000 after duplicate request.")

    # 4. Test Debit Idempotency
    debit_key = f"debit-key-{uuid.uuid4()}"
    debit_headers = {**headers, "Idempotency-Key": debit_key}

    print("\n[4] Testing Debit Idempotency...")
    # First debit: -20.00
    d1 = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/debit",
        json={"amount": "20.0000", "description": "Debit with key"},
        headers=debit_headers,
    )
    assert d1.status_code == 200, f"Debit 1 failed: {d1.text}"
    d1_entry = d1.json()
    assert float(d1_entry["balance_after"]) == 30.0
    assert d1_entry["idempotency_key"] == debit_key

    # Replay debit: same key!
    d2 = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/debit",
        json={"amount": "20.0000", "description": "Duplicate debit attempt"},
        headers=debit_headers,
    )
    assert d2.status_code == 200, f"Debit 2 replay failed: {d2.text}"
    d2_entry = d2.json()
    assert d2_entry["id"] == d1_entry["id"], "Idempotent replay did not return original entry ID!"
    assert float(d2_entry["balance_after"]) == 30.0

    # Verify balance is still 30, NOT 10
    bal = requests.get(f"{BASE_URL}/wallets/{wallet_id}/balance", headers=headers).json()
    assert float(bal["balance"]) == 30.0, f"Balance was double debited! Expected 30.0, got {bal['balance']}"
    print(" -> Debit Idempotency PASSED! Balance remains 30.0000 after duplicate request.")

    # 5. Test Backward Compatibility: Requests WITHOUT Idempotency-Key
    print("\n[5] Testing Backward Compatibility (requests without Idempotency-Key)...")
    d_no_key = requests.post(
        f"{BASE_URL}/wallets/{wallet_id}/debit",
        json={"amount": "10.0000", "description": "No key debit"},
        headers=headers,
    )
    assert d_no_key.status_code == 200, f"Standard debit failed: {d_no_key.text}"
    assert d_no_key.json()["idempotency_key"] is None
    bal = requests.get(f"{BASE_URL}/wallets/{wallet_id}/balance", headers=headers).json()
    assert float(bal["balance"]) == 20.0
    print(" -> Non-idempotent request succeeded normally. Balance is now 20.0000.")

    # 6. Test Concurrent Requests with IDENTICAL Idempotency-Key
    print("\n[6] Testing Concurrent Requests with the SAME Idempotency-Key (Race Condition Test)...")
    shared_key = f"race-key-{uuid.uuid4()}"
    race_headers = {**headers, "Idempotency-Key": shared_key}
    num_concurrent = 20

    results = []

    def send_concurrent_debit(idx):
        resp = requests.post(
            f"{BASE_URL}/wallets/{wallet_id}/debit",
            json={"amount": "5.0000", "description": f"Race debit {idx}"},
            headers=race_headers,
        )
        return (idx, resp.status_code, resp.json())

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(send_concurrent_debit, i + 1) for i in range(num_concurrent)]
        for f in as_completed(futures):
            results.append(f.result())
    elapsed = time.time() - start_time

    print(f" -> Sent {num_concurrent} simultaneous requests in {elapsed:.2f}s")
    for idx, code, body in results:
        assert code == 200, f"Concurrent request #{idx} returned {code}: {body}"

    # All returned IDs must be identical
    entry_ids = set(r[2]["id"] for r in results)
    assert len(entry_ids) == 1, f"Expected exactly 1 unique entry ID, but got {len(entry_ids)}: {entry_ids}"

    # Balance must be exactly 20.0 - 5.0 = 15.0 (NOT 20.0 - 100.0)
    bal = requests.get(f"{BASE_URL}/wallets/{wallet_id}/balance", headers=headers).json()
    assert float(bal["balance"]) == 15.0, f"Balance error! Expected 15.0, got {bal['balance']}"
    print(f" -> Concurrency Race Idempotency PASSED! Balance is 15.0000, exactly 1 debit of 5.0 occurred across all {num_concurrent} threads.")

    # 7. Check Total Ledger Count
    ledger = requests.get(f"{BASE_URL}/wallets/{wallet_id}/ledger", headers=headers).json()
    # Ledger should contain:
    # 1 credit (Initial) + 1 debit (with key) + 1 debit (no key) + 1 debit (from the 20 race requests) = 4 total
    assert ledger["total_entries"] == 4, f"Expected 4 ledger entries, but found {ledger['total_entries']}"
    print(f"\n[7] Total ledger entries verified: {ledger['total_entries']} (Expected: 4).")

    print("\n" + "=" * 70)
    print(f"ALL IDEMPOTENCY TESTS PASSED SUCCESSFULLY ({mode_name})!")
    print("=" * 70)


if __name__ == "__main__":
    run_idempotency_test()
