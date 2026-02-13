"""Quick endpoint test script — run with: python -m riskcast.scripts.test_endpoints"""

import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8002/api/v1"


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", errors="replace"))


def main():
    passed = 0
    failed = 0

    # 1. Register
    print("=== 1. REGISTER ===")
    code, res = api("POST", "/auth/register", {
        "company_name": "Vietlog Test",
        "company_slug": "vietlog-test",
        "email": "admin@vietlog.vn",
        "password": "test12345",
        "name": "Admin User",
        "industry": "logistics",
    })
    print(f"  Status: {code}")
    if code == 200:
        token = res["access_token"]
        print(f"  Token: {token[:30]}...")
        print(f"  User: {res['name']} ({res['role']})")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1
        return

    # 2. Login
    print("\n=== 2. LOGIN ===")
    code, res = api("POST", "/auth/login", {"email": "admin@vietlog.vn", "password": "test12345"})
    print(f"  Status: {code}")
    if code == 200:
        token = res["access_token"]
        print(f"  Login OK: {res['name']}")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1

    # 3. Create Customer
    print("\n=== 3. CREATE CUSTOMER ===")
    code, res = api("POST", "/customers/", {"name": "Hoa Phat Steel", "code": "HPG", "tier": "vip"}, token)
    print(f"  Status: {code}")
    if code == 201:
        cust_id = res["id"]
        print(f"  Customer: {res['name']} (id: {cust_id[:8]}...)")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1

    # 4. List Customers
    print("\n=== 4. LIST CUSTOMERS ===")
    code, res = api("GET", "/customers/", token=token)
    print(f"  Status: {code}, Count: {len(res)}")
    passed += 1 if code == 200 else 0
    failed += 0 if code == 200 else 1

    # 5. Create Order
    print("\n=== 5. CREATE ORDER ===")
    code, res = api("POST", "/orders/", {
        "order_number": "VL-2026-0001",
        "status": "pending",
        "total_value": 50000000,
        "origin": "HCM",
        "destination": "Hai Phong",
    }, token)
    print(f"  Status: {code}")
    if code == 201:
        print(f"  Order: {res['order_number']}")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1

    # 6. Create Route
    print("\n=== 6. CREATE ROUTE ===")
    code, res = api("POST", "/routes/", {
        "name": "HCM-HP",
        "origin": "TP HCM",
        "destination": "Hai Phong",
        "transport_mode": "road",
    }, token)
    print(f"  Status: {code}")
    if code == 201:
        print(f"  Route: {res['name']}")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1

    # 7. Signals
    print("\n=== 7. LIST SIGNALS ===")
    code, res = api("GET", "/signals/", token=token)
    print(f"  Status: {code}, Total: {res.get('total', '?')}")
    passed += 1 if code == 200 else 0
    failed += 0 if code == 200 else 1

    # 8. Trigger Scan
    print("\n=== 8. TRIGGER SCAN ===")
    code, res = api("POST", "/signals/scan", token=token)
    print(f"  Status: {code}, Result: {res}")
    passed += 1 if code == 200 else 0
    failed += 0 if code == 200 else 1

    # 9. Onboarding Status
    print("\n=== 9. ONBOARDING STATUS ===")
    code, res = api("GET", "/onboarding/status", token=token)
    print(f"  Status: {code}, Completion: {res.get('completion_pct', '?')}%")
    passed += 1 if code == 200 else 0
    failed += 0 if code == 200 else 1

    # 10. Chat Sessions
    print("\n=== 10. CHAT SESSIONS ===")
    code, res = api("GET", "/chat/sessions", token=token)
    print(f"  Status: {code}, Sessions: {len(res.get('sessions', []))}")
    passed += 1 if code == 200 else 0
    failed += 0 if code == 200 else 1

    # 11. Company Info
    print("\n=== 11. GET COMPANY ===")
    code, res = api("GET", "/companies/me", token=token)
    print(f"  Status: {code}")
    if code == 200:
        print(f"  Company: {res['name']} ({res['slug']})")
        passed += 1
    else:
        print(f"  Error: {res}")
        failed += 1

    # Summary
    print(f"\n{'='*40}")
    print(f"PASSED: {passed}/{passed+failed}")
    if failed:
        print(f"FAILED: {failed}")
    else:
        print("ALL TESTS PASSED!")


if __name__ == "__main__":
    main()
