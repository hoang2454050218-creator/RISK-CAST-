"""
Seed First Customer — Vietnam Exports Co.

Creates a real company with routes and active shipments for end-to-end pipeline testing.

Usage:
    python scripts/seed_first_customer.py

What it creates:
    1. Company: "Vietnam Exports Co" (SME exporter)
    2. 2 Routes: VNHCM→NLRTM (Rotterdam), VNHCM→DEHAM (Hamburg)
    3. 5 Active Orders/Shipments on those routes
       - 3 containers VNHCM→NLRTM, cargo $45K–$80K each
       - 2 containers VNHCM→DEHAM, cargo $30K–$55K each
       - Total exposure: ~$260K
"""

import json
import sys
from datetime import date, timedelta

import httpx

BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api/v1"

# ── Step 1: Register Company ─────────────────────────────────────────


def register_company() -> dict:
    """Register Vietnam Exports Co and get JWT token."""
    print("\n── Step 1: Registering company ──")
    resp = httpx.post(
        f"{API}/auth/register",
        json={
            "company_name": "Vietnam Exports Co",
            "company_slug": "vietnam-exports",
            "industry": "maritime-logistics",
            "email": "admin@vnexports.vn",
            "password": "RiskCast2026!",
            "name": "Nguyen Van Minh",
        },
        timeout=15,
    )

    if resp.status_code == 409:
        # Already exists — try login instead
        print("  Company already exists, logging in...")
        resp = httpx.post(
            f"{API}/auth/login",
            json={
                "email": "admin@vnexports.vn",
                "password": "RiskCast2026!",
            },
            timeout=15,
        )

    if resp.status_code not in (200, 201):
        print(f"  FAILED: {resp.status_code} — {resp.text}")
        sys.exit(1)

    data = resp.json()
    print(f"  Company ID: {data['company_id']}")
    print(f"  User: {data['name']} ({data['email']})")
    print(f"  Token: {data['access_token'][:30]}...")
    return data


# ── Step 2: Create Routes ───────────────────────────────────────────


def create_routes(token: str) -> dict:
    """Create the two main shipping routes."""
    print("\n── Step 2: Creating routes ──")
    headers = {"Authorization": f"Bearer {token}"}

    routes = [
        {
            "name": "VNHCM-NLRTM (Vietnam to Rotterdam)",
            "origin": "Ho Chi Minh City, Vietnam (VNHCM)",
            "destination": "Rotterdam, Netherlands (NLRTM)",
            "transport_mode": "sea",
            "avg_duration_days": 28,
            "metadata_extra": {
                "chokepoints": ["MALACCA", "SUEZ", "RED_SEA"],
                "distance_nm": 8800,
                "carrier_options": ["MSC", "Maersk", "CMA CGM", "Evergreen"],
                "alternative_via": "Cape of Good Hope (+14 days)",
            },
        },
        {
            "name": "VNHCM-DEHAM (Vietnam to Hamburg)",
            "origin": "Ho Chi Minh City, Vietnam (VNHCM)",
            "destination": "Hamburg, Germany (DEHAM)",
            "transport_mode": "sea",
            "avg_duration_days": 30,
            "metadata_extra": {
                "chokepoints": ["MALACCA", "SUEZ", "RED_SEA"],
                "distance_nm": 9500,
                "carrier_options": ["Hapag-Lloyd", "MSC", "Maersk"],
                "alternative_via": "Cape of Good Hope (+14 days)",
            },
        },
    ]

    route_ids = {}
    for route in routes:
        resp = httpx.post(f"{API}/routes", json=route, headers=headers, timeout=15)
        if resp.status_code == 201:
            data = resp.json()
            route_ids[route["name"].split(" ")[0]] = data["id"]
            print(f"  Created: {route['name']} → {data['id']}")
        else:
            print(f"  WARN: {resp.status_code} — {resp.text[:200]}")

    return route_ids


# ── Step 3: Create Customer ─────────────────────────────────────────


def create_customer(token: str) -> str:
    """Create the main customer profile."""
    print("\n── Step 3: Creating customer ──")
    headers = {"Authorization": f"Bearer {token}"}

    resp = httpx.post(
        f"{API}/customers",
        json={
            "name": "Vietnam Exports Co — Trading Division",
            "code": "VNX-001",
            "tier": "professional",
            "contact_email": "ops@vnexports.vn",
            "contact_phone": "+84-28-3823-6789",
            "payment_terms": 45,
            "metadata_extra": {
                "risk_tolerance": "MEDIUM",
                "primary_routes": ["VNHCM-NLRTM", "VNHCM-DEHAM"],
                "relevant_chokepoints": ["RED_SEA", "SUEZ", "MALACCA"],
                "cargo_types": ["electronics", "textiles", "furniture"],
                "avg_monthly_shipments": 35,
                "avg_shipment_value_usd": 52000,
                "notification_channels": ["whatsapp", "email"],
                "whatsapp_number": "+84-901-234-567",
            },
        },
        headers=headers,
        timeout=15,
    )

    if resp.status_code == 201:
        data = resp.json()
        print(f"  Created customer: {data['name']} → {data['id']}")
        return data["id"]
    else:
        print(f"  FAILED: {resp.status_code} — {resp.text[:300]}")
        sys.exit(1)


# ── Step 4: Create Shipments (Orders) ───────────────────────────────


def create_shipments(token: str, customer_id: str, route_ids: dict) -> list:
    """Create 5 active shipments on the routes."""
    print("\n── Step 4: Creating shipments ──")
    headers = {"Authorization": f"Bearer {token}"}
    today = date.today()

    # Route IDs: get the first available ones
    rrtm_id = route_ids.get("VNHCM-NLRTM")
    deham_id = route_ids.get("VNHCM-DEHAM")

    shipments = [
        # 3 containers to Rotterdam
        {
            "customer_id": customer_id,
            "route_id": rrtm_id,
            "order_number": "VNX-2026-0201",
            "status": "in_transit",
            "total_value": 78000,
            "currency": "USD",
            "origin": "Ho Chi Minh City, Vietnam",
            "destination": "Rotterdam, Netherlands",
            "expected_date": str(today + timedelta(days=18)),
            "metadata_extra": {
                "containers": 2,
                "cargo_type": "electronics",
                "carrier": "MSC",
                "vessel": "MSC ISABELLA",
                "imo": "9839430",
                "booking_ref": "MSC-BK-20260201",
                "current_position": "South China Sea",
                "chokepoints_remaining": ["MALACCA", "RED_SEA", "SUEZ"],
                "insurance_value_usd": 82000,
            },
        },
        {
            "customer_id": customer_id,
            "route_id": rrtm_id,
            "order_number": "VNX-2026-0205",
            "status": "in_transit",
            "total_value": 45000,
            "currency": "USD",
            "origin": "Ho Chi Minh City, Vietnam",
            "destination": "Rotterdam, Netherlands",
            "expected_date": str(today + timedelta(days=22)),
            "metadata_extra": {
                "containers": 1,
                "cargo_type": "textiles",
                "carrier": "Maersk",
                "vessel": "MAERSK SENTOSA",
                "booking_ref": "MRK-BK-20260205",
                "current_position": "Indian Ocean",
                "chokepoints_remaining": ["RED_SEA", "SUEZ"],
                "insurance_value_usd": 48000,
            },
        },
        {
            "customer_id": customer_id,
            "route_id": rrtm_id,
            "order_number": "VNX-2026-0210",
            "status": "pending_departure",
            "total_value": 65000,
            "currency": "USD",
            "origin": "Ho Chi Minh City, Vietnam",
            "destination": "Rotterdam, Netherlands",
            "expected_date": str(today + timedelta(days=30)),
            "metadata_extra": {
                "containers": 2,
                "cargo_type": "furniture",
                "carrier": "CMA CGM",
                "booking_ref": "CMA-BK-20260210",
                "current_position": "VNHCM Port (not departed)",
                "chokepoints_remaining": ["MALACCA", "RED_SEA", "SUEZ"],
                "insurance_value_usd": 70000,
            },
        },
        # 2 containers to Hamburg
        {
            "customer_id": customer_id,
            "route_id": deham_id,
            "order_number": "VNX-2026-0203",
            "status": "in_transit",
            "total_value": 55000,
            "currency": "USD",
            "origin": "Ho Chi Minh City, Vietnam",
            "destination": "Hamburg, Germany",
            "expected_date": str(today + timedelta(days=20)),
            "metadata_extra": {
                "containers": 1,
                "cargo_type": "electronics",
                "carrier": "Hapag-Lloyd",
                "vessel": "HAMBURG EXPRESS",
                "booking_ref": "HL-BK-20260203",
                "current_position": "Arabian Sea",
                "chokepoints_remaining": ["RED_SEA", "SUEZ"],
                "insurance_value_usd": 58000,
            },
        },
        {
            "customer_id": customer_id,
            "route_id": deham_id,
            "order_number": "VNX-2026-0208",
            "status": "pending_departure",
            "total_value": 32000,
            "currency": "USD",
            "origin": "Ho Chi Minh City, Vietnam",
            "destination": "Hamburg, Germany",
            "expected_date": str(today + timedelta(days=35)),
            "metadata_extra": {
                "containers": 1,
                "cargo_type": "textiles",
                "carrier": "MSC",
                "booking_ref": "MSC-BK-20260208",
                "current_position": "VNHCM Port (not departed)",
                "chokepoints_remaining": ["MALACCA", "RED_SEA", "SUEZ"],
                "insurance_value_usd": 35000,
            },
        },
    ]

    created = []
    total_value = 0
    for ship in shipments:
        resp = httpx.post(f"{API}/orders", json=ship, headers=headers, timeout=15)
        if resp.status_code == 201:
            data = resp.json()
            created.append(data)
            val = float(ship["total_value"])
            total_value += val
            print(f"  {ship['order_number']}: ${val:,.0f} → {ship['metadata_extra']['carrier']} → {data['id']}")
        else:
            print(f"  WARN: {ship['order_number']}: {resp.status_code} — {resp.text[:200]}")

    print(f"\n  Total exposure: ${total_value:,.0f} across {len(created)} shipments")
    return created


# ── Summary ──────────────────────────────────────────────────────────


def print_summary(auth: dict, route_ids: dict, customer_id: str, shipments: list):
    """Print a summary of everything created."""
    print("\n" + "=" * 60)
    print("  SEED COMPLETE — Vietnam Exports Co")
    print("=" * 60)
    print(f"""
  Company:    {auth['company_id']}
  JWT Token:  {auth['access_token'][:50]}...
  Customer:   {customer_id}
  Routes:     {len(route_ids)}
  Shipments:  {len(shipments)}
  
  Login credentials:
    Email:    admin@vnexports.vn
    Password: RiskCast2026!

  API Key (dev):
    X-API-Key: riskcast-dev-key-2026
    
  Test with:
    curl -H "Authorization: Bearer {auth['access_token'][:30]}..." \\
         {API}/customers
    
    curl -H "X-API-Key: riskcast-dev-key-2026" \\
         {API}/orders
""")


# ── Main ─────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("  RISKCAST V2 — Seed First Customer")
    print("=" * 60)

    # Check server is up
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"ERROR: RISKCAST not healthy: {r.status_code}")
            sys.exit(1)
        print(f"Server: {r.json().get('service', 'riskcast')} v{r.json().get('version', '?')}")
    except Exception as e:
        print(f"ERROR: Cannot reach RISKCAST at {BASE_URL}: {e}")
        sys.exit(1)

    # Seed
    auth = register_company()
    token = auth["access_token"]
    route_ids = create_routes(token)
    customer_id = create_customer(token)
    shipments = create_shipments(token, customer_id, route_ids)

    print_summary(auth, route_ids, customer_id, shipments)


if __name__ == "__main__":
    main()
