"""
Seed Script — Creates demo company with realistic Vietnamese supply chain data.

Usage:
    python -m riskcast.scripts.seed

Creates:
    1 company ("Vietlog Logistics")
    1 admin user
    10 customers
    5 routes
    30 orders
    50 payments
    10 incidents
"""

import asyncio
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from riskcast.config import settings
from riskcast.db.models import (
    AlertRuleModel,
    Company,
    Customer,
    Incident,
    OmenIngestSignal,
    Order,
    Outcome,
    Payment,
    RiskAppetiteProfile,
    Route,
    Signal,
    User,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (matches auth router)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ── Data Templates ───────────────────────────────────────────────────────

CUSTOMERS = [
    {"name": "Công ty TNHH Thép Hòa Phát", "code": "HPG", "tier": "vip", "payment_terms": 45},
    {"name": "CTCP Sữa Việt Nam (Vinamilk)", "code": "VNM", "tier": "vip", "payment_terms": 30},
    {"name": "CTCP Tập đoàn Masan", "code": "MSN", "tier": "premium", "payment_terms": 30},
    {"name": "Công ty TNHH Samsung Electronics VN", "code": "SEV", "tier": "vip", "payment_terms": 60},
    {"name": "CTCP Thế giới Di động", "code": "MWG", "tier": "standard", "payment_terms": 30},
    {"name": "Công ty TNHH Nestlé Việt Nam", "code": "NES", "tier": "premium", "payment_terms": 45},
    {"name": "CTCP Gemadept", "code": "GMD", "tier": "standard", "payment_terms": 30},
    {"name": "Công ty TNHH Procter & Gamble VN", "code": "PGV", "tier": "premium", "payment_terms": 45},
    {"name": "CTCP Phân bón Cà Mau", "code": "DCM", "tier": "standard", "payment_terms": 30},
    {"name": "Công ty CP Logistics Miền Nam", "code": "SLG", "tier": "new", "payment_terms": 15},
]

ROUTES = [
    {"name": "HCM → Hải Phòng", "origin": "TP. Hồ Chí Minh", "destination": "Hải Phòng", "mode": "road", "days": 3},
    {"name": "HCM → Singapore", "origin": "Cát Lái, HCM", "destination": "Singapore", "mode": "sea", "days": 5},
    {"name": "Hà Nội → Lạng Sơn", "origin": "Hà Nội", "destination": "Lạng Sơn", "mode": "road", "days": 1},
    {"name": "Hải Phòng → Rotterdam", "origin": "Hải Phòng", "destination": "Rotterdam, NL", "mode": "sea", "days": 28},
    {"name": "Nội Bài → Shanghai", "origin": "Nội Bài, Hà Nội", "destination": "Shanghai, CN", "mode": "air", "days": 1},
]

ORDER_STATUSES = ["pending", "confirmed", "in_transit", "delivered", "cancelled"]
PAYMENT_STATUSES = ["pending", "paid", "overdue", "partial"]
INCIDENT_TYPES = [
    "delivery_delay", "cargo_damage", "customs_hold", "payment_dispute",
    "route_disruption", "documentation_error", "quality_issue",
    "container_shortage", "port_congestion", "weather_delay",
]
SEVERITIES = ["low", "medium", "high", "critical"]

SIGNAL_TYPES = [
    {"source": "payment_risk_analyzer", "signal_type": "late_payment_risk", "entity_type": "customer"},
    {"source": "route_disruption_analyzer", "signal_type": "route_disruption", "entity_type": "route"},
    {"source": "order_risk_scorer", "signal_type": "order_composite_risk", "entity_type": "order"},
    {"source": "omen_ingest", "signal_type": "geopolitical_risk", "entity_type": "route"},
    {"source": "omen_ingest", "signal_type": "weather_disruption", "entity_type": "route"},
    {"source": "payment_risk_analyzer", "signal_type": "payment_behavior_change", "entity_type": "customer"},
    {"source": "route_disruption_analyzer", "signal_type": "port_congestion", "entity_type": "route"},
    {"source": "order_risk_scorer", "signal_type": "high_value_order_risk", "entity_type": "order"},
]

ALERT_RULES = [
    {"name": "High Payment Risk", "metric": "payment_risk_score", "operator": ">=", "threshold": 70, "severity": "warning"},
    {"name": "Critical Route Disruption", "metric": "route_disruption_score", "operator": ">=", "threshold": 80, "severity": "critical"},
    {"name": "Large Order Risk", "metric": "order_composite_risk", "operator": ">=", "threshold": 60, "severity": "warning"},
    {"name": "Overdue Payments", "metric": "overdue_count", "operator": ">=", "threshold": 3, "severity": "warning"},
]

OMEN_SIGNALS = [
    {
        "title": "Red Sea shipping disruption — Houthi attacks escalate",
        "category": "geopolitical",
        "description": "Multiple container vessels rerouting via Cape of Good Hope. Freight rates HCM-Rotterdam up 40%.",
        "probability": 0.82,
        "confidence": 0.75,
    },
    {
        "title": "Typhoon approaching South China Sea",
        "category": "weather",
        "description": "Category 3 typhoon expected to reach Vietnamese coast in 48 hours. Ports Hai Phong and Cat Lai may close.",
        "probability": 0.91,
        "confidence": 0.88,
    },
    {
        "title": "Port congestion at Singapore PSA terminals",
        "category": "logistics",
        "description": "Average dwell time increased to 5.2 days. Transshipment delays affecting Vietnam-Europe routes.",
        "probability": 0.67,
        "confidence": 0.72,
    },
    {
        "title": "USD/VND exchange rate volatility spike",
        "category": "financial",
        "description": "VND depreciated 2.3% vs USD in 7 days. Payment risk for USD-denominated contracts increasing.",
        "probability": 0.58,
        "confidence": 0.65,
    },
    {
        "title": "Suez Canal transit delays due to maintenance",
        "category": "logistics",
        "description": "Planned maintenance reducing daily transit capacity by 30%. Queues building up on both sides.",
        "probability": 0.73,
        "confidence": 0.80,
    },
]


async def seed():
    """Run the seeding process."""
    engine = create_async_engine(settings.async_database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        # ── Company ──────────────────────────────────────────────────
        company = Company(
            name="Vietlog Logistics",
            slug="vietlog",
            industry="logistics",
            timezone="Asia/Ho_Chi_Minh",
            plan="professional",
        )
        session.add(company)
        await session.flush()
        company_id = company.id
        print(f"Created company: {company.name} ({company_id})")

        # ── Admin User ───────────────────────────────────────────────
        admin_user = User(
            company_id=company_id,
            email="admin@vietlog.vn",
            password_hash=hash_password("vietlog2026"),
            name="Nguyen Van Admin",
            role="admin",
        )
        session.add(admin_user)
        await session.flush()
        print(f"Created admin user: {admin_user.email}")

        # ── Test Account ──────────────────────────────────────────────
        test_user = User(
            company_id=company_id,
            email="hoangpro268@gmail.com",
            password_hash=hash_password("Hoang2672004"),
            name="Hoang Nguyen",
            role="admin",
        )
        session.add(test_user)
        await session.flush()
        print(f"Created test user: {test_user.email}")

        # ── Demo Accounts ─────────────────────────────────────────────
        demo_users = [
            ("analyst@riskcast.io", "demo", "Sarah Chen", "analyst"),
            ("manager@riskcast.io", "demo", "David Park", "manager"),
            ("executive@riskcast.io", "demo", "Minh Nguyen", "executive"),
        ]
        for email, pwd, name, role in demo_users:
            demo_user = User(
                company_id=company_id,
                email=email,
                password_hash=hash_password(pwd),
                name=name,
                role=role,
            )
            session.add(demo_user)
        await session.flush()
        print(f"Created {len(demo_users)} demo users")

        # ── Risk Appetite Profile ────────────────────────────────────
        appetite = RiskAppetiteProfile(
            company_id=company_id,
            profile={
                "payment_risk_tolerance": "medium",
                "route_risk_tolerance": "medium",
                "new_customer_policy": "cautious",
                "vip_override_enabled": True,
                "auto_alert_threshold": 0.7,
                "learned_rules": [],
            },
        )
        session.add(appetite)

        # ── Customers ────────────────────────────────────────────────
        customer_ids = []
        for c in CUSTOMERS:
            cust = Customer(
                company_id=company_id,
                name=c["name"],
                code=c["code"],
                tier=c["tier"],
                contact_email=f"{c['code'].lower()}@example.vn",
                contact_phone=f"+8490{random.randint(1000000, 9999999)}",
                payment_terms=c["payment_terms"],
            )
            session.add(cust)
            await session.flush()
            customer_ids.append(cust.id)
        print(f"Created {len(customer_ids)} customers")

        # ── Routes ───────────────────────────────────────────────────
        route_ids = []
        for r in ROUTES:
            route = Route(
                company_id=company_id,
                name=r["name"],
                origin=r["origin"],
                destination=r["destination"],
                transport_mode=r["mode"],
                avg_duration_days=Decimal(str(r["days"])),
            )
            session.add(route)
            await session.flush()
            route_ids.append(route.id)
        print(f"Created {len(route_ids)} routes")

        # ── Orders ───────────────────────────────────────────────────
        order_ids = []
        today = date.today()
        for i in range(30):
            days_ago = random.randint(0, 60)
            expected = today + timedelta(days=random.randint(-10, 30))
            status = random.choice(ORDER_STATUSES)
            actual = expected + timedelta(days=random.randint(-2, 7)) if status == "delivered" else None

            order = Order(
                company_id=company_id,
                customer_id=random.choice(customer_ids),
                route_id=random.choice(route_ids),
                order_number=f"VL-2026-{i+1:04d}",
                status=status,
                total_value=Decimal(str(random.randint(5, 500) * 1_000_000)),
                currency="VND",
                origin=random.choice(ROUTES)["origin"],
                destination=random.choice(ROUTES)["destination"],
                expected_date=expected,
                actual_date=actual,
            )
            session.add(order)
            await session.flush()
            order_ids.append(order.id)
        print(f"Created {len(order_ids)} orders")

        # ── Payments ─────────────────────────────────────────────────
        for i in range(50):
            days_ago = random.randint(0, 90)
            due = today - timedelta(days=days_ago) + timedelta(days=random.randint(0, 45))
            status = random.choice(PAYMENT_STATUSES)
            paid = due + timedelta(days=random.randint(-5, 15)) if status == "paid" else None

            payment = Payment(
                company_id=company_id,
                order_id=random.choice(order_ids) if random.random() > 0.2 else None,
                customer_id=random.choice(customer_ids),
                amount=Decimal(str(random.randint(10, 200) * 1_000_000)),
                currency="VND",
                status=status,
                due_date=due,
                paid_date=paid,
            )
            session.add(payment)
        await session.flush()
        print("Created 50 payments")

        # ── Incidents ────────────────────────────────────────────────
        for i in range(10):
            days_ago = random.randint(0, 30)
            resolved = random.random() > 0.4
            incident = Incident(
                company_id=company_id,
                order_id=random.choice(order_ids) if random.random() > 0.3 else None,
                route_id=random.choice(route_ids) if random.random() > 0.5 else None,
                customer_id=random.choice(customer_ids),
                type=random.choice(INCIDENT_TYPES),
                severity=random.choice(SEVERITIES),
                description=f"Sự cố #{i+1} — auto-generated seed data",
                resolution="Đã xử lý" if resolved else None,
                resolved_at=datetime.utcnow() - timedelta(days=random.randint(0, 5)) if resolved else None,
            )
            session.add(incident)
        await session.flush()
        print("Created 10 incidents")

        # ── Signals ────────────────────────────────────────────────
        # Use unique (source, signal_type, entity_type, entity_id) per signal
        signal_ids = []
        seen_keys = set()
        i = 0
        for sig_template in SIGNAL_TYPES:
            entity_type = sig_template["entity_type"]
            entity_pool = customer_ids if entity_type == "customer" else route_ids if entity_type == "route" else order_ids
            for entity_id in entity_pool[:3]:  # Max 3 entities per signal type
                key = (sig_template["source"], sig_template["signal_type"], entity_type, entity_id)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                days_ago = random.randint(0, 14)
                confidence = round(random.uniform(0.40, 0.95), 2)
                severity = round(random.uniform(15.0, 90.0), 2)

                signal = Signal(
                    company_id=company_id,
                    source=sig_template["source"],
                    signal_type=sig_template["signal_type"],
                    entity_type=entity_type,
                    entity_id=entity_id,
                    confidence=Decimal(str(confidence)),
                    severity_score=Decimal(str(severity)),
                    evidence={
                        "source": sig_template["source"],
                        "indicators": [f"indicator_{j}" for j in range(random.randint(1, 4))],
                        "analysis": f"Auto-generated signal #{i+1} — seed data",
                    },
                    context={"generated": True, "seed_version": "2.0"},
                    is_active=random.random() > 0.2,
                    created_at=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
                )
                session.add(signal)
                await session.flush()
                signal_ids.append(signal.id)
                i += 1
        print(f"Created {len(signal_ids)} signals")

        # ── OMEN Ingest Signals ────────────────────────────────────
        for i, omen in enumerate(OMEN_SIGNALS):
            omen_signal = OmenIngestSignal(
                signal_id=f"omen-seed-{uuid.uuid4().hex[:12]}",
                ack_id=f"ack-seed-{uuid.uuid4().hex[:12]}",
                schema_version="1.0.0",
                title=omen["title"],
                description=omen["description"],
                probability=Decimal(str(omen["probability"])),
                confidence_score=Decimal(str(omen["confidence"])),
                confidence_level="high" if omen["confidence"] > 0.7 else "medium",
                category=omen["category"],
                tags={"tags": [omen["category"], "seed"]},
                evidence={"sources": [f"source_{j}" for j in range(3)]},
                raw_payload={"title": omen["title"], "seed": True},
                ingested_at=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
                is_active=True,
                processed=random.random() > 0.3,
            )
            session.add(omen_signal)
        await session.flush()
        print(f"Created {len(OMEN_SIGNALS)} OMEN ingest signals")

        # ── Alert Rules ──────────────────────────────────────────────
        for rule in ALERT_RULES:
            alert_rule = AlertRuleModel(
                rule_id=f"rule-{uuid.uuid4().hex[:8]}",
                company_id=company_id,
                rule_name=rule["name"],
                description=f"Auto-fire when {rule['metric']} {rule['operator']} {rule['threshold']}",
                is_active=True,
                metric=rule["metric"],
                operator=rule["operator"],
                threshold=Decimal(str(rule["threshold"])),
                severity=rule["severity"],
                channels=["discord", "in_app"],
                cooldown_minutes=30,
                max_per_day=10,
            )
            session.add(alert_rule)
        await session.flush()
        print(f"Created {len(ALERT_RULES)} alert rules")

        # ── Outcomes (prediction accuracy) ────────────────────────────
        actions = ["monitor", "hedge", "reroute", "escalate", "hold"]
        outcome_types = ["risk_materialized", "risk_averted", "false_positive", "partial_loss"]
        for i in range(15):
            days_ago = random.randint(7, 60)
            predicted_risk = round(random.uniform(20.0, 90.0), 2)
            predicted_confidence = round(random.uniform(0.40, 0.95), 4)
            predicted_loss = round(random.uniform(1000, 50000), 2)
            actual_loss = round(predicted_loss * random.uniform(0.0, 1.5), 2) if random.random() > 0.4 else 0
            risk_materialized = actual_loss > 0
            was_accurate = abs(predicted_risk - (80 if risk_materialized else 20)) < 30

            outcome = Outcome(
                decision_id=f"dec-seed-{uuid.uuid4().hex[:12]}",
                company_id=company_id,
                entity_type=random.choice(["order", "customer", "route"]),
                entity_id=str(random.choice(order_ids)),
                predicted_risk_score=Decimal(str(predicted_risk)),
                predicted_confidence=Decimal(str(predicted_confidence)),
                predicted_loss_usd=Decimal(str(predicted_loss)),
                predicted_action=random.choice(actions),
                outcome_type=random.choice(outcome_types),
                actual_loss_usd=Decimal(str(actual_loss)),
                actual_delay_days=Decimal(str(round(random.uniform(0, 7), 2))) if risk_materialized else Decimal("0"),
                action_taken=random.choice(actions),
                action_followed_recommendation=random.random() > 0.3,
                risk_materialized=risk_materialized,
                prediction_error=Decimal(str(round(abs(predicted_risk - (80 if risk_materialized else 20)) / 100, 4))),
                was_accurate=was_accurate,
                value_generated_usd=Decimal(str(round(random.uniform(500, 20000), 2))) if was_accurate else Decimal("0"),
                recorded_at=datetime.utcnow() - timedelta(days=days_ago),
            )
            session.add(outcome)
        await session.flush()
        print("Created 15 outcomes")

        await session.commit()
        print("\nSeed completed successfully!")
        print(f"  Company ID: {company_id}")
        print(f"  Admin login: admin@vietlog.vn / vietlog2026")
        print(f"  Test login:  hoangpro268@gmail.com / Hoang2672004")
        print(f"  Demo logins: analyst@riskcast.io / demo")
        print(f"               manager@riskcast.io / demo")
        print(f"               executive@riskcast.io / demo")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
