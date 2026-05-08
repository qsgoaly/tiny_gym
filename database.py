import json
import time

import numpy as np

# --- Heavy in-memory "index" (~1.46 GB) ---
# 14000 x 14000 float64 = 14000 * 14000 * 8 bytes ≈ 1.46 GB
print("[DB] Allocating heavy database index (~1.5 GB) ...")
_HEAVY_INDEX = np.random.RandomState(42).random((14000, 14000))
print("[DB] Database index ready.")

# --- User records ---
USERS = {
    "U001": {"name": "Alice Johnson", "dob": "1985-03-15", "ssn_last4": "1234"},
    "U002": {"name": "Bob Smith", "dob": "1990-07-22", "ssn_last4": "5678"},
    "U003": {"name": "Carol Williams", "dob": "1978-11-03", "ssn_last4": "9012"},
    "U004": {"name": "David Brown", "dob": "1995-01-30", "ssn_last4": "3456"},
    "U005": {"name": "Emily Davis", "dob": "1982-06-18", "ssn_last4": "7890"},
    "U006": {"name": "Frank Miller", "dob": "1988-09-25", "ssn_last4": "2345"},
    "U007": {"name": "Grace Wilson", "dob": "1993-04-12", "ssn_last4": "6789"},
    "U008": {"name": "Henry Moore", "dob": "1975-12-08", "ssn_last4": "0123"},
    "U009": {"name": "Irene Taylor", "dob": "1987-02-14", "ssn_last4": "4567"},
    "U010": {"name": "Jack Anderson", "dob": "1991-08-07", "ssn_last4": "8901"},
    "U011": {"name": "Karen Thomas", "dob": "1980-05-21", "ssn_last4": "2346"},
    "U012": {"name": "Leo Jackson", "dob": "1996-10-16", "ssn_last4": "6780"},
    "U013": {"name": "Mia White", "dob": "1984-07-29", "ssn_last4": "1357"},
    "U014": {"name": "Nathan Harris", "dob": "1992-03-04", "ssn_last4": "2468"},
    "U015": {"name": "Olivia Martin", "dob": "1977-11-19", "ssn_last4": "3579"},
}

# --- Account records ---
ACCOUNTS = {
    "ACC-10001": {"user_id": "U001", "balance": 15234.56, "account_type": "checking"},
    "ACC-10002": {"user_id": "U001", "balance": 89012.34, "account_type": "savings"},
    "ACC-10003": {"user_id": "U002", "balance": 3421.00, "account_type": "checking"},
    "ACC-10004": {"user_id": "U003", "balance": 67890.12, "account_type": "checking"},
    "ACC-10005": {"user_id": "U003", "balance": 12045.67, "account_type": "savings"},
    "ACC-10006": {"user_id": "U004", "balance": 890.45, "account_type": "checking"},
    "ACC-10007": {"user_id": "U005", "balance": 45678.90, "account_type": "savings"},
    "ACC-10008": {"user_id": "U006", "balance": 23456.78, "account_type": "checking"},
    "ACC-10009": {"user_id": "U007", "balance": 5678.90, "account_type": "checking"},
    "ACC-10010": {"user_id": "U007", "balance": 34567.12, "account_type": "savings"},
    "ACC-10011": {"user_id": "U008", "balance": 78901.23, "account_type": "checking"},
    "ACC-10012": {"user_id": "U009", "balance": 1234.56, "account_type": "checking"},
    "ACC-10013": {"user_id": "U010", "balance": 56789.01, "account_type": "savings"},
    "ACC-10014": {"user_id": "U011", "balance": 9012.34, "account_type": "checking"},
    "ACC-10015": {"user_id": "U012", "balance": 43210.98, "account_type": "checking"},
    "ACC-10016": {"user_id": "U013", "balance": 7654.32, "account_type": "savings"},
    "ACC-10017": {"user_id": "U014", "balance": 21098.76, "account_type": "checking"},
    "ACC-10018": {"user_id": "U015", "balance": 65432.10, "account_type": "checking"},
    "ACC-10019": {"user_id": "U015", "balance": 10987.65, "account_type": "savings"},
}


def _simulate_heavy_search(query_seed: float) -> None:
    """Run an expensive computation on the large numpy array to simulate a
    heavy database index scan. Guarantees >= 2 seconds wall-clock time and
    forces real memory access across the 1.46 GB array."""
    start = time.time()

    row_idx = int(abs(query_seed) * 13999) % 14000
    query_vector = _HEAVY_INDEX[row_idx]

    norms = np.linalg.norm(_HEAVY_INDEX, axis=1)
    query_norm = np.linalg.norm(query_vector)
    similarities = _HEAVY_INDEX @ query_vector / (norms * query_norm + 1e-10)
    _ = np.argsort(similarities)[-100:]

    elapsed = time.time() - start
    remaining = 2.0 - elapsed
    if remaining > 0:
        time.sleep(remaining)


def verify_identity(name: str, date_of_birth: str, ssn_last_4: str) -> str:
    """Verify a customer's identity against the bank database.

    Returns a JSON string with verification result.
    """
    print(f"[DB] verify_identity called — scanning index ...")
    _simulate_heavy_search(hash(name) / 1e18)

    for user_id, info in USERS.items():
        if (
            info["name"].lower() == name.lower()
            and info["dob"] == date_of_birth
            and info["ssn_last4"] == ssn_last_4
        ):
            print(f"[DB] Identity verified: {user_id}")
            return json.dumps({"verified": True, "user_id": user_id})

    print("[DB] Identity verification failed.")
    return json.dumps({
        "verified": False,
        "reason": "No matching customer found. Please check the provided information.",
    })


def get_account_balance(user_id: str) -> str:
    """Retrieve account balance(s) for a verified customer.

    Returns a JSON string with account details.
    """
    print(f"[DB] get_account_balance called for {user_id} — scanning index ...")
    _simulate_heavy_search(hash(user_id) / 1e18)

    accounts = []
    for acc_num, acc_info in ACCOUNTS.items():
        if acc_info["user_id"] == user_id:
            accounts.append({
                "account_number": acc_num,
                "account_type": acc_info["account_type"],
                "balance": acc_info["balance"],
            })

    if not accounts:
        print(f"[DB] No accounts found for {user_id}")
        return json.dumps({"error": f"No accounts found for user {user_id}"})

    print(f"[DB] Found {len(accounts)} account(s) for {user_id}")
    return json.dumps({"accounts": accounts})
