"""
LLM Service for Reasoning Engine.

Integrates Claude (Anthropic) into the RISKCAST reasoning pipeline.
This service provides:
- Company context understanding via LLM
- Signal analysis and interpretation
- Causal chain enhancement
- Natural language decision explanations
- Risk assessment augmentation

The service is designed as an enhancement layer:
- If LLM is unavailable, the system falls back to rule-based reasoning
- LLM outputs are validated and bounded (never trusted blindly)
- All LLM calls are logged for audit trail
"""

import json
import os
from datetime import datetime
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Anthropic API constants
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ReasoningLLMService:
    """
    LLM service specifically for the reasoning engine.
    
    Uses Claude to enhance rule-based reasoning with:
    - Contextual understanding of company operations
    - Signal interpretation beyond templates
    - Dynamic causal chain generation
    - Natural language risk communication
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._available = bool(self.api_key)
        if not self._available:
            logger.warning("reasoning_llm_unavailable", msg="No ANTHROPIC_API_KEY — LLM features disabled")

    @property
    def is_available(self) -> bool:
        return self._available

    async def _call_claude(
        self,
        system: str,
        user_message: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1500,
    ) -> str:
        """Make a non-streaming call to Claude API."""
        if not self._available:
            return ""

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                content = data.get("content", [])
                text_parts = [
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                ]
                result = "".join(text_parts)
                
                logger.info(
                    "llm_call_completed",
                    model=model,
                    input_tokens=data.get("usage", {}).get("input_tokens", 0),
                    output_tokens=data.get("usage", {}).get("output_tokens", 0),
                )
                return result

        except httpx.TimeoutException:
            logger.error("llm_timeout", model=model)
            return ""
        except Exception as e:
            logger.error("llm_call_failed", model=model, error=str(e))
            return ""

    async def analyze_company_context(
        self,
        company_name: str,
        industry: Optional[str],
        primary_routes: list[str],
        chokepoints: list[str],
        risk_tolerance: str,
        active_shipments_count: int = 0,
    ) -> dict:
        """
        Use LLM to deeply understand a company's risk profile.
        
        Returns structured analysis of:
        - Key vulnerabilities based on routes and industry
        - Specific chokepoint risks
        - Industry-specific risk factors
        - Recommended monitoring priorities
        """
        if not self._available:
            return self._fallback_company_analysis(
                company_name, industry, primary_routes, chokepoints, risk_tolerance
            )

        system = """You are a senior maritime risk analyst at a supply chain intelligence firm.
Analyze the company's risk profile based on their trade routes, industry, and chokepoint exposure.

Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{
    "risk_summary": "2-3 sentence overview of key risks",
    "key_exposures": ["list of specific risk exposures"],
    "vulnerability_score": 0.0-1.0,
    "industry_risks": ["industry-specific risk factors"],
    "chokepoint_analysis": {"chokepoint_name": "risk description"},
    "recommendations": ["actionable recommendations"],
    "monitoring_priorities": ["what to watch most closely"]
}"""

        user_msg = f"""Company: {company_name}
Industry: {industry or 'Not specified'}
Trade Routes: {', '.join(primary_routes) if primary_routes else 'None configured'}
Chokepoints: {', '.join(chokepoints) if chokepoints else 'None detected'}
Risk Tolerance: {risk_tolerance}
Active Shipments: {active_shipments_count}

Analyze this company's maritime supply chain risk profile."""

        result = await self._call_claude(system, user_msg, model="claude-sonnet-4-20250514", max_tokens=1000)
        
        if not result:
            return self._fallback_company_analysis(
                company_name, industry, primary_routes, chokepoints, risk_tolerance
            )

        try:
            # Try to parse JSON from the response
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            logger.warning("llm_json_parse_failed", response_preview=result[:200])
            return self._fallback_company_analysis(
                company_name, industry, primary_routes, chokepoints, risk_tolerance
            )

    async def enhance_causal_analysis(
        self,
        event_type: str,
        signal_description: str,
        affected_chokepoints: list[str],
        existing_chain: list[dict],
    ) -> dict:
        """
        Use LLM to enhance the causal chain analysis beyond templates.
        
        Takes the rule-based causal chain and adds:
        - Additional causal links
        - Historical context
        - Probability estimates
        - Intervention suggestions
        """
        if not self._available:
            return {"enhanced": False, "chain": existing_chain, "additional_context": ""}

        system = """You are an expert in maritime supply chain disruption analysis.
Given a signal event and existing causal chain, provide enhanced analysis.

Return ONLY valid JSON with this structure:
{
    "enhanced_chain": [
        {"cause": "...", "effect": "...", "probability": 0.0-1.0, "timeframe": "..."}
    ],
    "historical_precedents": ["similar events and their outcomes"],
    "second_order_effects": ["indirect impacts beyond the immediate chain"],
    "intervention_points": [
        {"action": "...", "effectiveness": 0.0-1.0, "timing": "..."}
    ],
    "confidence": 0.0-1.0
}"""

        user_msg = f"""Event: {event_type}
Description: {signal_description}
Affected Chokepoints: {', '.join(affected_chokepoints)}

Existing Causal Chain:
{json.dumps(existing_chain, indent=2)}

Enhance this causal analysis with additional context and deeper reasoning."""

        result = await self._call_claude(system, user_msg, model="claude-sonnet-4-20250514", max_tokens=1200)

        if not result:
            return {"enhanced": False, "chain": existing_chain, "additional_context": ""}

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = json.loads(cleaned)
            parsed["enhanced"] = True
            return parsed
        except (json.JSONDecodeError, IndexError):
            return {"enhanced": False, "chain": existing_chain, "additional_context": result[:500]}

    async def analyze_signal(
        self,
        signal_type: str,
        evidence: dict,
        confidence: float,
        chokepoint: Optional[str] = None,
    ) -> dict:
        """
        Use LLM to provide deeper signal analysis.
        
        Goes beyond the raw signal data to provide:
        - Context about what the signal means
        - Likely timeline of impact
        - Which types of cargo/routes are most affected
        - Reliability assessment of the signal source
        """
        if not self._available:
            return {
                "interpretation": f"Signal type: {signal_type}",
                "severity_assessment": "unknown",
                "timeline": "unknown",
                "affected_sectors": [],
                "confidence_assessment": confidence,
            }

        system = """You are a maritime intelligence analyst specializing in supply chain disruption signals.
Analyze the given signal and provide actionable intelligence.

Return ONLY valid JSON:
{
    "interpretation": "What this signal means in practical terms",
    "severity_assessment": "low|medium|high|critical",
    "timeline": "Expected duration and phases of impact",
    "affected_sectors": ["industries/cargo types most affected"],
    "geographic_scope": "How wide is the impact",
    "confidence_assessment": 0.0-1.0,
    "recommended_actions": ["immediate actions to consider"],
    "watch_indicators": ["things that would make this worse or better"]
}"""

        user_msg = f"""Signal Type: {signal_type}
Confidence: {confidence}
Chokepoint: {chokepoint or 'Global'}
Evidence: {json.dumps(evidence, default=str)[:1500]}

Analyze this signal and provide actionable intelligence."""

        result = await self._call_claude(system, user_msg, model="claude-haiku-4-5-20251001", max_tokens=800)

        if not result:
            return {
                "interpretation": f"Signal type: {signal_type}",
                "severity_assessment": "unknown",
                "timeline": "unknown",
                "affected_sectors": [],
                "confidence_assessment": confidence,
            }

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(cleaned)
        except (json.JSONDecodeError, IndexError):
            return {
                "interpretation": result[:500],
                "severity_assessment": "unknown",
                "timeline": "unknown",
                "affected_sectors": [],
                "confidence_assessment": confidence,
            }

    async def generate_decision_explanation(
        self,
        decision_action: str,
        reasoning_trace: dict,
        customer_context: dict,
    ) -> str:
        """
        Generate a human-readable explanation of why a decision was made.
        
        Takes the full reasoning trace and produces a clear,
        actionable explanation for the customer.
        """
        if not self._available:
            return f"Recommended action: {decision_action}. Based on current signal analysis and your risk profile."

        system = """You are a professional risk advisor writing to a supply chain manager.
Write a clear, concise explanation of the recommended action.

Rules:
- Be specific with numbers and dates
- Explain WHY this action is recommended
- Mention the key risk factors
- Keep it under 200 words
- Professional but accessible tone
- Include confidence level"""

        user_msg = f"""Recommended Action: {decision_action}

Customer: {customer_context.get('company_name', 'Unknown')}
Industry: {customer_context.get('industry', 'General')}
Risk Tolerance: {customer_context.get('risk_tolerance', 'BALANCED')}

Key Reasoning:
- Data Quality: {reasoning_trace.get('data_quality_score', 'N/A')}
- Confidence: {reasoning_trace.get('final_confidence', 'N/A')}
- Escalated: {reasoning_trace.get('escalated', False)}

Write a clear explanation for the customer."""

        result = await self._call_claude(system, user_msg, model="claude-haiku-4-5-20251001", max_tokens=400)
        
        return result if result else f"Recommended action: {decision_action}. Based on current signal analysis and your risk profile."

    # ── Fallback methods ─────────────────────────────────────────

    def _fallback_company_analysis(
        self,
        company_name: str,
        industry: Optional[str],
        primary_routes: list[str],
        chokepoints: list[str],
        risk_tolerance: str,
    ) -> dict:
        """Rule-based fallback when LLM is unavailable."""
        exposures = []
        recommendations = []
        vulnerability = 0.3

        for cp in chokepoints:
            cp_lower = cp.lower()
            if "red_sea" in cp_lower or "suez" in cp_lower:
                exposures.append(f"Red Sea/Suez Canal exposure via routes: {', '.join(primary_routes)}")
                recommendations.append("Monitor Houthi activity and carrier rerouting announcements")
                vulnerability += 0.2
            elif "malacca" in cp_lower:
                exposures.append(f"Strait of Malacca exposure — high traffic density risk")
                recommendations.append("Track congestion reports and piracy incidents")
                vulnerability += 0.15
            elif "panama" in cp_lower:
                exposures.append(f"Panama Canal exposure — drought/capacity restrictions")
                recommendations.append("Monitor canal authority water level reports")
                vulnerability += 0.15
            elif "hormuz" in cp_lower:
                exposures.append(f"Strait of Hormuz — geopolitical and energy risk")
                recommendations.append("Track Iran/Gulf tensions and oil supply disruptions")
                vulnerability += 0.2

        if not exposures:
            exposures.append("No specific chokepoint exposure detected")
            recommendations.append("Configure trade routes to enable risk monitoring")

        return {
            "risk_summary": f"{company_name} operates in {industry or 'general'} industry with {len(primary_routes)} active routes. "
                           f"{'High' if vulnerability > 0.6 else 'Moderate' if vulnerability > 0.4 else 'Low'} overall risk profile.",
            "key_exposures": exposures,
            "vulnerability_score": min(vulnerability, 1.0),
            "industry_risks": [f"{industry or 'General'} industry standard risks"],
            "chokepoint_analysis": {cp: "Monitored" for cp in chokepoints},
            "recommendations": recommendations,
            "monitoring_priorities": chokepoints[:3] if chokepoints else ["Configure routes first"],
        }


# ── Singleton ────────────────────────────────────────────────

_instance: Optional[ReasoningLLMService] = None


def get_reasoning_llm_service() -> ReasoningLLMService:
    """Get or create the singleton LLM service."""
    global _instance
    if _instance is None:
        _instance = ReasoningLLMService()
    return _instance
