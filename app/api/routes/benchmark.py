"""
Benchmark API Endpoints.

E1 + E2 COMPLIANCE API:
- E1: Benchmark comparison data against competitors
- E2: Flywheel operational status and metrics

Endpoints:
- GET /benchmark/evidence - Get benchmark evidence vs alternatives
- GET /benchmark/report - Get full benchmark report
- GET /benchmark/flywheel/status - Get flywheel operational status
- GET /benchmark/flywheel/metrics - Get flywheel performance metrics
- POST /benchmark/flywheel/retrain - Trigger model retraining
- POST /benchmark/flywheel/outcome - Record outcome for decision
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
import structlog

from app.benchmark.evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceCollector,
    create_benchmark_evidence_collector,
)
from app.benchmark.framework import (
    BenchmarkFramework,
    BenchmarkReport,
    get_benchmark_framework,
)
from app.benchmark.reports import (
    BenchmarkReportGenerator,
    BenchmarkSummary,
)
from app.ml.flywheel import (
    FlywheelMetrics,
    FlywheelStatus,
    OperationalFlywheel,
    get_operational_flywheel,
)
from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class OutcomeRecordRequest(BaseModel):
    """Request to record outcome for a decision."""
    
    decision_id: str = Field(..., description="Decision ID")
    actual_disruption: bool = Field(..., description="Did disruption occur?")
    actual_delay_days: float = Field(..., ge=0, description="Actual delay in days")
    actual_loss_usd: float = Field(..., ge=0, description="Actual loss in USD")
    action_taken: str = Field(..., description="Action customer took")
    action_success: bool = Field(..., description="Was action successful?")
    source: str = Field(default="api", description="Source: api, webhook, manual")


class OutcomeRecordResponse(BaseModel):
    """Response after recording outcome."""
    
    success: bool
    outcome_id: Optional[str] = None
    message: str
    outcomes_since_retrain: int


class RetrainTriggerResponse(BaseModel):
    """Response after triggering retrain."""
    
    status: str  # triggered, insufficient_data, already_running
    reason: str
    training_data_size: Optional[int] = None


class FlywheelStatusResponse(BaseModel):
    """Flywheel status with E2 compliance indicators."""
    
    # Core status
    is_operational: bool
    operational_since: Optional[datetime] = None
    
    # E2 compliance indicators
    outcome_collection_active: bool
    scheduled_retraining_active: bool
    automatic_deployment_active: bool
    
    # Metrics
    last_outcome_collected: Optional[datetime] = None
    last_model_retrain: Optional[datetime] = None
    last_model_deploy: Optional[datetime] = None
    
    # Health
    outcome_collection_rate: float
    training_data_size: int
    outcomes_pending_training: int
    next_scheduled_retrain: Optional[datetime] = None
    
    # E2 compliance status
    e2_compliance_status: str  # compliant, partial, non_compliant


class BenchmarkEvidenceSummary(BaseModel):
    """Summary of benchmark evidence for API response."""
    
    evidence_id: str
    period: str
    total_decisions: int
    
    # RISKCAST performance
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    # Value metrics
    total_value_delivered_usd: float
    roi_multiple: float
    
    # Baseline comparisons
    vs_do_nothing_improvement: float
    vs_threshold_improvement: float
    
    # Status
    beats_all_baselines: bool
    statistically_significant: bool
    
    # Headlines
    headline_finding: str


# ============================================================================
# BENCHMARK EVIDENCE ENDPOINTS (E1 Compliance)
# ============================================================================


@router.get("/evidence", response_model=BenchmarkEvidence)
async def get_benchmark_evidence(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
):
    """
    Get benchmark evidence comparing RISKCAST to alternatives.
    
    E1 COMPLIANCE: Provides benchmark comparison data.
    
    Returns:
    - Comparison vs do-nothing baseline
    - Comparison vs simple threshold
    - Comparison vs always-act
    - Statistical significance
    - Total value delivered
    - ROI calculation
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        session_factory = get_session_factory()
        collector = create_benchmark_evidence_collector(session_factory)
        evidence = await collector.collect_evidence(start_date, end_date)
        
        logger.info(
            "benchmark_evidence_retrieved",
            evidence_id=evidence.evidence_id,
            total_decisions=evidence.total_decisions,
            beats_all_baselines=evidence.beats_all_baselines,
        )
        
        return evidence
        
    except Exception as e:
        logger.error("benchmark_evidence_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect benchmark evidence: {str(e)}",
        )


@router.get("/evidence/summary", response_model=BenchmarkEvidenceSummary)
async def get_benchmark_evidence_summary(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
):
    """
    Get summary of benchmark evidence.
    
    Lighter-weight endpoint for dashboards.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        session_factory = get_session_factory()
        collector = create_benchmark_evidence_collector(session_factory)
        evidence = await collector.collect_evidence(start_date, end_date)
        
        return BenchmarkEvidenceSummary(
            evidence_id=evidence.evidence_id,
            period=evidence.period,
            total_decisions=evidence.total_decisions,
            accuracy=evidence.accuracy,
            precision=evidence.precision,
            recall=evidence.recall,
            f1_score=evidence.f1_score,
            total_value_delivered_usd=evidence.total_value_delivered_usd,
            roi_multiple=evidence.roi_multiple,
            vs_do_nothing_improvement=evidence.vs_do_nothing.accuracy_improvement,
            vs_threshold_improvement=evidence.vs_simple_threshold.accuracy_improvement,
            beats_all_baselines=evidence.beats_all_baselines,
            statistically_significant=evidence.statistically_significant,
            headline_finding=evidence.headline_finding,
        )
        
    except Exception as e:
        logger.error("benchmark_summary_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get benchmark summary: {str(e)}",
        )


@router.get("/report", response_model=BenchmarkReport)
async def get_benchmark_report(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
):
    """
    Get full benchmark comparison report.
    
    Returns detailed comparison against all baselines including:
    - Do nothing
    - Always act
    - Simple threshold
    - Perfect hindsight (theoretical upper bound)
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        framework = get_benchmark_framework()
        report = await framework.run_benchmark(start_date, end_date)
        
        logger.info(
            "benchmark_report_generated",
            report_id=report.report_id,
            total_decisions=report.total_decisions_analyzed,
            beats_all_baselines=report.beats_all_baselines,
        )
        
        return report
        
    except Exception as e:
        logger.error("benchmark_report_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate benchmark report: {str(e)}",
        )


@router.get("/report/summary", response_model=BenchmarkSummary)
async def get_benchmark_report_summary(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
):
    """
    Get executive summary of benchmark report.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        framework = get_benchmark_framework()
        report = await framework.run_benchmark(start_date, end_date)
        
        generator = BenchmarkReportGenerator()
        summary = generator.generate_summary(report)
        
        return summary
        
    except Exception as e:
        logger.error("benchmark_summary_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate benchmark summary: {str(e)}",
        )


@router.get("/report/markdown")
async def get_benchmark_report_markdown(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
):
    """
    Get benchmark report in Markdown format.
    
    Suitable for documentation or sharing.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        framework = get_benchmark_framework()
        report = await framework.run_benchmark(start_date, end_date)
        
        generator = BenchmarkReportGenerator()
        markdown = generator.generate_markdown_report(report)
        
        return {
            "format": "markdown",
            "content": markdown,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error("benchmark_markdown_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate markdown report: {str(e)}",
        )


# ============================================================================
# FLYWHEEL ENDPOINTS (E2 Compliance)
# ============================================================================


@router.get("/flywheel/status", response_model=FlywheelStatusResponse)
async def get_flywheel_status():
    """
    Get data flywheel operational status.
    
    E2 COMPLIANCE: Shows flywheel operational state.
    
    Returns:
    - Is flywheel running?
    - Last outcome collected
    - Last model retrain
    - Outcome collection rate
    - E2 compliance status
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        status = await flywheel.get_flywheel_status()
        
        # Determine E2 compliance status
        if status.is_operational and status.outcome_collection_rate > 0:
            e2_status = "compliant"
        elif status.training_data_size > 0:
            e2_status = "partial"
        else:
            e2_status = "non_compliant"
        
        return FlywheelStatusResponse(
            is_operational=status.is_operational,
            operational_since=None,  # Would track in production
            outcome_collection_active=status.outcome_collector_status == "running",
            scheduled_retraining_active=status.training_scheduler_status == "running",
            automatic_deployment_active=status.deployment_pipeline_status == "ready",
            last_outcome_collected=status.last_outcome_collected,
            last_model_retrain=status.last_model_retrain,
            last_model_deploy=status.last_model_deploy,
            outcome_collection_rate=status.outcome_collection_rate,
            training_data_size=status.training_data_size,
            outcomes_pending_training=status.outcomes_pending_training,
            next_scheduled_retrain=status.next_scheduled_retrain,
            e2_compliance_status=e2_status,
        )
        
    except Exception as e:
        logger.error("flywheel_status_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flywheel status: {str(e)}",
        )


@router.get("/flywheel/metrics", response_model=FlywheelMetrics)
async def get_flywheel_metrics():
    """
    Get flywheel performance metrics.
    
    E2 COMPLIANCE: Shows learning velocity and model improvement.
    
    Returns:
    - Outcome coverage
    - Model accuracy trend
    - Learning velocity
    - Training data size
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        metrics = await flywheel.get_flywheel_metrics()
        
        logger.info(
            "flywheel_metrics_retrieved",
            total_decisions=metrics.total_decisions,
            outcome_coverage=metrics.outcome_coverage,
            current_accuracy=metrics.current_accuracy,
        )
        
        return metrics
        
    except Exception as e:
        logger.error("flywheel_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get flywheel metrics: {str(e)}",
        )


@router.post("/flywheel/retrain", response_model=RetrainTriggerResponse)
async def trigger_flywheel_retrain(
    reason: str = Query(default="manual", description="Reason for retrain"),
):
    """
    Manually trigger model retraining.
    
    E2 COMPLIANCE: Supports manual retraining trigger.
    
    Use cases:
    - After significant data collection
    - After accuracy degradation detected
    - Scheduled maintenance
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        
        # Get current metrics for response
        metrics = await flywheel.get_flywheel_metrics()
        
        # Trigger retrain
        success = await flywheel.trigger_retrain(reason=reason)
        
        if success:
            return RetrainTriggerResponse(
                status="triggered",
                reason=reason,
                training_data_size=metrics.training_data_size,
            )
        else:
            return RetrainTriggerResponse(
                status="insufficient_data",
                reason=f"Need at least {flywheel.MIN_TRAINING_SAMPLES} training samples",
                training_data_size=metrics.training_data_size,
            )
        
    except Exception as e:
        logger.error("retrain_trigger_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger retrain: {str(e)}",
        )


@router.post("/flywheel/outcome", response_model=OutcomeRecordResponse)
async def record_outcome(request: OutcomeRecordRequest):
    """
    Record outcome for a decision.
    
    E2 COMPLIANCE: Outcome collection endpoint.
    
    This is the INPUT to the flywheel - more outcomes = better models.
    
    Called via:
    - Manual entry
    - Webhook from tracking systems
    - Integration with shipping platforms
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        
        outcome = await flywheel.collect_outcome(
            decision_id=request.decision_id,
            actual_disruption=request.actual_disruption,
            actual_delay_days=request.actual_delay_days,
            actual_loss_usd=request.actual_loss_usd,
            action_taken=request.action_taken,
            action_success=request.action_success,
            source=request.source,
        )
        
        if outcome:
            status = await flywheel.get_flywheel_status()
            
            return OutcomeRecordResponse(
                success=True,
                outcome_id=outcome.outcome_id,
                message=f"Outcome recorded for decision {request.decision_id}",
                outcomes_since_retrain=status.outcomes_pending_training,
            )
        else:
            return OutcomeRecordResponse(
                success=False,
                message=f"Decision {request.decision_id} not found",
                outcomes_since_retrain=0,
            )
        
    except Exception as e:
        logger.error(
            "outcome_recording_failed",
            error=str(e),
            decision_id=request.decision_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record outcome: {str(e)}",
        )


@router.post("/flywheel/start")
async def start_flywheel():
    """
    Start the operational flywheel.
    
    E2 COMPLIANCE: Start production flywheel.
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        await flywheel.start()
        
        return {
            "status": "started",
            "message": "Operational flywheel started",
            "outcome_collection": "active",
            "scheduled_retraining": "active",
        }
        
    except Exception as e:
        logger.error("flywheel_start_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start flywheel: {str(e)}",
        )


@router.post("/flywheel/stop")
async def stop_flywheel():
    """
    Stop the operational flywheel.
    
    Use with caution - stops all automatic learning.
    """
    try:
        session_factory = get_session_factory()
        flywheel = get_operational_flywheel(session_factory)
        await flywheel.stop()
        
        return {
            "status": "stopped",
            "message": "Operational flywheel stopped",
        }
        
    except Exception as e:
        logger.error("flywheel_stop_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop flywheel: {str(e)}",
        )


# ============================================================================
# E1 + E2 COMBINED COMPLIANCE
# ============================================================================


@router.get("/compliance")
async def get_e1_e2_compliance():
    """
    Get E1 + E2 audit compliance status.
    
    Returns:
    - E1: Benchmark evidence availability
    - E2: Flywheel operational status
    - Combined compliance score
    """
    try:
        session_factory = get_session_factory()
        
        # E1: Check benchmark evidence
        collector = create_benchmark_evidence_collector(session_factory)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        evidence = await collector.collect_evidence(start_date, end_date)
        
        e1_compliant = (
            evidence.total_decisions >= 30 and
            evidence.beats_all_baselines
        )
        
        # E2: Check flywheel status
        flywheel = get_operational_flywheel(session_factory)
        status = await flywheel.get_flywheel_status()
        
        e2_compliant = (
            status.is_operational and
            status.training_data_size >= 50
        )
        
        # Calculate points
        e1_points = 15 if e1_compliant else (8 if evidence.total_decisions >= 30 else 0)
        e2_points = 20 if e2_compliant else (10 if status.training_data_size >= 30 else 0)
        
        return {
            "e1_benchmark_evidence": {
                "status": "compliant" if e1_compliant else "partial",
                "total_decisions_analyzed": evidence.total_decisions,
                "beats_all_baselines": evidence.beats_all_baselines,
                "statistically_significant": evidence.statistically_significant,
                "points_earned": e1_points,
                "points_max": 15,
            },
            "e2_operational_flywheel": {
                "status": "compliant" if e2_compliant else "partial",
                "is_operational": status.is_operational,
                "training_data_size": status.training_data_size,
                "outcome_collection_rate": status.outcome_collection_rate,
                "points_earned": e2_points,
                "points_max": 20,
            },
            "combined": {
                "total_points_earned": e1_points + e2_points,
                "total_points_max": 35,
                "compliance_pct": (e1_points + e2_points) / 35 * 100,
                "gap_closed": e1_compliant and e2_compliant,
            },
        }
        
    except Exception as e:
        logger.error("compliance_check_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check compliance: {str(e)}",
        )


# ============================================================================
# REGISTER ROUTER
# ============================================================================


def include_benchmark_router(app):
    """Include benchmark router in FastAPI app."""
    app.include_router(router)
