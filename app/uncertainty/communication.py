"""
Confidence Communication Module - Translate uncertainty to actionable guidance.

This module addresses audit gap A4.4 (Confidence Communication = 3/25):
- Uncertainty always communicated (not just point estimates)
- Uncertainty calibrated ("high confidence" is actually reliable)
- Uncertainty actionable (what would reduce it?)
- Uncertainty language appropriate (technical vs accessible)

Every decision should include ConfidenceGuidance that tells users:
1. Whether to act or wait
2. What the uncertainty ranges are
3. What would reduce uncertainty
4. Risk-adjusted recommendations (conservative/balanced/aggressive)
"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, computed_field
import structlog

if TYPE_CHECKING:
    from app.riskcast.schemas.decision import DecisionObject

from app.uncertainty.bayesian import UncertainValue

logger = structlog.get_logger(__name__)


# ============================================================================
# UNCERTAINTY LEVELS
# ============================================================================


class UncertaintyLevel(str, Enum):
    """Classification of uncertainty based on CI width relative to estimate."""
    VERY_LOW = "very_low"       # CI width < 10% of estimate
    LOW = "low"                 # CI width 10-25%
    MODERATE = "moderate"       # CI width 25-50%
    HIGH = "high"               # CI width 50-100%
    VERY_HIGH = "very_high"     # CI width > 100%


class ActConfidence(str, Enum):
    """Confidence level for taking action."""
    HIGH = "high"               # Strong confidence to act immediately
    MODERATE = "moderate"       # Act recommended but monitor closely
    LOW = "low"                 # Consider waiting for more information
    VERY_LOW = "very_low"       # Recommend human review before acting


# ============================================================================
# UNCERTAINTY REDUCERS
# ============================================================================


class UncertaintyReducer(BaseModel):
    """A specific action that would reduce uncertainty."""
    
    action: str = Field(description="What to do to reduce uncertainty")
    impact: str = Field(description="Which uncertainty it reduces")
    time_required: str = Field(description="How long it takes")
    difficulty: str = Field(default="easy", description="easy/medium/hard")
    
    def __str__(self) -> str:
        return f"{self.action} ({self.impact}, ~{self.time_required})"


# ============================================================================
# RISK-ADJUSTED RECOMMENDATIONS
# ============================================================================


class RiskAdjustedRecommendations(BaseModel):
    """Recommendations at different risk tolerance levels."""
    
    conservative: str = Field(
        description="What to do if risk-averse (minimize worst case)"
    )
    balanced: str = Field(
        description="What to do with balanced risk tolerance (optimize EV)"
    )
    aggressive: str = Field(
        description="What to do if risk-seeking (maximize upside)"
    )
    
    conservative_rationale: str = Field(
        default="",
        description="Why conservative action makes sense"
    )
    balanced_rationale: str = Field(
        default="",
        description="Why balanced action makes sense"
    )
    aggressive_rationale: str = Field(
        default="",
        description="Why aggressive action makes sense"
    )


# ============================================================================
# CONFIDENCE GUIDANCE - MAIN OUTPUT
# ============================================================================


class ConfidenceGuidance(BaseModel):
    """
    Actionable guidance based on confidence and uncertainty.
    
    This is the key deliverable for A4.4 Confidence Communication.
    Every decision should include this to help users understand
    and act on uncertainty appropriately.
    """
    
    # Core confidence metrics
    confidence_score: float = Field(
        ge=0, le=1,
        description="Overall confidence score (0-1)"
    )
    calibrated_score: float = Field(
        ge=0, le=1,
        description="Confidence after calibration adjustment"
    )
    confidence_level: str = Field(
        description="Human-readable level: LOW/MODERATE/HIGH"
    )
    uncertainty_level: UncertaintyLevel = Field(
        description="Uncertainty classification based on CI width"
    )
    
    # Key prediction ranges (formatted for display)
    exposure_range: str = Field(
        description="e.g., '$150K-$320K (90% confidence)'"
    )
    delay_range: str = Field(
        description="e.g., '7-14 days (90% confidence)'"
    )
    cost_range: str = Field(
        description="e.g., '$8,000-$12,000 (90% confidence)'"
    )
    
    # Action guidance
    should_act: bool = Field(
        description="Whether action is recommended given uncertainty"
    )
    act_confidence: ActConfidence = Field(
        description="Confidence level for taking action"
    )
    act_confidence_text: str = Field(
        description="Plain language explanation of act confidence"
    )
    
    # Uncertainty reducers
    uncertainty_reducers: List[UncertaintyReducer] = Field(
        default_factory=list,
        description="Actions that would reduce uncertainty"
    )
    
    # Risk-adjusted recommendations
    risk_adjusted: RiskAdjustedRecommendations = Field(
        description="Recommendations at different risk levels"
    )
    
    # Impact of data quality on confidence
    data_quality_impact: str = Field(
        description="How data quality affects confidence"
    )
    model_confidence_impact: str = Field(
        description="How model uncertainty affects confidence"
    )
    
    # Plain language summary
    plain_language_summary: str = Field(
        description="1-2 paragraph explanation for non-technical users"
    )
    
    # Wait guidance
    should_wait_hours: Optional[int] = Field(
        default=None,
        description="If should wait, how many hours"
    )
    wait_reason: Optional[str] = Field(
        default=None,
        description="Why waiting might be beneficial"
    )
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_high_uncertainty(self) -> bool:
        """Flag if uncertainty is concerning."""
        return self.uncertainty_level in [
            UncertaintyLevel.HIGH, 
            UncertaintyLevel.VERY_HIGH
        ]
    
    @computed_field
    @property
    def action_recommended(self) -> bool:
        """Alias for should_act."""
        return self.should_act
    
    def get_top_uncertainty_reducers(self, n: int = 3) -> List[str]:
        """Get top N uncertainty reducers as strings."""
        return [str(r) for r in self.uncertainty_reducers[:n]]


# ============================================================================
# CONFIDENCE COMMUNICATOR
# ============================================================================


class ConfidenceCommunicator:
    """
    Translates uncertainty metrics into actionable guidance.
    
    This class is the main entry point for generating ConfidenceGuidance
    from decision data and uncertain values.
    """
    
    # Thresholds for classification
    CI_WIDTH_THRESHOLDS = {
        UncertaintyLevel.VERY_LOW: 0.10,
        UncertaintyLevel.LOW: 0.25,
        UncertaintyLevel.MODERATE: 0.50,
        UncertaintyLevel.HIGH: 1.00,
        # VERY_HIGH is anything above 1.00
    }
    
    # Action thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    MODERATE_CONFIDENCE_THRESHOLD = 0.55
    LOW_CONFIDENCE_THRESHOLD = 0.40
    
    def generate_guidance(
        self,
        decision: "DecisionObject",
        exposure_uncertain: UncertainValue,
        delay_uncertain: UncertainValue,
        cost_uncertain: UncertainValue,
        calibrated_confidence: Optional[float] = None,
    ) -> ConfidenceGuidance:
        """
        Generate comprehensive confidence guidance for a decision.
        
        Args:
            decision: The decision object
            exposure_uncertain: Uncertain exposure value with CIs
            delay_uncertain: Uncertain delay value with CIs
            cost_uncertain: Uncertain action cost value with CIs
            calibrated_confidence: Optional calibrated confidence score
            
        Returns:
            ConfidenceGuidance with full actionable uncertainty information
        """
        # Get raw confidence from decision
        raw_confidence = decision.q6_confidence.score
        calibrated = calibrated_confidence or raw_confidence
        
        # Calculate uncertainty level from exposure CI
        uncertainty_level = self._classify_uncertainty(exposure_uncertain)
        
        # Determine if should act
        should_act = self._should_act(
            calibrated, 
            uncertainty_level, 
            decision,
            exposure_uncertain,
            cost_uncertain,
        )
        
        # Get act confidence
        act_confidence = self._get_act_confidence(calibrated, uncertainty_level)
        
        # Generate uncertainty reducers
        reducers = self._identify_uncertainty_reducers(
            decision, 
            exposure_uncertain,
            delay_uncertain,
        )
        
        # Generate risk-adjusted recommendations
        risk_adjusted = self._generate_risk_adjusted_recommendations(
            decision,
            exposure_uncertain,
            cost_uncertain,
        )
        
        # Format ranges
        exposure_range = self._format_range(exposure_uncertain, prefix="$", suffix="")
        delay_range = self._format_range(delay_uncertain, prefix="", suffix=" days")
        cost_range = self._format_range(cost_uncertain, prefix="$", suffix="")
        
        # Generate plain language summary
        plain_summary = self._generate_plain_summary(
            decision,
            calibrated,
            uncertainty_level,
            should_act,
            exposure_uncertain,
        )
        
        # Data quality and model impact
        data_quality_impact = self._assess_data_quality_impact(decision)
        model_confidence_impact = self._assess_model_confidence_impact(decision)
        
        # Wait guidance
        should_wait_hours = None
        wait_reason = None
        if not should_act and calibrated < self.MODERATE_CONFIDENCE_THRESHOLD:
            should_wait_hours = 6
            wait_reason = (
                "Waiting 6 hours may provide updated signals and reduce uncertainty. "
                "Monitor for carrier announcements or market movements."
            )
        
        return ConfidenceGuidance(
            confidence_score=raw_confidence,
            calibrated_score=calibrated,
            confidence_level=decision.q6_confidence.level.value,
            uncertainty_level=uncertainty_level,
            exposure_range=exposure_range,
            delay_range=delay_range,
            cost_range=cost_range,
            should_act=should_act,
            act_confidence=act_confidence,
            act_confidence_text=self._get_act_confidence_text(act_confidence, uncertainty_level),
            uncertainty_reducers=reducers,
            risk_adjusted=risk_adjusted,
            data_quality_impact=data_quality_impact,
            model_confidence_impact=model_confidence_impact,
            plain_language_summary=plain_summary,
            should_wait_hours=should_wait_hours,
            wait_reason=wait_reason,
        )
    
    def _classify_uncertainty(self, uncertain_value: UncertainValue) -> UncertaintyLevel:
        """Classify uncertainty level based on CI width relative to estimate."""
        if uncertain_value.point_estimate == 0:
            return UncertaintyLevel.VERY_HIGH
        
        ci_width = uncertain_value.ci_90[1] - uncertain_value.ci_90[0]
        width_ratio = ci_width / abs(uncertain_value.point_estimate)
        
        if width_ratio < self.CI_WIDTH_THRESHOLDS[UncertaintyLevel.VERY_LOW]:
            return UncertaintyLevel.VERY_LOW
        elif width_ratio < self.CI_WIDTH_THRESHOLDS[UncertaintyLevel.LOW]:
            return UncertaintyLevel.LOW
        elif width_ratio < self.CI_WIDTH_THRESHOLDS[UncertaintyLevel.MODERATE]:
            return UncertaintyLevel.MODERATE
        elif width_ratio < self.CI_WIDTH_THRESHOLDS[UncertaintyLevel.HIGH]:
            return UncertaintyLevel.HIGH
        else:
            return UncertaintyLevel.VERY_HIGH
    
    def _should_act(
        self,
        confidence: float,
        uncertainty: UncertaintyLevel,
        decision: "DecisionObject",
        exposure: UncertainValue,
        cost: UncertainValue,
    ) -> bool:
        """Determine if action is warranted given uncertainty."""
        # High confidence + low uncertainty = definitely act
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            if uncertainty in [UncertaintyLevel.VERY_LOW, UncertaintyLevel.LOW]:
                return True
        
        # Even with uncertainty, act if expected value is strongly positive
        # Risk mitigated >> action cost
        action_cost = decision.q5_action.estimated_cost_usd
        inaction_cost = decision.q7_inaction.expected_loss_if_nothing
        
        # If inaction cost is much higher than action cost, act anyway
        if inaction_cost > action_cost * 3:
            logger.info(
                "recommending_action_despite_uncertainty",
                reason="inaction_cost_much_higher",
                inaction_cost=inaction_cost,
                action_cost=action_cost,
            )
            return True
        
        # Check worst case scenario
        # Even in pessimistic scenario, is action still better?
        worst_case_inaction = decision.q7_inaction.worst_case_cost
        worst_case_action_cost = cost.ci_95[1]  # Upper bound of action cost
        
        if worst_case_inaction > worst_case_action_cost * 2:
            return True
        
        # Low confidence or high uncertainty = consider waiting
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return False
        
        if uncertainty in [UncertaintyLevel.HIGH, UncertaintyLevel.VERY_HIGH]:
            # Only act if the expected value is very clearly positive
            if inaction_cost > action_cost * 2:
                return True
            return False
        
        # Moderate confidence, moderate uncertainty = act if EV positive
        return confidence >= self.MODERATE_CONFIDENCE_THRESHOLD
    
    def _get_act_confidence(
        self, 
        confidence: float, 
        uncertainty: UncertaintyLevel,
    ) -> ActConfidence:
        """Get the action confidence level."""
        if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            if uncertainty in [UncertaintyLevel.VERY_LOW, UncertaintyLevel.LOW]:
                return ActConfidence.HIGH
            return ActConfidence.MODERATE
        elif confidence >= self.MODERATE_CONFIDENCE_THRESHOLD:
            if uncertainty in [UncertaintyLevel.HIGH, UncertaintyLevel.VERY_HIGH]:
                return ActConfidence.LOW
            return ActConfidence.MODERATE
        elif confidence >= self.LOW_CONFIDENCE_THRESHOLD:
            return ActConfidence.LOW
        else:
            return ActConfidence.VERY_LOW
    
    def _get_act_confidence_text(
        self, 
        act_confidence: ActConfidence,
        uncertainty: UncertaintyLevel,
    ) -> str:
        """Get plain text explanation of act confidence."""
        texts = {
            ActConfidence.HIGH: (
                "HIGH confidence to act - proceed with recommended action. "
                "Uncertainty is manageable and expected value is clearly positive."
            ),
            ActConfidence.MODERATE: (
                "MODERATE confidence to act - action is recommended but monitor closely. "
                "Some uncertainty remains; be prepared to adjust if conditions change."
            ),
            ActConfidence.LOW: (
                "LOW confidence - consider waiting for more information. "
                "Uncertainty is significant. If action is time-sensitive, proceed with caution."
            ),
            ActConfidence.VERY_LOW: (
                "VERY LOW confidence - recommend human review before acting. "
                "Uncertainty is high and expected value is unclear."
            ),
        }
        
        base_text = texts.get(act_confidence, texts[ActConfidence.LOW])
        
        if uncertainty == UncertaintyLevel.VERY_HIGH:
            base_text += " Note: Estimates have very wide uncertainty ranges."
        
        return base_text
    
    def _identify_uncertainty_reducers(
        self,
        decision: "DecisionObject",
        exposure: UncertainValue,
        delay: UncertainValue,
    ) -> List[UncertaintyReducer]:
        """Identify actions that would reduce uncertainty."""
        reducers = []
        
        # Check confidence factors
        factors = decision.q6_confidence.factors
        
        # Signal probability uncertainty
        if factors.get("signal_probability", 1.0) < 0.7:
            reducers.append(UncertaintyReducer(
                action="Wait for additional signal confirmation from news or market",
                impact="Reduces signal uncertainty",
                time_required="2-6 hours",
                difficulty="easy",
            ))
        
        # Correlation/reality confirmation
        if factors.get("intelligence_correlation", 1.0) < 0.7:
            reducers.append(UncertaintyReducer(
                action="Verify vessel positions directly with carrier",
                impact="Confirms disruption is affecting your routes",
                time_required="1-2 hours",
                difficulty="medium",
            ))
        
        # Impact assessment uncertainty
        if factors.get("impact_assessment", 1.0) < 0.7:
            reducers.append(UncertaintyReducer(
                action="Confirm cargo value and contract penalties with customer",
                impact="Improves cost estimate accuracy",
                time_required="30 minutes",
                difficulty="easy",
            ))
        
        # Delay uncertainty
        if delay.uncertainty_ratio > 0.5:
            reducers.append(UncertaintyReducer(
                action="Request ETAs from carriers for affected shipments",
                impact="Narrows delay estimate range",
                time_required="1-4 hours",
                difficulty="medium",
            ))
        
        # Exposure uncertainty
        if exposure.uncertainty_ratio > 0.5:
            reducers.append(UncertaintyReducer(
                action="Review contract terms for penalty clauses and grace periods",
                impact="Clarifies penalty exposure",
                time_required="15 minutes",
                difficulty="easy",
            ))
        
        # General time-based reducer
        reducers.append(UncertaintyReducer(
            action="Wait 6 hours for updated market signals and AIS data",
            impact="General uncertainty reduction as situation clarifies",
            time_required="6 hours",
            difficulty="easy",
        ))
        
        # Return top 5 most impactful
        return reducers[:5]
    
    def _generate_risk_adjusted_recommendations(
        self,
        decision: "DecisionObject",
        exposure: UncertainValue,
        cost: UncertainValue,
    ) -> RiskAdjustedRecommendations:
        """Generate recommendations at different risk tolerance levels."""
        action_type = decision.q5_action.action_type
        action_cost = decision.q5_action.estimated_cost_usd
        inaction_loss = decision.q7_inaction.expected_loss_if_nothing
        
        # Conservative: minimize worst case
        conservative_action = f"MONITOR for 24 hours, then {action_type} if signals strengthen"
        conservative_rationale = (
            f"Worst case action cost is ${cost.ci_95[1]:,.0f}. "
            f"Waiting may clarify situation and reduce uncertainty."
        )
        
        # Balanced: optimize expected value
        balanced_action = f"{action_type} - expected value positive with current confidence"
        balanced_rationale = (
            f"Expected action cost ${action_cost:,.0f} vs expected inaction loss ${inaction_loss:,.0f}. "
            f"Net expected benefit: ${(inaction_loss - action_cost):,.0f}."
        )
        
        # Aggressive: maximize upside, capture time value
        aggressive_action = f"{action_type} immediately to capture maximum time value"
        aggressive_rationale = (
            f"Acting now preserves optionality. Delay costs escalate: "
            f"${decision.q7_inaction.cost_if_wait_6h:,.0f} in 6h, "
            f"${decision.q7_inaction.cost_if_wait_24h:,.0f} in 24h."
        )
        
        return RiskAdjustedRecommendations(
            conservative=conservative_action,
            balanced=balanced_action,
            aggressive=aggressive_action,
            conservative_rationale=conservative_rationale,
            balanced_rationale=balanced_rationale,
            aggressive_rationale=aggressive_rationale,
        )
    
    def _format_range(
        self, 
        uncertain: UncertainValue, 
        prefix: str = "",
        suffix: str = "",
    ) -> str:
        """Format uncertain value as range string."""
        low, high = uncertain.ci_90
        point = uncertain.point_estimate
        
        # Format based on magnitude
        if abs(point) >= 10000:
            return f"{prefix}{point:,.0f}{suffix} [{prefix}{low:,.0f} - {prefix}{high:,.0f}] (90% CI)"
        elif abs(point) >= 100:
            return f"{prefix}{point:,.0f}{suffix} [{prefix}{low:,.0f} - {prefix}{high:,.0f}] (90% CI)"
        else:
            return f"{prefix}{point:.1f}{suffix} [{prefix}{low:.1f} - {prefix}{high:.1f}] (90% CI)"
    
    def _generate_plain_summary(
        self,
        decision: "DecisionObject",
        confidence: float,
        uncertainty: UncertaintyLevel,
        should_act: bool,
        exposure: UncertainValue,
    ) -> str:
        """Generate plain language summary for non-technical users."""
        action = decision.q5_action.action_type
        action_cost = decision.q5_action.estimated_cost_usd
        inaction_loss = decision.q7_inaction.expected_loss_if_nothing
        
        if should_act:
            return f"""We recommend {action} with {confidence:.0%} confidence.

Your potential exposure is ${exposure.point_estimate:,.0f}, though this could reasonably range from ${exposure.ci_90[0]:,.0f} to ${exposure.ci_90[1]:,.0f}. The cost of action (${action_cost:,.0f}) appears justified by the expected loss if you do nothing (${inaction_loss:,.0f}).

Uncertainty level is {uncertainty.value.replace('_', ' ')}. While our estimates may vary from actual outcomes, the expected value calculation favors taking action now rather than waiting."""
        else:
            return f"""We suggest MONITORING rather than immediate {action}.

While there is ${exposure.point_estimate:,.0f} potential exposure (range: ${exposure.ci_90[0]:,.0f} to ${exposure.ci_90[1]:,.0f}), our confidence ({confidence:.0%}) is below the threshold for immediate action. 

Uncertainty is {uncertainty.value.replace('_', ' ')}. We recommend waiting for additional confirmation before committing to action. Check back in 6-12 hours for updated signals, or proceed with caution if the situation is time-critical."""
    
    def _assess_data_quality_impact(self, decision: "DecisionObject") -> str:
        """Assess how data quality affects confidence."""
        factors = decision.q6_confidence.factors
        signal = factors.get("signal_probability", 0.5)
        
        if signal >= 0.8:
            return "Data quality is HIGH - signal sources are reliable and recent."
        elif signal >= 0.6:
            return "Data quality is MODERATE - some signal sources may be dated or uncertain."
        else:
            return "Data quality is LOW - signal sources have limited reliability or freshness."
    
    def _assess_model_confidence_impact(self, decision: "DecisionObject") -> str:
        """Assess how model uncertainty affects confidence."""
        factors = decision.q6_confidence.factors
        impact = factors.get("impact_assessment", 0.5)
        
        if impact >= 0.8:
            return "Model confidence is HIGH - cost and delay estimates are based on strong historical patterns."
        elif impact >= 0.6:
            return "Model confidence is MODERATE - estimates are reasonable but historical data is limited."
        else:
            return "Model confidence is LOW - limited historical data makes estimates uncertain."


# ============================================================================
# FACTORY
# ============================================================================


def create_confidence_communicator() -> ConfidenceCommunicator:
    """Factory function to create ConfidenceCommunicator."""
    return ConfidenceCommunicator()
