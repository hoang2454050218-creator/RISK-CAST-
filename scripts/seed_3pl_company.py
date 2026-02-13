"""
Seed realistic 3PL SME company data for Bui Xuan Hoang's account.

Transforms the account into a realistic Vietnamese 3PL company:
- Company: Nexus Logistics Vietnam (3PL / Freight Forwarding)
- 8 real customers (Vietnamese manufacturers + international brands)
- 6 active trade routes (Vietnam <-> Global)
- 25+ active orders/shipments with realistic values
- Plan: professional (Enterprise will be set separately)
"""

import asyncio
import uuid
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy import text, update
from riskcast.db.engine import get_engine, Base
from riskcast.db.models import Company, User, Customer, Route, Order


COMPANY_ID = "142ee1f0-8299-4f91-84de-eb65209cf5b5"  # Bui Xuan Hoang's Company
USER_ID = "2edb050a-8407-459c-82c2-5f51291c9eb7"      # hoangpro266@gmail.com


async def main():
    engine = get_engine()

    async with engine.begin() as conn:
        # ──────────────────────────────────────────────────────
        # 1. Update Company Profile
        # ──────────────────────────────────────────────────────
        print("[1/6] Updating company profile...")
        await conn.execute(
            text("""
                UPDATE v2_companies SET
                    name = :name,
                    slug = :slug,
                    industry = :industry,
                    timezone = :tz,
                    plan = :plan,
                    settings = :settings,
                    updated_at = NOW()
                WHERE id = :cid
            """),
            {
                "cid": COMPANY_ID,
                "name": "Nexus Logistics Vietnam",
                "slug": "nexus-logistics-vn",
                "industry": "3PL / Freight Forwarding",
                "tz": "Asia/Ho_Chi_Minh",
                "plan": "professional",
                "settings": '{"currency": "USD", "language": "vi", "notifications": {"email": true, "discord": true, "in_app": true}, "risk_appetite": "balanced", "auto_alerts": true}',
            },
        )
        print("  -> Nexus Logistics Vietnam (3PL, Professional plan)")

        # ──────────────────────────────────────────────────────
        # 2. Update User Profile
        # ──────────────────────────────────────────────────────
        print("[2/6] Updating user profile...")
        await conn.execute(
            text("""
                UPDATE v2_users SET
                    name = :name,
                    role = :role,
                    preferences = :prefs
                WHERE id = :uid
            """),
            {
                "uid": USER_ID,
                "name": "Hoang Bui",
                "role": "admin",
                "prefs": '{"theme": "dark", "language": "vi", "dashboard_layout": "professional", "notification_sound": true}',
            },
        )
        print("  -> Hoang Bui (Admin, Owner)")

        # ──────────────────────────────────────────────────────
        # 3. Delete old data for this company
        # ──────────────────────────────────────────────────────
        print("[3/6] Cleaning old data...")
        # Orders first (FK to customers and routes)
        await conn.execute(text("DELETE FROM v2_orders WHERE company_id = :cid"), {"cid": COMPANY_ID})
        await conn.execute(text("DELETE FROM v2_customers WHERE company_id = :cid"), {"cid": COMPANY_ID})
        await conn.execute(text("DELETE FROM v2_routes WHERE company_id = :cid"), {"cid": COMPANY_ID})
        print("  -> Cleaned previous data")

        # ──────────────────────────────────────────────────────
        # 4. Create Realistic Customers (3PL Clients)
        # ──────────────────────────────────────────────────────
        print("[4/6] Creating 3PL client portfolio...")
        customers = [
            {
                "id": str(uuid.uuid4()),
                "name": "TechVina Electronics",
                "code": "TVE",
                "tier": "enterprise",
                "contact_email": "logistics@techvina.vn",
                "contact_phone": "+84-28-3822-1100",
                "payment_terms": 30,
                "metadata": '{"type": "manufacturer", "industry": "Electronics", "annual_volume_teu": 480, "priority": "high", "since": "2023-06", "revenue_annual_usd": 185000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Saigon Garment Corp",
                "code": "SGC",
                "tier": "enterprise",
                "contact_email": "supply@saigongarment.com",
                "contact_phone": "+84-28-3829-5500",
                "payment_terms": 45,
                "metadata": '{"type": "manufacturer", "industry": "Textiles & Apparel", "annual_volume_teu": 720, "priority": "high", "since": "2022-11", "revenue_annual_usd": 275000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Mekong Seafood Export",
                "code": "MSE",
                "tier": "premium",
                "contact_email": "ops@mekongseafood.vn",
                "contact_phone": "+84-292-3866-100",
                "payment_terms": 15,
                "metadata": '{"type": "exporter", "industry": "Frozen Seafood", "annual_volume_teu": 360, "priority": "critical", "since": "2023-01", "revenue_annual_usd": 142000, "cold_chain": true}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "VN Furniture Works",
                "code": "VFW",
                "tier": "standard",
                "contact_email": "shipping@vnfurniture.com",
                "contact_phone": "+84-274-3825-200",
                "payment_terms": 30,
                "metadata": '{"type": "manufacturer", "industry": "Furniture & Home", "annual_volume_teu": 240, "priority": "medium", "since": "2024-03", "revenue_annual_usd": 96000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Dragon Ceramics JSC",
                "code": "DCJ",
                "tier": "standard",
                "contact_email": "export@dragonceramics.vn",
                "contact_phone": "+84-221-3865-300",
                "payment_terms": 30,
                "metadata": '{"type": "manufacturer", "industry": "Ceramics & Building", "annual_volume_teu": 180, "priority": "medium", "since": "2024-06", "revenue_annual_usd": 68000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Pacific Coffee Trading",
                "code": "PCT",
                "tier": "premium",
                "contact_email": "trade@pacificcoffee.vn",
                "contact_phone": "+84-263-3822-400",
                "payment_terms": 21,
                "metadata": '{"type": "trader", "industry": "Coffee & Agricultural", "annual_volume_teu": 300, "priority": "high", "since": "2023-09", "revenue_annual_usd": 118000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Hanoi Precision Parts",
                "code": "HPP",
                "tier": "standard",
                "contact_email": "logistics@hanoiprecision.com",
                "contact_phone": "+84-24-3855-7700",
                "payment_terms": 30,
                "metadata": '{"type": "manufacturer", "industry": "Auto Parts & Machinery", "annual_volume_teu": 150, "priority": "medium", "since": "2024-08", "revenue_annual_usd": 54000}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Green Rubber Vietnam",
                "code": "GRV",
                "tier": "standard",
                "contact_email": "export@greenrubber.vn",
                "contact_phone": "+84-271-3855-100",
                "payment_terms": 30,
                "metadata": '{"type": "exporter", "industry": "Natural Rubber", "annual_volume_teu": 200, "priority": "medium", "since": "2024-01", "revenue_annual_usd": 72000}',
            },
        ]

        for c in customers:
            await conn.execute(
                text("""
                    INSERT INTO v2_customers (id, company_id, name, code, tier, contact_email, contact_phone, payment_terms, metadata, created_at, updated_at)
                    VALUES (:id, :cid, :name, :code, :tier, :email, :phone, :terms, CAST(:meta AS jsonb), NOW(), NOW())
                """),
                {
                    "id": c["id"],
                    "cid": COMPANY_ID,
                    "name": c["name"],
                    "code": c["code"],
                    "tier": c["tier"],
                    "email": c["contact_email"],
                    "phone": c["contact_phone"],
                    "terms": c["payment_terms"],
                    "meta": c["metadata"],
                },
            )
            print(f"  -> {c['name']} ({c['code']}) [{c['tier']}]")

        # ──────────────────────────────────────────────────────
        # 5. Create Trade Routes
        # ──────────────────────────────────────────────────────
        print("[5/6] Creating trade routes...")
        routes = [
            {
                "id": str(uuid.uuid4()),
                "name": "HCMC -> Rotterdam (EU Main)",
                "origin": "Ho Chi Minh City, Vietnam (VNSGN)",
                "destination": "Rotterdam, Netherlands (NLRTM)",
                "transport_mode": "ocean",
                "avg_duration_days": 28,
                "metadata": '{"chokepoints": ["MALACCA", "SUEZ"], "carriers": ["Maersk", "MSC", "CMA CGM"], "frequency": "weekly", "avg_rate_usd_teu": 2800, "risk_level": "high"}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "HCMC -> Los Angeles (US West)",
                "origin": "Ho Chi Minh City, Vietnam (VNSGN)",
                "destination": "Los Angeles, USA (USLAX)",
                "transport_mode": "ocean",
                "avg_duration_days": 18,
                "metadata": '{"chokepoints": ["TAIWAN_STRAIT", "PACIFIC"], "carriers": ["Evergreen", "ONE", "Yang Ming"], "frequency": "weekly", "avg_rate_usd_teu": 3200, "risk_level": "medium"}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Hai Phong -> Hamburg (EU North)",
                "origin": "Hai Phong, Vietnam (VNHPH)",
                "destination": "Hamburg, Germany (DEHAM)",
                "transport_mode": "ocean",
                "avg_duration_days": 30,
                "metadata": '{"chokepoints": ["MALACCA", "SUEZ", "GIBRALTAR"], "carriers": ["Hapag-Lloyd", "MSC"], "frequency": "bi-weekly", "avg_rate_usd_teu": 2950, "risk_level": "high"}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "HCMC -> Tokyo/Yokohama (Japan)",
                "origin": "Ho Chi Minh City, Vietnam (VNSGN)",
                "destination": "Tokyo, Japan (JPTYO)",
                "transport_mode": "ocean",
                "avg_duration_days": 8,
                "metadata": '{"chokepoints": ["TAIWAN_STRAIT", "EAST_CHINA_SEA"], "carriers": ["ONE", "NYK", "K-Line"], "frequency": "2x weekly", "avg_rate_usd_teu": 1200, "risk_level": "medium"}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Da Nang -> Sydney (Australia)",
                "origin": "Da Nang, Vietnam (VNDAN)",
                "destination": "Sydney, Australia (AUSYD)",
                "transport_mode": "ocean",
                "avg_duration_days": 14,
                "metadata": '{"chokepoints": ["SOUTH_CHINA_SEA", "LOMBOK"], "carriers": ["ANL", "MSC"], "frequency": "bi-weekly", "avg_rate_usd_teu": 1800, "risk_level": "low"}',
            },
            {
                "id": str(uuid.uuid4()),
                "name": "HCMC -> Felixstowe (UK)",
                "origin": "Ho Chi Minh City, Vietnam (VNSGN)",
                "destination": "Felixstowe, UK (GBFXT)",
                "transport_mode": "ocean",
                "avg_duration_days": 32,
                "metadata": '{"chokepoints": ["MALACCA", "SUEZ", "ENGLISH_CHANNEL"], "carriers": ["Maersk", "CMA CGM", "OOCL"], "frequency": "weekly", "avg_rate_usd_teu": 3100, "risk_level": "critical"}',
            },
        ]

        route_map = {}
        for r in routes:
            await conn.execute(
                text("""
                    INSERT INTO v2_routes (id, company_id, name, origin, destination, transport_mode, avg_duration_days, is_active, metadata, created_at)
                    VALUES (:id, :cid, :name, :origin, :dest, :mode, :dur, true, CAST(:meta AS jsonb), NOW())
                """),
                {
                    "id": r["id"],
                    "cid": COMPANY_ID,
                    "name": r["name"],
                    "origin": r["origin"],
                    "dest": r["destination"],
                    "mode": r["transport_mode"],
                    "dur": r["avg_duration_days"],
                    "meta": r["metadata"],
                },
            )
            route_map[r["name"]] = r["id"]
            print(f"  -> {r['name']} ({r['avg_duration_days']}d)")

        # ──────────────────────────────────────────────────────
        # 6. Create Active Orders/Shipments
        # ──────────────────────────────────────────────────────
        print("[6/6] Creating active shipments...")

        # Customer -> Route assignments (realistic)
        customer_routes = {
            "TVE": ["HCMC -> Los Angeles (US West)", "HCMC -> Tokyo/Yokohama (Japan)"],
            "SGC": ["HCMC -> Rotterdam (EU Main)", "HCMC -> Felixstowe (UK)", "HCMC -> Los Angeles (US West)"],
            "MSE": ["HCMC -> Tokyo/Yokohama (Japan)", "Da Nang -> Sydney (Australia)"],
            "VFW": ["HCMC -> Rotterdam (EU Main)", "HCMC -> Los Angeles (US West)"],
            "DCJ": ["Hai Phong -> Hamburg (EU North)", "Da Nang -> Sydney (Australia)"],
            "PCT": ["HCMC -> Rotterdam (EU Main)", "Hai Phong -> Hamburg (EU North)"],
            "HPP": ["HCMC -> Tokyo/Yokohama (Japan)", "HCMC -> Los Angeles (US West)"],
            "GRV": ["HCMC -> Rotterdam (EU Main)", "HCMC -> Felixstowe (UK)"],
        }

        statuses = ["in_transit", "in_transit", "in_transit", "booked", "loading"]
        cargo_values_by_industry = {
            "TVE": (45000, 120000),   # Electronics: high value
            "SGC": (25000, 65000),    # Garments: medium
            "MSE": (35000, 80000),    # Seafood: medium-high
            "VFW": (20000, 55000),    # Furniture: medium
            "DCJ": (15000, 40000),    # Ceramics: lower
            "PCT": (30000, 75000),    # Coffee: medium-high
            "HPP": (40000, 95000),    # Auto parts: high
            "GRV": (18000, 45000),    # Rubber: medium-low
        }

        order_count = 0
        for cust in customers:
            code = cust["code"]
            cust_id = cust["id"]
            available_routes = customer_routes.get(code, [])

            # 2-4 active orders per customer
            num_orders = random.randint(2, 4)
            for i in range(num_orders):
                route_name = available_routes[i % len(available_routes)]
                route_id = route_map[route_name]
                val_range = cargo_values_by_industry[code]
                cargo_value = random.randint(val_range[0], val_range[1])
                status = random.choice(statuses)
                days_offset = random.randint(-5, 20)
                expected = date.today() + timedelta(days=days_offset + random.randint(10, 35))

                order_number = f"NLV-{code}-{2026}{str(i+1).zfill(3)}"
                container_count = random.choice([1, 1, 2, 2, 3])
                hs_codes = {
                    "TVE": "8471.30", "SGC": "6204.62", "MSE": "0306.17",
                    "VFW": "9403.60", "DCJ": "6907.21", "PCT": "0901.11",
                    "HPP": "8708.99", "GRV": "4001.22",
                }

                # Parse origin/dest from route
                for r in routes:
                    if r["name"] == route_name:
                        origin = r["origin"]
                        dest = r["destination"]
                        break

                meta = {
                    "container_count": container_count,
                    "container_type": "40HC" if cargo_value > 50000 else "20GP",
                    "hs_code": hs_codes.get(code, "9999.99"),
                    "carrier": random.choice(["Maersk", "MSC", "CMA CGM", "Evergreen", "ONE", "Hapag-Lloyd"]),
                    "booking_ref": f"BK{random.randint(100000,999999)}",
                    "incoterm": random.choice(["FOB", "CIF", "CFR", "FCA"]),
                    "insurance": cargo_value > 60000,
                    "commodity": cust["name"].split()[0] + " goods",
                }

                import json
                await conn.execute(
                    text("""
                        INSERT INTO v2_orders (id, company_id, customer_id, route_id, order_number, status, total_value, currency, origin, destination, expected_date, metadata, created_at, updated_at)
                        VALUES (:id, :cid, :custid, :rid, :onum, :status, :val, 'USD', :origin, :dest, :edate, CAST(:meta AS jsonb), NOW(), NOW())
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "cid": COMPANY_ID,
                        "custid": cust_id,
                        "rid": route_id,
                        "onum": order_number,
                        "status": status,
                        "val": cargo_value,
                        "origin": origin,
                        "dest": dest,
                        "edate": expected,
                        "meta": json.dumps(meta),
                    },
                )
                order_count += 1

        print(f"  -> {order_count} orders created across 8 customers")

    # ──────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────
    async with engine.connect() as conn:
        r = await conn.execute(
            text("SELECT COUNT(*) FROM v2_orders WHERE company_id = :cid"),
            {"cid": COMPANY_ID},
        )
        total_orders = r.scalar()

        r = await conn.execute(
            text("SELECT COALESCE(SUM(total_value), 0) FROM v2_orders WHERE company_id = :cid"),
            {"cid": COMPANY_ID},
        )
        total_value = r.scalar()

        r = await conn.execute(
            text("SELECT COUNT(*) FROM v2_customers WHERE company_id = :cid"),
            {"cid": COMPANY_ID},
        )
        total_customers = r.scalar()

        r = await conn.execute(
            text("SELECT COUNT(*) FROM v2_routes WHERE company_id = :cid"),
            {"cid": COMPANY_ID},
        )
        total_routes = r.scalar()

    print("\n" + "=" * 60)
    print("  NEXUS LOGISTICS VIETNAM -- Account Ready")
    print("=" * 60)
    print(f"  Company:   Nexus Logistics Vietnam (3PL)")
    print(f"  Plan:      Professional")
    print(f"  Admin:     Hoang Bui <hoangpro266@gmail.com>")
    print(f"  Customers: {total_customers}")
    print(f"  Routes:    {total_routes}")
    print(f"  Orders:    {total_orders} (${float(total_value):,.0f} total value)")
    print(f"  Industry:  3PL / Freight Forwarding")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
