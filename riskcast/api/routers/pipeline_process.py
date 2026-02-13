"""
Pipeline Process — End-to-end OMEN → Signal → Risk → Decision pipeline.

POST /api/v1/pipeline/process
    Fetch OMEN signals → detect chokepoints → match to orders → assess risk → generate decisions.

This is the CORE of RISKCAST. One API call turns raw OMEN intelligence into
actionable decisions with costs, deadlines, and alternatives.
"""

import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.alerting.auto_trigger import on_scan_completed
from riskcast.alerting.schemas import AlertRecord
from riskcast.analyzers.base import InternalSignal
from riskcast.api.deps import get_company_id, get_db
from riskcast.config import settings
from riskcast.db.models import Order, Route, Signal
from riskcast.decisions.engine import DecisionEngine
from riskcast.decisions.schemas import Decision
from riskcast.services.omen_client import OmenClient, OmenSignal
from riskcast.services.signal_service import SignalService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

# ── Chokepoint keyword detection ──────────────────────────────────────

CHOKEPOINT_KEYWORDS: dict[str, list[str]] = {
    "RED_SEA": [
        "red sea", "houthi", "bab-el-mandeb", "bab el mandeb", "yemen",
        "aden", "gulf of aden",
    ],
    "SUEZ": [
        "suez", "suez canal", "ever given", "canal blockage",
    ],
    "MALACCA": [
        "malacca", "strait of malacca", "singapore strait", "taiwan",
        "china blockade", "south china sea", "taiwan strait",
    ],
    "HORMUZ": [
        "hormuz", "strait of hormuz", "iran", "persian gulf",
        "iran sanctions", "iran navy",
    ],
    "PANAMA": [
        "panama", "panama canal", "gatun", "drought panama",
    ],
    "CAPE": [
        "cape of good hope", "cape route", "south africa",
    ],
    "DARDANELLES": [
        "dardanelles", "bosphorus", "turkish strait", "black sea",
    ],
}


def detect_chokepoints(signal: OmenSignal) -> list[str]:
    """
    Detect chokepoints from signal text and geographic data.

    Combines:
    1. Geographic chokepoints from OMEN signal (if populated)
    2. Keyword-based detection from title + description + context
    """
    chokepoints: set[str] = set()

    # From OMEN geographic data
    geo_cps = signal.context.get("chokepoints", [])
    for cp in geo_cps:
        if isinstance(cp, str):
            chokepoints.add(cp.upper().replace(" ", "_"))

    # Keyword-based detection from text
    text_to_scan = " ".join([
        signal.title.lower(),
        signal.description.lower(),
        str(signal.context).lower(),
        str(signal.evidence).lower(),
    ])

    for chokepoint_name, keywords in CHOKEPOINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_to_scan:
                chokepoints.add(chokepoint_name)
                break

    return list(chokepoints)


# ── Request / Response schemas ─────────────────────────────────────────

class PipelineProcessRequest(BaseModel):
    """Request to process OMEN signals through the pipeline."""
    min_confidence: float = Field(default=0.3, ge=0, le=1, description="Minimum signal confidence to process")
    limit: int = Field(default=50, ge=1, le=200, description="Max OMEN signals to fetch")
    entity_types: list[str] = Field(default=["order"], description="Entity types to match (order, route, customer)")


class MatchedOrder(BaseModel):
    """An order matched to an OMEN signal."""
    order_id: str
    order_number: str
    route_name: str
    cargo_value_usd: float
    destination: str
    matched_chokepoints: list[str]
    status: str


class ProcessedSignal(BaseModel):
    """Result of processing a single OMEN signal."""
    signal_id: str
    title: str
    probability: float
    confidence: float
    severity_score: float
    detected_chokepoints: list[str]
    matched_orders: list[MatchedOrder]
    decisions_generated: int
    signals_upserted: int


class AlertSummary(BaseModel):
    """Summary of alerts fired during pipeline processing."""
    total_alerts_fired: int = 0
    critical_alerts: int = 0
    high_alerts: int = 0
    channels_dispatched: list[str] = Field(default_factory=list)
    alert_ids: list[str] = Field(default_factory=list)


class PipelineProcessResponse(BaseModel):
    """Result of processing OMEN signals through the pipeline."""
    status: str
    omen_signals_fetched: int
    signals_with_chokepoints: int
    total_orders_matched: int
    total_signals_upserted: int
    total_decisions_generated: int
    alerts: AlertSummary = Field(default_factory=AlertSummary)
    processed_signals: list[ProcessedSignal]
    decisions: list[Decision]
    processing_time_ms: float
    timestamp: str


# ── Pipeline Process endpoint ──────────────────────────────────────────

@router.post("/process", response_model=PipelineProcessResponse)
async def process_pipeline(
    body: PipelineProcessRequest = PipelineProcessRequest(),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Run the end-to-end pipeline: OMEN → Signal → Risk → Decision.

    Steps:
    1. Fetch live signals from OMEN
    2. Detect chokepoints from signal text
    3. Match signals to orders whose routes pass through affected chokepoints
    4. Upsert signals into DB linked to matched orders
    5. Generate decisions for affected orders via DecisionEngine
    6. Return comprehensive results

    This endpoint transforms raw OMEN intelligence into actionable decisions.
    """
    start = datetime.utcnow()
    cid = str(company_id)

    # ── 1. Fetch OMEN signals ────────────────────────────────────────
    omen = OmenClient(base_url=settings.omen_url, api_key=settings.omen_api_key)
    omen_signals = await omen.get_signals(
        min_confidence=body.min_confidence,
        limit=body.limit,
    )
    logger.info("pipeline_omen_fetched", count=len(omen_signals))

    if not omen_signals:
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return PipelineProcessResponse(
            status="no_signals",
            omen_signals_fetched=0,
            signals_with_chokepoints=0,
            total_orders_matched=0,
            total_signals_upserted=0,
            total_decisions_generated=0,
            processed_signals=[],
            decisions=[],
            processing_time_ms=elapsed,
            timestamp=start.isoformat(),
        )

    # ── 2. Detect chokepoints ────────────────────────────────────────
    signals_with_cps: list[tuple[OmenSignal, list[str]]] = []
    for sig in omen_signals:
        cps = detect_chokepoints(sig)
        if cps:
            signals_with_cps.append((sig, cps))

    logger.info(
        "pipeline_chokepoints_detected",
        total_signals=len(omen_signals),
        signals_with_chokepoints=len(signals_with_cps),
    )

    # ── 3. Load company orders + routes ──────────────────────────────
    # Fetch all active/in-transit orders for this company with their routes
    order_result = await db.execute(
        select(Order, Route)
        .outerjoin(Route, Order.route_id == Route.id)
        .where(
            Order.company_id == cid,
            Order.status.in_(["in_transit", "pending_departure", "booked", "active"]),
        )
    )
    order_rows = order_result.all()

    # Build order-to-chokepoint mapping from route metadata
    order_chokepoints: dict[str, tuple[Order, Route, list[str]]] = {}
    for order, route in order_rows:
        cps_list: list[str] = []
        if route and route.metadata_:
            cps_list = route.metadata_.get("chokepoints", [])
        # Also check order metadata
        if order.metadata_:
            cps_list.extend(order.metadata_.get("chokepoints_remaining", []))
        # Deduplicate
        cps_set = list(set(cps_list))
        order_chokepoints[str(order.id)] = (order, route, cps_set)

    # ── 4. Match signals to orders + upsert + generate decisions ─────
    signal_service = SignalService()
    decision_engine = DecisionEngine()
    all_decisions: list[Decision] = []
    all_alerts: list[AlertRecord] = []
    processed: list[ProcessedSignal] = []
    total_upserted = 0
    total_matched = 0

    for omen_sig, sig_chokepoints in signals_with_cps:
        matched_orders: list[MatchedOrder] = []
        internal_signals: list[InternalSignal] = []

        # Find orders whose route chokepoints overlap with signal chokepoints
        for oid, (order, route, order_cps) in order_chokepoints.items():
            overlap = set(sig_chokepoints) & set(order_cps)
            if overlap:
                matched_orders.append(MatchedOrder(
                    order_id=oid,
                    order_number=order.order_number,
                    route_name=route.name if route else "Unknown",
                    cargo_value_usd=float(order.total_value or 0),
                    destination=order.destination or "Unknown",
                    matched_chokepoints=list(overlap),
                    status=order.status,
                ))

                # Create an InternalSignal for this order
                internal_signals.append(InternalSignal(
                    source="omen_live",
                    signal_type=omen_sig.category or omen_sig.signal_type or "disruption",
                    entity_type="order",
                    entity_id=oid,
                    confidence=min(omen_sig.confidence, 0.99),
                    severity_score=min(omen_sig.severity_score, 100),
                    evidence={
                        "omen_signal_id": omen_sig.id,
                        "title": omen_sig.title,
                        "probability": omen_sig.probability,
                        "description": omen_sig.description,
                        "sources": omen_sig.evidence.get("sources", []),
                        "source_count": omen_sig.evidence.get("count", 0),
                    },
                    context={
                        "chokepoints": list(overlap),
                        "signal_chokepoints": sig_chokepoints,
                        "omen_context": omen_sig.context,
                        "cargo_value_usd": float(order.total_value or 0),
                        "destination": order.destination,
                        "carrier": (order.metadata_ or {}).get("carrier", "unknown"),
                    },
                ))

        # Upsert signals for matched orders
        if internal_signals:
            upserted = await signal_service.upsert_signals(db, cid, internal_signals)
            total_upserted += upserted

        total_matched += len(matched_orders)

        # Generate decisions for each matched order
        decisions_for_signal = 0
        for mo in matched_orders:
            try:
                decision = await decision_engine.generate_decision(
                    session=db,
                    company_id=cid,
                    entity_type="order",
                    entity_id=mo.order_id,
                    exposure_usd=mo.cargo_value_usd,
                )
                all_decisions.append(decision)
                decisions_for_signal += 1

                # NOTE: Per-decision alerts (Discord, in-app) are dispatched
                # automatically by DecisionEngine.generate_decision() via
                # auto_trigger.on_decision_generated(). No duplicate call here.

            except Exception as e:
                logger.error(
                    "pipeline_decision_failed",
                    order_id=mo.order_id,
                    signal_id=omen_sig.id,
                    error=str(e),
                )

        processed.append(ProcessedSignal(
            signal_id=omen_sig.id,
            title=omen_sig.title,
            probability=omen_sig.probability,
            confidence=omen_sig.confidence,
            severity_score=omen_sig.severity_score,
            detected_chokepoints=sig_chokepoints,
            matched_orders=matched_orders,
            decisions_generated=decisions_for_signal,
            signals_upserted=len(internal_signals),
        ))

    # ── 5b. ALERT: Scan summary alert ──────────────────────────────
    critical_count = sum(1 for d in all_decisions if d.risk_score >= 75)
    high_count = sum(1 for d in all_decisions if 50 <= d.risk_score < 75)
    try:
        scan_alert = await on_scan_completed(
            company_id=cid,
            signals_upserted=total_upserted,
            critical_count=critical_count,
            high_count=high_count,
        )
        if scan_alert:
            all_alerts.append(scan_alert)
    except Exception as ae:
        logger.warning("pipeline_scan_alert_failed", error=str(ae))

    elapsed = (datetime.utcnow() - start).total_seconds() * 1000

    # Build alert summary
    alert_summary = AlertSummary(
        total_alerts_fired=len(all_alerts),
        critical_alerts=sum(1 for a in all_alerts if a.severity.value == "critical"),
        high_alerts=sum(1 for a in all_alerts if a.severity.value == "high"),
        channels_dispatched=list({
            ch for a in all_alerts for ch in a.delivery_results.keys()
        }),
        alert_ids=[a.alert_id for a in all_alerts],
    )

    logger.info(
        "pipeline_process_complete",
        omen_signals=len(omen_signals),
        chokepoint_signals=len(signals_with_cps),
        orders_matched=total_matched,
        signals_upserted=total_upserted,
        decisions_generated=len(all_decisions),
        alerts_fired=len(all_alerts),
        elapsed_ms=elapsed,
    )

    return PipelineProcessResponse(
        status="completed",
        omen_signals_fetched=len(omen_signals),
        signals_with_chokepoints=len(signals_with_cps),
        total_orders_matched=total_matched,
        total_signals_upserted=total_upserted,
        total_decisions_generated=len(all_decisions),
        alerts=alert_summary,
        processed_signals=processed,
        decisions=all_decisions,
        processing_time_ms=round(elapsed, 2),
        timestamp=start.isoformat(),
    )
