"""
Full Pipeline End-to-End Test.

Runs the complete RISKCAST pipeline:
  OMEN (live signals) -> Chokepoint Detection -> Order Matching -> Risk Assessment -> Decision Generation -> Alerts

Usage:
    python scripts/test_full_pipeline.py

Requires: RISKCAST on port 8001, OMEN on port 8000
"""

import json
import sys
import time

import httpx

BASE = "http://localhost:8001"
API = f"{BASE}/api/v1"
HEADERS = {"X-API-Key": "riskcast-dev-key-2026", "Content-Type": "application/json"}


def check_services():
    """Check RISKCAST and OMEN are running."""
    print("=" * 70)
    print("  RISKCAST V2 -- Full Pipeline End-to-End Test")
    print("=" * 70)

    # RISKCAST
    try:
        r = httpx.get(f"{BASE}/health", timeout=5)
        info = r.json()
        print(f"  RISKCAST: {info.get('service')} v{info.get('version')} [OK]")
    except Exception as e:
        print(f"  RISKCAST: OFFLINE ({e})")
        sys.exit(1)

    # OMEN
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5, follow_redirects=True)
        print(f"  OMEN:     status={r.status_code} [OK]")
    except Exception as e:
        print(f"  OMEN:     OFFLINE ({e})")
        sys.exit(1)


def check_data():
    """Check seeded data exists."""
    print("\n-- Checking seeded data --")
    r = httpx.get(f"{API}/orders", headers=HEADERS, timeout=10)
    orders = r.json()
    vnx = [o for o in orders if o["order_number"].startswith("VNX")]
    print(f"  Orders: {len(orders)} total, {len(vnx)} VNX shipments")

    r = httpx.get(f"{API}/customers", headers=HEADERS, timeout=10)
    customers = r.json()
    print(f"  Customers: {len(customers)}")

    r = httpx.get(f"{API}/routes", headers=HEADERS, timeout=10)
    routes = r.json()
    vnhcm = [rt for rt in routes if "VNHCM" in rt.get("name", "")]
    print(f"  Routes: {len(routes)} total, {len(vnhcm)} VNHCM routes")

    if not vnx:
        print("  WARNING: No VNX shipments found. Run seed script first!")
        print("  python scripts/seed_first_customer.py")
        sys.exit(1)

    return vnx


def run_pipeline():
    """Run the pipeline process endpoint."""
    print("\n-- Running Pipeline: OMEN -> Risk -> Decisions --")
    start = time.time()

    r = httpx.post(
        f"{API}/pipeline/process",
        json={"min_confidence": 0.0, "limit": 50},
        headers=HEADERS,
        timeout=120,
    )

    elapsed = (time.time() - start) * 1000
    if r.status_code != 200:
        print(f"  FAILED: {r.status_code} - {r.text[:300]}")
        sys.exit(1)

    result = r.json()
    print(f"  Status: {result['status']}")
    print(f"  OMEN Signals Fetched: {result['omen_signals_fetched']}")
    print(f"  Signals with Chokepoints: {result['signals_with_chokepoints']}")
    print(f"  Orders Matched: {result['total_orders_matched']}")
    print(f"  Signals Upserted: {result['total_signals_upserted']}")
    print(f"  DECISIONS GENERATED: {result['total_decisions_generated']}")
    print(f"  Processing Time: {result['processing_time_ms']:.0f}ms (wall: {elapsed:.0f}ms)")

    return result


def show_signals(result):
    """Show matched signals."""
    matched = [s for s in result["processed_signals"] if s["matched_orders"]]
    if not matched:
        print("\n  No signals matched any orders.")
        return

    print(f"\n-- Matched Signals ({len(matched)}) --")
    for sig in matched:
        cps = ", ".join(sig["detected_chokepoints"])
        print(f"\n  SIGNAL: {sig['title']}")
        print(f"    Probability: {sig['probability']:.1%}")
        print(f"    Confidence: {sig['confidence']:.1%}")
        print(f"    Chokepoints: {cps}")
        print(f"    Matched Orders: {len(sig['matched_orders'])}")
        for mo in sig["matched_orders"]:
            print(f"      -> {mo['order_number']}: ${mo['cargo_value_usd']:,.0f} to {mo['destination']}")
            print(f"         Overlap: {', '.join(mo['matched_chokepoints'])}")


def show_decisions(result):
    """Show generated decisions."""
    decisions = result.get("decisions", [])
    if not decisions:
        print("\n  No decisions generated.")
        return

    print(f"\n{'=' * 70}")
    print(f"  DECISIONS GENERATED: {len(decisions)}")
    print(f"{'=' * 70}")

    # Deduplicate by entity_id (same order may have multiple decisions from different signals)
    seen = set()
    unique_decisions = []
    for d in decisions:
        if d["entity_id"] not in seen:
            seen.add(d["entity_id"])
            unique_decisions.append(d)

    for i, d in enumerate(unique_decisions[:5], 1):
        sev = d["severity"].upper()
        print(f"\n  Decision {i}/{len(unique_decisions)}: {d['decision_id']}")
        print(f"  Severity: {sev} | Risk Score: {d['risk_score']:.1f}/100 | Confidence: {d['confidence']:.1%}")
        print(f"  Summary: {d['situation_summary'][:200]}")
        print(f"  ")
        ra = d["recommended_action"]
        print(f"  RECOMMENDED ACTION: {ra['action_type']}")
        print(f"    {ra['description']}")
        print(f"    Cost: ${ra['estimated_cost_usd']:,.0f} | Benefit: ${ra['estimated_benefit_usd']:,.0f}")
        print(f"    Net Value: ${ra['net_value']:,.0f} | Success: {ra['success_probability']:.0%}")
        if ra.get("deadline"):
            print(f"    Deadline: {ra['deadline']}")
        print(f"  ")
        print(f"  INACTION COST: ${d['inaction_cost']:,.0f}")
        print(f"  {d['inaction_risk']}")
        print(f"  ")
        print(f"  Alternatives: {len(d['alternative_actions'])}")
        for alt in d["alternative_actions"][:3]:
            print(f"    - {alt['action_type']}: ${alt['estimated_cost_usd']:,.0f} cost, ${alt['net_value']:,.0f} net")
        print(f"  Human Review: {d['needs_human_review']}")
        print(f"  Valid Until: {d.get('valid_until', 'N/A')}")


def check_dashboard():
    """Verify dashboard has real data."""
    print(f"\n-- Dashboard Summary --")
    r = httpx.get(f"{API}/dashboard/summary", headers=HEADERS, timeout=10)
    d = r.json()
    print(f"  Orders: {d['total_orders']}")
    print(f"  Active Signals: {d['active_signals']}")
    print(f"  Critical: {d['critical_signals']}")
    print(f"  Orders at Risk: {d['orders_at_risk']}")
    print(f"  Revenue: ${d['total_revenue']:,.0f}")
    print(f"  Customers: {d['total_customers']}")
    print(f"  Data Freshness: {d['data_freshness']['staleness_level']}")


def main():
    check_services()
    check_data()
    result = run_pipeline()
    show_signals(result)
    show_decisions(result)
    check_dashboard()

    print(f"\n{'=' * 70}")
    print("  END-TO-END PIPELINE TEST COMPLETE")
    print(f"{'=' * 70}")
    print(f"""
  Summary:
    - OMEN: {result['omen_signals_fetched']} live signals fetched
    - Chokepoints detected: {result['signals_with_chokepoints']}
    - Orders matched: {result['total_orders_matched']}
    - Decisions generated: {result['total_decisions_generated']}
    - Frontend: http://localhost:5173/dashboard

  Login credentials for frontend:
    Email:    admin@vnexports.vn
    Password: RiskCast2026!
""")


if __name__ == "__main__":
    main()
