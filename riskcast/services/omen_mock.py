"""
Mock OMEN Server — Lightweight standalone service for development.

Provides realistic test signals so the full RiskCast pipeline works
without the real OMEN service.

Usage:
    python -m riskcast.services.omen_mock

Runs on port 8000 (same port OMEN would use).
"""

import random
import uuid
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OMEN Mock", version="0.1.0-mock")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Signal Templates ─────────────────────────────────────────────

SIGNAL_TEMPLATES = [
    {
        "signal_type": "port_congestion",
        "title": "Port congestion detected at {location}",
        "description": "Vessel dwell time increased by {pct}% at {location}. Average wait now {days} days.",
        "locations": ["Ho Chi Minh City", "Singapore", "Shanghai", "Busan", "Rotterdam"],
    },
    {
        "signal_type": "weather_disruption",
        "title": "Severe weather alert: {location}",
        "description": "Typhoon/storm system approaching {location}. Estimated impact window: 48-72 hours.",
        "locations": ["South China Sea", "Philippine Sea", "Bay of Bengal", "Strait of Malacca"],
    },
    {
        "signal_type": "geopolitical_risk",
        "title": "Trade restriction risk: {location}",
        "description": "New regulatory changes affecting shipping through {location}. Compliance review recommended.",
        "locations": ["Red Sea", "Suez Canal", "Taiwan Strait", "Black Sea"],
    },
    {
        "signal_type": "freight_rate_spike",
        "title": "Freight rate surge on {location} corridor",
        "description": "Spot rates up {pct}% on {location} trade lane. Capacity tightening expected.",
        "locations": ["Asia-Europe", "Transpacific", "Asia-US West Coast", "Intra-Asia"],
    },
    {
        "signal_type": "supply_chain_disruption",
        "title": "Supply chain bottleneck at {location}",
        "description": "Container shortage and congestion reported at {location}. Lead times extended by {days} days.",
        "locations": ["Hai Phong", "Cat Lai", "Cai Mep", "Da Nang", "Quy Nhon"],
    },
]


def _generate_signal(template: dict | None = None) -> dict:
    """Generate a realistic mock signal."""
    tpl = template or random.choice(SIGNAL_TEMPLATES)
    location = random.choice(tpl["locations"])
    pct = random.randint(15, 85)
    days = random.randint(2, 14)
    confidence = round(random.uniform(0.4, 0.95), 2)

    return {
        "id": str(uuid.uuid4()),
        "signal_type": tpl["signal_type"],
        "confidence": confidence,
        "severity_score": round(confidence * 100 * random.uniform(0.7, 1.0), 1),
        "evidence": {
            "source": "omen_mock",
            "location": location,
            "data_points": random.randint(5, 50),
            "last_updated": datetime.utcnow().isoformat(),
        },
        "context": {
            "location": location,
            "impact_estimate": f"{pct}% increase",
            "duration_estimate": f"{days} days",
        },
        "created_at": datetime.utcnow().isoformat(),
    }


# ── API Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "omen-mock", "version": "0.1.0-mock"}


@app.get("/api/v1/signals")
async def get_signals(
    signal_type: str | None = Query(default=None),
    min_confidence: float = Query(default=0.0),
    limit: int = Query(default=50),
):
    """Return mock signals, optionally filtered."""
    signals = []
    for _ in range(random.randint(3, min(limit, 15))):
        if signal_type:
            matching = [t for t in SIGNAL_TEMPLATES if t["signal_type"] == signal_type]
            tpl = random.choice(matching) if matching else None
            sig = _generate_signal(tpl)
        else:
            sig = _generate_signal()

        if sig["confidence"] >= min_confidence:
            signals.append(sig)

    return signals[:limit]


@app.get("/api/v1/signals/market")
async def get_market_signals(
    location: str | None = Query(default=None),
):
    """Return market-specific mock signals."""
    signals = []
    for _ in range(random.randint(1, 5)):
        sig = _generate_signal()
        if location:
            sig["context"]["location"] = location
            sig["evidence"]["location"] = location
        signals.append(sig)
    return signals


# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8003"))
    print("=" * 60)
    print(f"  OMEN Mock Server — Development Only (port {port})")
    print("  Generating realistic test signals for RiskCast")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)
