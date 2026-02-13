"""Quick API test — login + fetch data from real DB."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import requests
import json

BASE = "http://localhost:8001"

print("=== RiskCast V2 API Test ===\n")

# 1. Health
r = requests.get(f"{BASE}/health")
print(f"[Health] {r.status_code}: {r.json()}")

# 2. Login
r = requests.post(f"{BASE}/api/v1/auth/login", json={"email": "admin@vietlog.vn", "password": "vietlog2026"})
print(f"[Login] {r.status_code}: role={r.json().get('role')}, name={r.json().get('name')}")
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Customers
r = requests.get(f"{BASE}/api/v1/customers", headers=headers)
print(f"[Customers] {r.status_code}")
data = r.json()
if isinstance(data, list):
    print(f"  Count: {len(data)}")
    for c in data[:3]:
        print(f"  - {c.get('name')} ({c.get('code')}) tier={c.get('tier')}")
elif isinstance(data, dict):
    items = data.get("items", data.get("customers", []))
    print(f"  Count: {len(items)}")
    for c in items[:3]:
        print(f"  - {c.get('name')} ({c.get('code')}) tier={c.get('tier')}")

# 4. Orders
r = requests.get(f"{BASE}/api/v1/orders", headers=headers)
print(f"[Orders] {r.status_code}")
data = r.json()
if isinstance(data, list):
    print(f"  Count: {len(data)}")
elif isinstance(data, dict):
    items = data.get("items", data.get("orders", []))
    print(f"  Count: {len(items)}")

# 5. Signals
r = requests.get(f"{BASE}/api/v1/signals", headers=headers)
print(f"[Signals] {r.status_code}")
data = r.json()
if isinstance(data, list):
    print(f"  Count: {len(data)}")
    for s in data[:3]:
        print(f"  - [{s.get('source')}] {s.get('signal_type')} conf={s.get('confidence')}")
elif isinstance(data, dict):
    items = data.get("items", data.get("signals", []))
    print(f"  Count: {len(items)}")

# 6. Dashboard
r = requests.get(f"{BASE}/api/v1/dashboard/summary", headers=headers)
print(f"[Dashboard] {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"  {json.dumps(d, indent=2, ensure_ascii=False)[:500]}")

# 7. Analytics
r = requests.get(f"{BASE}/api/v1/analytics/risk-over-time", headers=headers)
print(f"[Analytics] {r.status_code}")

print("\n=== Test Complete ===")
