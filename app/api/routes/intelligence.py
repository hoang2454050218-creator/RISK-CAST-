"""Intelligence API Endpoints.

LLM-enhanced analysis endpoints:
- Company risk analysis
- Signal interpretation
- Decision explanations
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.riskcast.repos.customer import (
    PostgresCustomerRepository,
    CustomerNotFoundError,
)
from app.reasoning.llm_service import get_reasoning_llm_service, ReasoningLLMService

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================


class CompanyAnalysisResponse(BaseModel):
    """LLM-generated company risk analysis."""
    company_id: str
    analysis: str = ""
    risk_summary: str
    key_exposures: list[str]
    vulnerability_score: float = 0.0
    industry_risks: list[str] = []
    chokepoint_analysis: dict = {}
    recommendations: list[str]
    monitoring_priorities: list[str] = []
    confidence: float
    generated_at: str
    llm_enhanced: bool = False


class SignalAnalysisRequest(BaseModel):
    """Request for signal analysis."""
    signal_type: str
    evidence: dict = {}
    confidence: float = 0.5
    chokepoint: Optional[str] = None


class SignalAnalysisResponse(BaseModel):
    """LLM-generated signal analysis."""
    interpretation: str
    severity_assessment: str
    timeline: str = ""
    affected_sectors: list[str] = []
    geographic_scope: str = ""
    confidence_assessment: float
    recommended_actions: list[str] = []
    watch_indicators: list[str] = []
    llm_enhanced: bool = False


# ============================================================================
# DEPENDENCIES
# ============================================================================


def get_repository(session: AsyncSession = Depends(get_db_session)) -> PostgresCustomerRepository:
    return PostgresCustomerRepository(session)


def get_llm_service() -> ReasoningLLMService:
    return get_reasoning_llm_service()


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/analyze/{customer_id}",
    response_model=CompanyAnalysisResponse,
    summary="Analyze company risk profile",
    description="Use AI to analyze a company's risk profile based on their routes, industry, and chokepoint exposure",
)
async def analyze_company(
    customer_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
    llm: ReasoningLLMService = Depends(get_llm_service),
) -> CompanyAnalysisResponse:
    """
    Analyze a company's risk profile using LLM.
    
    Falls back to rule-based analysis if LLM is unavailable.
    """
    # Get customer profile
    profile = await repo.get_profile(customer_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    # Run LLM analysis
    analysis = await llm.analyze_company_context(
        company_name=profile.company_name,
        industry=profile.industry,
        primary_routes=profile.primary_routes,
        chokepoints=profile.relevant_chokepoints,
        risk_tolerance=profile.risk_tolerance.value,
    )

    return CompanyAnalysisResponse(
        company_id=customer_id,
        analysis=analysis.get("risk_summary", ""),
        risk_summary=analysis.get("risk_summary", "No analysis available"),
        key_exposures=analysis.get("key_exposures", []),
        vulnerability_score=analysis.get("vulnerability_score", 0.0),
        industry_risks=analysis.get("industry_risks", []),
        chokepoint_analysis=analysis.get("chokepoint_analysis", {}),
        recommendations=analysis.get("recommendations", []),
        monitoring_priorities=analysis.get("monitoring_priorities", []),
        confidence=analysis.get("vulnerability_score", 0.5),
        generated_at=datetime.utcnow().isoformat(),
        llm_enhanced=llm.is_available,
    )


@router.get(
    "/insights/{customer_id}",
    response_model=CompanyAnalysisResponse,
    summary="Get company insights",
    description="Get cached or generate company risk insights",
)
async def get_company_insights(
    customer_id: str,
    repo: PostgresCustomerRepository = Depends(get_repository),
    llm: ReasoningLLMService = Depends(get_llm_service),
) -> CompanyAnalysisResponse:
    """Get or generate company insights."""
    # For now, generate fresh (in production, cache in Redis)
    return await analyze_company(customer_id, repo, llm)


@router.post(
    "/analyze-signal/{signal_id}",
    response_model=SignalAnalysisResponse,
    summary="Analyze a signal",
    description="Use AI to analyze and interpret a signal",
)
async def analyze_signal(
    signal_id: str,
    request: SignalAnalysisRequest,
    llm: ReasoningLLMService = Depends(get_llm_service),
) -> SignalAnalysisResponse:
    """Analyze a signal using LLM."""
    analysis = await llm.analyze_signal(
        signal_type=request.signal_type,
        evidence=request.evidence,
        confidence=request.confidence,
        chokepoint=request.chokepoint,
    )

    return SignalAnalysisResponse(
        interpretation=analysis.get("interpretation", ""),
        severity_assessment=analysis.get("severity_assessment", "unknown"),
        timeline=analysis.get("timeline", ""),
        affected_sectors=analysis.get("affected_sectors", []),
        geographic_scope=analysis.get("geographic_scope", ""),
        confidence_assessment=analysis.get("confidence_assessment", request.confidence),
        recommended_actions=analysis.get("recommended_actions", []),
        watch_indicators=analysis.get("watch_indicators", []),
        llm_enhanced=llm.is_available,
    )
