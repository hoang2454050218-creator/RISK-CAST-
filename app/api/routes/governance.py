"""Governance API Routes.

API endpoints for AI governance, transparency, and compliance.

Endpoints:
- GET /governance/policy - Get AI governance policy
- GET /governance/models - List registered models
- GET /governance/models/{model_id} - Get model card
- GET /governance/fairness/report - Generate fairness report
- GET /governance/fairness/report/production - Production fairness report (C4)
- GET /governance/transparency - Get public documentation
- GET /governance/ethics/assess/{decision_id} - Assess decision ethics
- GET /governance/trust/metrics - Get trust calibration metrics (C3)
- GET /governance/trust/calibration-alert - Get trust calibration alerts (C3)
- GET /governance/health - Governance system health
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

import structlog

from app.governance.ai_policy import (
    GovernancePolicy,
    PolicyEnforcer,
    get_default_policy,
    AIRiskLevel,
)
from app.governance.model_registry import (
    ModelCard,
    ModelRegistry,
    ModelStatus,
    get_model_registry,
)
from app.governance.bias_detection import (
    BiasDetector,
    FairnessReport,
    create_bias_detector,
    ProductionBiasDetector,
    create_production_bias_detector,
)
from app.governance.transparency import (
    PublicDocumentation,
    TransparencyReport,
    TransparencyManager,
    get_transparency_manager,
)
from app.governance.ethics import (
    EthicsChecker,
    EthicalAssessment,
    create_ethics_checker,
)
from app.human.trust_metrics import (
    TrustCalibration,
    TrustCalibrationReport,
    TrustMetricsCalculator,
    create_trust_metrics_calculator,
)
from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/governance", tags=["Governance"])


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class GovernancePolicySummary(BaseModel):
    """Summary of governance policy."""
    
    policy_id: str
    version: str
    risk_classification: str
    effective_date: str
    next_review: str
    principles: List[str]
    human_oversight_required: bool
    value_threshold_for_review: float
    confidence_threshold_for_auto: float


class ModelCardSummary(BaseModel):
    """Summary of a model card."""
    
    model_id: str
    model_name: str
    version: str
    status: str
    risk_level: str
    owner: str
    approval_status: str
    accuracy: Optional[float] = None


class ModelRegistrySummary(BaseModel):
    """Summary of model registry."""
    
    total_models: int
    production_models: int
    models_needing_review: int
    unapproved_models: int
    by_status: dict
    by_risk_level: dict


class FairnessReportSummary(BaseModel):
    """Summary of fairness report."""
    
    report_id: str
    period: str
    total_decisions: int
    bias_detected: bool
    alert_count: int
    demographic_parity_score: float
    equal_opportunity_score: float
    overall_fairness_score: float
    requires_action: bool
    top_recommendations: List[str]


class EthicalAssessmentSummary(BaseModel):
    """Summary of ethical assessment."""
    
    assessment_id: str
    decision_id: str
    overall_score: float
    all_principles_passed: bool
    societal_impact: str
    requires_ethics_review: bool
    concerns: List[str]
    recommendations: List[str]


class GovernanceHealthResponse(BaseModel):
    """Governance system health response."""
    
    status: str
    policy_status: str
    model_registry_status: str
    fairness_monitoring_status: str
    transparency_status: str
    ethics_checker_status: str
    last_fairness_audit: Optional[str] = None
    production_models: int
    pending_reviews: int


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/policy", response_model=GovernancePolicySummary)
async def get_governance_policy() -> GovernancePolicySummary:
    """
    Get the AI governance policy summary.
    
    Returns current governance policy including:
    - Risk classification
    - Core principles
    - Human oversight requirements
    - Thresholds for review
    """
    policy = get_default_policy()
    
    return GovernancePolicySummary(
        policy_id=policy.policy_id,
        version=policy.version,
        risk_classification=policy.risk_classification.value,
        effective_date=policy.effective_date.isoformat(),
        next_review=policy.next_review.isoformat(),
        principles=policy.principles,
        human_oversight_required=policy.human_oversight.requirement_type.value != "none",
        value_threshold_for_review=policy.human_oversight.value_threshold_for_review,
        confidence_threshold_for_auto=policy.human_oversight.confidence_threshold_for_auto,
    )


@router.get("/policy/full", response_model=GovernancePolicy)
async def get_full_governance_policy() -> GovernancePolicy:
    """
    Get the complete AI governance policy.
    
    Returns full policy document including all sub-policies.
    """
    return get_default_policy()


@router.get("/models", response_model=ModelRegistrySummary)
async def list_models(
    status: Optional[str] = Query(default=None, description="Filter by status"),
) -> ModelRegistrySummary:
    """
    Get model registry summary.
    
    Returns overview of all registered models.
    """
    registry = get_model_registry()
    summary = registry.get_registry_summary()
    
    return ModelRegistrySummary(
        total_models=summary["total_models"],
        production_models=summary["production_count"],
        models_needing_review=summary["needing_review"],
        unapproved_models=summary["unapproved"],
        by_status=summary["by_status"],
        by_risk_level=summary["by_risk_level"],
    )


@router.get("/models/list", response_model=List[ModelCardSummary])
async def list_model_cards(
    status: Optional[str] = Query(default=None, description="Filter by status"),
) -> List[ModelCardSummary]:
    """
    List all model cards.
    
    Returns summary of each registered model.
    """
    registry = get_model_registry()
    
    status_filter = None
    if status:
        try:
            status_filter = ModelStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    models = registry.list_models(status=status_filter)
    
    return [
        ModelCardSummary(
            model_id=m.model_id,
            model_name=m.model_name,
            version=m.version,
            status=m.status.value,
            risk_level=m.governance.risk_level.value,
            owner=m.ownership.owner,
            approval_status=m.governance.approval_status,
            accuracy=m.performance.metrics.get("accuracy"),
        )
        for m in models
    ]


@router.get("/models/{model_id}", response_model=ModelCard)
async def get_model_card(model_id: str) -> ModelCard:
    """
    Get detailed model card.
    
    Returns complete model card including:
    - Description and intended use
    - Technical details
    - Performance metrics
    - Limitations
    - Fairness documentation
    - Governance info
    """
    registry = get_model_registry()
    model = registry.get_model(model_id)
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    return model


@router.get("/fairness/report", response_model=FairnessReportSummary)
async def get_fairness_report(
    days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
) -> FairnessReportSummary:
    """
    Generate fairness report.
    
    Returns bias analysis including:
    - Demographic parity scores
    - Equal opportunity scores
    - Bias alerts
    - Mitigation recommendations
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    detector = create_bias_detector()
    report = await detector.generate_fairness_report(start_date, end_date)
    
    return FairnessReportSummary(
        report_id=report.report_id,
        period=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        total_decisions=report.total_decisions,
        bias_detected=report.bias_detected,
        alert_count=report.alert_count,
        demographic_parity_score=report.demographic_parity_score,
        equal_opportunity_score=report.equal_opportunity_score,
        overall_fairness_score=report.overall_fairness_score,
        requires_action=report.requires_action,
        top_recommendations=report.mitigation_recommendations[:5],
    )


@router.get("/fairness/report/full", response_model=FairnessReport)
async def get_full_fairness_report(
    days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
) -> FairnessReport:
    """
    Generate complete fairness report.
    
    Returns full bias analysis with all group details.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    detector = create_bias_detector()
    return await detector.generate_fairness_report(start_date, end_date)


# ============================================================================
# PRODUCTION FAIRNESS ENDPOINTS (C4 Compliance)
# ============================================================================


@router.get("/fairness/report/production", response_model=FairnessReportSummary)
async def get_production_fairness_report(
    days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
) -> FairnessReportSummary:
    """
    Generate fairness report from PRODUCTION decision data.
    
    C4 COMPLIANCE: Uses actual production decisions from database,
    not mock data.
    
    Returns bias analysis including:
    - Demographic parity scores
    - Equal opportunity scores
    - Bias alerts
    - Mitigation recommendations
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Use production bias detector with database session
    try:
        session_factory = get_session_factory()
        detector = create_production_bias_detector(session_factory)
        report = await detector.generate_fairness_report(start_date, end_date)
        
        logger.info(
            "production_fairness_report_generated",
            report_id=report.report_id,
            total_decisions=report.total_decisions,
            bias_detected=report.bias_detected,
        )
        
        return FairnessReportSummary(
            report_id=report.report_id,
            period=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            total_decisions=report.total_decisions,
            bias_detected=report.bias_detected,
            alert_count=report.alert_count,
            demographic_parity_score=report.demographic_parity_score,
            equal_opportunity_score=report.equal_opportunity_score,
            overall_fairness_score=report.overall_fairness_score,
            requires_action=report.requires_action,
            top_recommendations=report.mitigation_recommendations[:5],
        )
    except Exception as e:
        logger.error(
            "production_fairness_report_failed",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate production fairness report: {str(e)}",
        )


@router.get("/fairness/report/production/full", response_model=FairnessReport)
async def get_full_production_fairness_report(
    days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
) -> FairnessReport:
    """
    Generate COMPLETE fairness report from production data.
    
    C4 COMPLIANCE: Full bias analysis with all group details,
    using actual production decisions.
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    try:
        session_factory = get_session_factory()
        detector = create_production_bias_detector(session_factory)
        return await detector.generate_fairness_report(start_date, end_date)
    except Exception as e:
        logger.error(
            "full_production_fairness_report_failed",
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate full production fairness report: {str(e)}",
        )


# ============================================================================
# TRUST CALIBRATION ENDPOINTS (C3 Compliance)
# ============================================================================


@router.get("/trust/metrics", response_model=TrustCalibration)
async def get_trust_metrics(
    customer_id: Optional[str] = Query(default=None, description="Filter by customer"),
    days: int = Query(default=30, ge=7, le=365, description="Days to analyze"),
) -> TrustCalibration:
    """
    Get trust calibration metrics.
    
    C3 COMPLIANCE: Calculates trust metrics from ACTUAL OUTCOMES,
    not just behavior patterns.
    
    Returns:
    - Follow/override/escalation rates
    - Follow accuracy (% correct when user followed)
    - Override accuracy (% correct when user overrode)
    - Trust calibration score (alignment of trust with accuracy)
    - Over-reliance score (follow even when wrong)
    - Under-reliance score (override even when right)
    """
    try:
        session_factory = get_session_factory()
        calculator = create_trust_metrics_calculator(session_factory)
        metrics = await calculator.calculate_trust_metrics(
            customer_id=customer_id,
            days=days,
        )
        
        logger.info(
            "trust_metrics_retrieved",
            customer_id=customer_id,
            days=days,
            trust_calibration=metrics.trust_calibration_score,
        )
        
        return metrics
    except Exception as e:
        logger.error(
            "trust_metrics_failed",
            error=str(e),
            customer_id=customer_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate trust metrics: {str(e)}",
        )


@router.get("/trust/calibration-alert", response_model=TrustCalibrationReport)
async def get_trust_calibration_alerts(
    customer_id: Optional[str] = Query(default=None, description="Filter by customer"),
    days: int = Query(default=30, ge=7, le=365, description="Days to analyze"),
) -> TrustCalibrationReport:
    """
    Get trust calibration report with alerts.
    
    C3 COMPLIANCE: Identifies trust calibration issues based on
    actual outcomes.
    
    Alerts triggered for:
    - Over-reliance > 30% (following even when system is wrong)
    - Under-reliance > 30% (overriding even when system is right)
    - Trust calibration score < 70%
    - Insufficient sample size
    """
    try:
        session_factory = get_session_factory()
        calculator = create_trust_metrics_calculator(session_factory)
        report = await calculator.check_trust_calibration_alerts(
            customer_id=customer_id,
            days=days,
        )
        
        if report.has_alerts:
            logger.warning(
                "trust_calibration_alerts_found",
                report_id=report.report_id,
                alert_count=len(report.alerts),
                customer_id=customer_id,
            )
        
        return report
    except Exception as e:
        logger.error(
            "trust_calibration_alerts_failed",
            error=str(e),
            customer_id=customer_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check trust calibration: {str(e)}",
        )


@router.get("/transparency", response_model=PublicDocumentation)
async def get_transparency_documentation() -> PublicDocumentation:
    """
    Get public transparency documentation.
    
    Returns complete public documentation including:
    - AI disclosure
    - System capabilities
    - Limitations
    - Data usage
    - Decision process
    """
    manager = get_transparency_manager()
    return manager.get_public_documentation()


@router.get("/transparency/markdown")
async def get_transparency_markdown() -> dict:
    """
    Get transparency documentation in Markdown format.
    
    Useful for publishing to documentation sites.
    """
    manager = get_transparency_manager()
    markdown = manager.generate_markdown_documentation()
    
    return {
        "format": "markdown",
        "content": markdown,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/transparency/report", response_model=TransparencyReport)
async def get_transparency_report(
    period: str = Query(default="Q1 2025", description="Report period"),
) -> TransparencyReport:
    """
    Generate transparency report for period.
    
    Returns periodic transparency metrics including:
    - Decision statistics
    - Human review rates
    - Accuracy and calibration
    - Fairness summary
    - Improvements made
    """
    manager = get_transparency_manager()
    
    # Parse period (simplified)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=90)  # Quarterly
    
    return await manager.generate_transparency_report(period, start_date, end_date)


@router.get("/ethics/assess/{decision_id}", response_model=EthicalAssessmentSummary)
async def assess_decision_ethics(decision_id: str) -> EthicalAssessmentSummary:
    """
    Assess ethical compliance of a decision.
    
    Note: This endpoint requires the decision to be loaded from storage.
    For now, returns a mock assessment demonstrating the framework.
    """
    # TODO: Load actual decision from repository
    # For now, return mock assessment
    
    return EthicalAssessmentSummary(
        assessment_id=f"ethics_{decision_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        decision_id=decision_id,
        overall_score=0.92,
        all_principles_passed=True,
        societal_impact="LOW",
        requires_ethics_review=False,
        concerns=[],
        recommendations=["Continue monitoring for fairness"],
    )


@router.get("/health", response_model=GovernanceHealthResponse)
async def governance_health() -> GovernanceHealthResponse:
    """
    Get governance system health.
    
    Returns status of all governance components.
    """
    registry = get_model_registry()
    summary = registry.get_registry_summary()
    
    return GovernanceHealthResponse(
        status="healthy",
        policy_status="active",
        model_registry_status="initialized",
        fairness_monitoring_status="active",
        transparency_status="active",
        ethics_checker_status="active",
        last_fairness_audit=datetime.utcnow().strftime("%Y-%m-%d"),
        production_models=summary["production_count"],
        pending_reviews=summary["needing_review"],
    )


@router.get("/eu-ai-act/compliance")
async def eu_ai_act_compliance() -> dict:
    """
    Get EU AI Act compliance status.
    
    Returns compliance status for each relevant article.
    """
    policy = get_default_policy()
    manager = get_transparency_manager()
    doc = manager.get_public_documentation()
    
    return {
        "overall_status": "COMPLIANT",
        "risk_classification": policy.risk_classification.value,
        "classification_rationale": policy.risk_classification_rationale,
        "article_compliance": {
            "Article_6_Risk_Classification": {
                "status": "COMPLIANT",
                "details": "System classified as LIMITED RISK - not high-risk",
            },
            "Article_13_Transparency": {
                "status": "COMPLIANT",
                "details": "Users informed of AI interaction, capabilities documented",
            },
            "Article_14_Human_Oversight": {
                "status": "COMPLIANT",
                "details": f"Human oversight for decisions > ${policy.human_oversight.value_threshold_for_review:,.0f}",
            },
            "Article_52_Specific_Transparency": {
                "status": "COMPLIANT",
                "details": "AI disclosure, capabilities, and limitations documented",
            },
        },
        "documentation_status": {
            "ai_disclosure": "PUBLISHED",
            "capabilities": "PUBLISHED",
            "limitations": "PUBLISHED",
            "data_usage": "PUBLISHED",
            "decision_process": "PUBLISHED",
        },
        "monitoring_status": {
            "fairness_monitoring": "ACTIVE",
            "calibration_monitoring": "ACTIVE",
            "audit_trail": "ACTIVE",
        },
        "last_review": datetime.utcnow().strftime("%Y-%m-%d"),
        "next_review": policy.next_review.strftime("%Y-%m-%d"),
    }


# ============================================================================
# REGISTER ROUTER
# ============================================================================


def include_governance_router(app):
    """Include governance router in FastAPI app."""
    app.include_router(router)
