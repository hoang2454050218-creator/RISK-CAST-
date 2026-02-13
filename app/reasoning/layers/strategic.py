"""
Layer 5: Strategic Reasoning.

Responsibilities:
- Assess alignment with customer's risk tolerance
- Evaluate long-term impacts
- Consider relationship effects
- Check portfolio concentration

This layer answers: "Does this fit customer's strategy?"
"""

from datetime import datetime
from typing import Any, Optional
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    StrategicLayerOutput,
)

logger = structlog.get_logger(__name__)


class StrategicLayer:
    """
    Layer 5: Strategic Reasoning.
    
    Evaluates decisions against customer's:
    - Risk tolerance
    - Long-term business goals
    - Carrier/supplier relationships
    - Portfolio concentration
    
    May recommend strategic override of tactical decision.
    """
    
    # Risk tolerance thresholds
    RISK_TOLERANCE_THRESHOLDS = {
        "conservative": {
            "max_exposure_pct": 0.05,  # 5% of cargo value
            "min_mitigation_confidence": 0.80,
            "accept_tail_risk": False,
        },
        "moderate": {
            "max_exposure_pct": 0.10,  # 10%
            "min_mitigation_confidence": 0.65,
            "accept_tail_risk": False,
        },
        "aggressive": {
            "max_exposure_pct": 0.20,  # 20%
            "min_mitigation_confidence": 0.50,
            "accept_tail_risk": True,
        },
    }
    
    async def execute(self, inputs: dict) -> StrategicLayerOutput:
        """
        Execute strategic reasoning layer.
        
        Args:
            inputs: Dict with 'counterfactual', 'context'
        """
        counterfactual = inputs.get("counterfactual")
        context = inputs.get("context")
        
        started_at = datetime.utcnow()
        
        # Get customer profile
        profile = getattr(context, "profile", None)
        risk_tolerance = getattr(profile, "risk_tolerance", "moderate")
        
        # Assess risk tolerance alignment
        alignment, alignment_details = self._assess_risk_alignment(
            counterfactual, context, risk_tolerance
        )
        
        # Evaluate long-term impact
        long_term_impact, long_term_details = self._evaluate_long_term_impact(
            counterfactual, context
        )
        
        # Consider relationship effects
        relationship_impact, relationship_considerations = self._consider_relationships(
            counterfactual, context
        )
        
        # Check portfolio concentration
        portfolio_exposure, concentration_risk = self._check_portfolio(context)
        
        # Determine if strategic override needed
        strategic_override, override_reason = self._check_strategic_override(
            counterfactual,
            alignment,
            long_term_impact,
            risk_tolerance,
        )
        
        completed_at = datetime.utcnow()
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            alignment, counterfactual, context
        )
        
        # Generate warnings
        warnings = self._generate_warnings(
            alignment, concentration_risk, strategic_override
        )
        
        output = StrategicLayerOutput(
            layer=ReasoningLayer.STRATEGIC,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "risk_tolerance": risk_tolerance,
                "robust_action": counterfactual.robust_action if counterfactual else None,
            },
            outputs={
                "alignment_score": alignment,
                "has_override": strategic_override is not None,
            },
            confidence=confidence,
            depends_on=[ReasoningLayer.COUNTERFACTUAL],
            risk_tolerance_alignment=alignment,
            long_term_impact=long_term_impact,
            long_term_impact_details=long_term_details,
            relationship_impact=relationship_impact,
            relationship_considerations=relationship_considerations,
            portfolio_exposure=portfolio_exposure,
            concentration_risk=concentration_risk,
            strategic_override=strategic_override,
            strategic_override_reason=override_reason,
            warnings=warnings,
        )
        
        logger.debug(
            "strategic_layer_complete",
            alignment=alignment,
            strategic_override=strategic_override,
            concentration_risk=concentration_risk,
        )
        
        return output
    
    def _assess_risk_alignment(
        self,
        counterfactual: Any,
        context: Any,
        risk_tolerance: str,
    ) -> tuple[float, str]:
        """Assess how well recommended action aligns with risk tolerance."""
        thresholds = self.RISK_TOLERANCE_THRESHOLDS.get(
            risk_tolerance, self.RISK_TOLERANCE_THRESHOLDS["moderate"]
        )
        
        if not counterfactual:
            return 0.5, "No counterfactual analysis available"
        
        recommended_action = counterfactual.robust_action or "monitor"
        robustness = counterfactual.robustness_score
        
        alignment_score = 0.5
        details = []
        
        # Check robustness against tolerance
        min_confidence = thresholds["min_mitigation_confidence"]
        if robustness >= min_confidence:
            alignment_score += 0.25
            details.append(f"Robustness ({robustness:.0%}) meets threshold ({min_confidence:.0%})")
        else:
            alignment_score -= 0.25
            details.append(f"Robustness ({robustness:.0%}) below threshold ({min_confidence:.0%})")
        
        # Check action appropriateness for risk tolerance
        if risk_tolerance == "conservative":
            # Conservative prefers protective actions
            if recommended_action in ["reroute", "insure"]:
                alignment_score += 0.25
                details.append("Protective action aligns with conservative tolerance")
            elif recommended_action == "do_nothing":
                alignment_score -= 0.25
                details.append("Inaction may not align with conservative tolerance")
        elif risk_tolerance == "aggressive":
            # Aggressive tolerates more risk
            if recommended_action in ["monitor", "do_nothing"]:
                alignment_score += 0.15
                details.append("Lighter action aligns with aggressive tolerance")
        
        return min(max(alignment_score, 0), 1), "; ".join(details)
    
    def _evaluate_long_term_impact(
        self,
        counterfactual: Any,
        context: Any,
    ) -> tuple[str, str]:
        """Evaluate long-term business impact."""
        if not counterfactual:
            return "neutral", "Insufficient data for long-term assessment"
        
        action = counterfactual.robust_action
        
        if action == "reroute":
            # Rerouting has costs but protects relationships
            return "neutral", "Rerouting incurs costs but maintains delivery commitments"
        elif action == "delay":
            # Delays can harm relationships
            return "negative", "Delays may impact customer relationships and contracts"
        elif action == "insure":
            # Insurance is protective
            return "positive", "Insurance protects against tail risk with limited downside"
        elif action == "monitor":
            # Monitoring preserves optionality
            return "neutral", "Monitoring preserves options but may miss optimal timing"
        else:
            return "neutral", "Minimal long-term impact expected"
    
    def _consider_relationships(
        self,
        counterfactual: Any,
        context: Any,
    ) -> tuple[str, list[str]]:
        """Consider carrier and supplier relationships."""
        considerations = []
        impact = "neutral"
        
        if not counterfactual:
            return impact, considerations
        
        action = counterfactual.robust_action
        
        # Carrier relationships
        if action == "reroute":
            considerations.append("May need to negotiate with carriers for alternative routes")
            considerations.append("Preferred carrier relationships may provide priority booking")
        elif action == "delay":
            considerations.append("Carriers may charge demurrage or storage fees")
        
        # Customer relationships (downstream)
        profile = getattr(context, "profile", None)
        if profile:
            if getattr(profile, "has_sla", False):
                considerations.append("SLA commitments must be considered")
                if action == "delay":
                    impact = "negative"
                    considerations.append("Delay may trigger SLA penalties")
        
        return impact, considerations
    
    def _check_portfolio(
        self,
        context: Any,
    ) -> tuple[float, str]:
        """Check portfolio exposure and concentration."""
        if not context:
            return 0.0, "low"
        
        shipments = getattr(context, "active_shipments", [])
        if not shipments:
            return 0.0, "low"
        
        # Calculate total exposure
        total_value = sum(getattr(s, "cargo_value_usd", 0) for s in shipments)
        
        # Calculate concentration by chokepoint
        chokepoint_exposure = {}
        for shipment in shipments:
            chokepoints = getattr(shipment, "route_chokepoints", [])
            value = getattr(shipment, "cargo_value_usd", 0)
            for cp in chokepoints:
                chokepoint_exposure[cp] = chokepoint_exposure.get(cp, 0) + value
        
        # Portfolio exposure as percentage
        if total_value > 0 and chokepoint_exposure:
            max_cp_exposure = max(chokepoint_exposure.values())
            portfolio_pct = max_cp_exposure / total_value
        else:
            portfolio_pct = 0.0
        
        # Determine concentration risk level
        if portfolio_pct > 0.5:
            concentration = "critical"
        elif portfolio_pct > 0.3:
            concentration = "high"
        elif portfolio_pct > 0.15:
            concentration = "medium"
        else:
            concentration = "low"
        
        return portfolio_pct, concentration
    
    def _check_strategic_override(
        self,
        counterfactual: Any,
        alignment: float,
        long_term_impact: str,
        risk_tolerance: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """Check if strategic considerations override tactical recommendation."""
        if not counterfactual:
            return None, None
        
        tactical_action = counterfactual.robust_action
        
        # Strategic override conditions
        
        # 1. Conservative customer with risky recommendation
        if risk_tolerance == "conservative" and tactical_action == "do_nothing":
            return "monitor", "Conservative customer should at minimum monitor situation"
        
        # 2. Low alignment score suggests mismatch
        if alignment < 0.4:
            if tactical_action == "do_nothing":
                return "monitor", f"Low alignment ({alignment:.0%}) suggests more caution"
            elif tactical_action == "reroute" and risk_tolerance == "aggressive":
                return "monitor", "Aggressive tolerance may prefer waiting for more info"
        
        # 3. Negative long-term impact
        if long_term_impact == "negative" and tactical_action == "delay":
            return "reroute", "Reroute preferred to avoid relationship damage from delay"
        
        return None, None
    
    def _calculate_confidence(
        self,
        alignment: float,
        counterfactual: Any,
        context: Any,
    ) -> float:
        """Calculate confidence in strategic assessment."""
        confidence = 0.5
        
        # Higher confidence with better alignment
        confidence += alignment * 0.3
        
        # Higher confidence with counterfactual data
        if counterfactual:
            confidence += 0.1
        
        # Higher confidence with customer profile
        if context and getattr(context, "profile", None):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_warnings(
        self,
        alignment: float,
        concentration: str,
        override: Optional[str],
    ) -> list[str]:
        """Generate strategic warnings."""
        warnings = []
        
        if alignment < 0.5:
            warnings.append(f"Recommendation may not align with risk tolerance ({alignment:.0%})")
        
        if concentration in ["high", "critical"]:
            warnings.append(f"Portfolio concentration risk is {concentration}")
        
        if override:
            warnings.append(f"Strategic override: {override}")
        
        return warnings
