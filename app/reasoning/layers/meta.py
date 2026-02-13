"""
Layer 6: Meta Reasoning.

The CRITICAL layer that decides whether to decide.

Responsibilities:
- Assess overall reasoning quality
- Decide: proceed with decision OR escalate to human
- Set confidence in the decision process itself

This layer answers: "Should I decide or escalate?"
"""

from datetime import datetime
from typing import Any, Optional, Dict
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    MetaLayerOutput,
    LayerOutput,
)

logger = structlog.get_logger(__name__)


class MetaLayer:
    """
    Layer 6: Meta Reasoning.
    
    The most important layer - decides whether to decide.
    
    Evaluates:
    - Data quality from factual layer
    - Reasoning quality across all layers
    - Decision robustness from counterfactual
    - Strategic alignment
    
    If quality is sufficient, proceeds with decision.
    Otherwise, escalates to human review.
    """
    
    # Thresholds for deciding to decide
    MIN_DATA_QUALITY = 0.5
    MIN_REASONING_CONFIDENCE = 0.55
    MIN_LAYER_CONFIDENCE = 0.4
    MAX_WARNINGS = 5
    MIN_ROBUSTNESS = 0.3
    
    async def execute(self, inputs: dict) -> MetaLayerOutput:
        """
        Execute meta reasoning layer.
        
        Args:
            inputs: Dict with 'all_layers', 'context'
        """
        all_layers = inputs.get("all_layers", {})
        context = inputs.get("context")
        
        started_at = datetime.utcnow()
        
        # Assess reasoning quality
        quality_assessment = self._assess_reasoning_quality(all_layers)
        
        # Decide whether to decide
        should_decide, decision_reason = self._decide_to_decide(
            quality_assessment,
            all_layers,
            context,
        )
        
        # Build escalation info if needed
        escalation_trigger = None
        escalation_reason = None
        escalation_urgency = None
        if not should_decide:
            escalation_trigger, escalation_reason, escalation_urgency = self._build_escalation_info(
                quality_assessment,
                decision_reason,
                all_layers,
            )
        
        # Build action info if deciding
        if_decide = {}
        if should_decide:
            if_decide = self._build_decision_info(all_layers)
        
        # Build escalation info
        if_escalate = {}
        if not should_decide:
            if_escalate = {
                "trigger": escalation_trigger,
                "reason": escalation_reason,
                "urgency": escalation_urgency,
                "recommended_reviewers": self._get_reviewers(context, quality_assessment),
            }
        
        completed_at = datetime.utcnow()
        
        output = MetaLayerOutput(
            layer=ReasoningLayer.META,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "layer_count": len(all_layers),
            },
            outputs={
                "should_decide": should_decide,
                "quality_score": quality_assessment["overall_score"],
            },
            confidence=quality_assessment["overall_score"],
            depends_on=list(all_layers.keys()),
            should_decide=should_decide,
            decision_reason=decision_reason,
            escalation_trigger=escalation_trigger,
            escalation_reason=escalation_reason,
            escalation_urgency=escalation_urgency,
            reasoning_confidence=quality_assessment["overall_score"],
            reasoning_quality_flags=quality_assessment["flags"],
            if_decide=if_decide,
            if_escalate=if_escalate,
            layer_quality_scores=quality_assessment["layer_scores"],
            warnings=quality_assessment["flags"][:5],  # Limit warnings
        )
        
        logger.info(
            "meta_layer_complete",
            should_decide=should_decide,
            quality_score=quality_assessment["overall_score"],
            escalated=not should_decide,
        )
        
        return output
    
    def _assess_reasoning_quality(
        self,
        layers: Dict[ReasoningLayer, LayerOutput],
    ) -> dict:
        """Assess quality of reasoning across all layers."""
        flags = []
        scores = {}
        
        # Check each layer
        for layer_type, layer_output in layers.items():
            if layer_type == ReasoningLayer.META:
                continue  # Don't assess ourselves
            
            if layer_output is None:
                flags.append(f"Missing {layer_type.value} layer")
                scores[layer_type.value] = 0.0
                continue
            
            scores[layer_type.value] = layer_output.confidence
            
            # Check for low confidence
            if layer_output.confidence < self.MIN_LAYER_CONFIDENCE:
                flags.append(f"Low confidence in {layer_type.value} layer ({layer_output.confidence:.0%})")
            
            # Collect layer warnings
            for warning in layer_output.warnings:
                flags.append(f"[{layer_type.value}] {warning}")
        
        # Check factual layer specifically
        factual = layers.get(ReasoningLayer.FACTUAL)
        if factual:
            if factual.data_quality_score < self.MIN_DATA_QUALITY:
                flags.append(f"Data quality below threshold ({factual.data_quality_score:.0%})")
            if factual.has_critical_gaps:
                flags.append("Critical data gaps identified")
        
        # Check counterfactual robustness
        counterfactual = layers.get(ReasoningLayer.COUNTERFACTUAL)
        if counterfactual:
            if counterfactual.robustness_score < self.MIN_ROBUSTNESS:
                flags.append(f"Decision robustness too low ({counterfactual.robustness_score:.0%})")
        
        # Calculate overall score
        if scores:
            overall_score = sum(scores.values()) / len(scores)
        else:
            overall_score = 0.0
        
        return {
            "overall_score": overall_score,
            "layer_scores": scores,
            "flags": flags,
        }
    
    def _decide_to_decide(
        self,
        quality: dict,
        layers: Dict[ReasoningLayer, LayerOutput],
        context: Any,
    ) -> tuple[bool, str]:
        """
        The crucial decision: should we make a decision?
        
        Returns (should_decide, reason)
        """
        # Check data quality
        factual = layers.get(ReasoningLayer.FACTUAL)
        if factual and factual.data_quality_score < self.MIN_DATA_QUALITY:
            return False, f"Data quality {factual.data_quality_score:.0%} below threshold {self.MIN_DATA_QUALITY:.0%}"
        
        # Check overall reasoning quality
        if quality["overall_score"] < self.MIN_REASONING_CONFIDENCE:
            return False, f"Reasoning confidence {quality['overall_score']:.0%} below threshold {self.MIN_REASONING_CONFIDENCE:.0%}"
        
        # Check warning count
        if len(quality["flags"]) > self.MAX_WARNINGS:
            return False, f"Too many quality warnings ({len(quality['flags'])})"
        
        # Check for conflicting signals / low robustness
        counterfactual = layers.get(ReasoningLayer.COUNTERFACTUAL)
        if counterfactual and counterfactual.robustness_score < self.MIN_ROBUSTNESS:
            return False, f"Decision too sensitive to assumptions (robustness {counterfactual.robustness_score:.0%})"
        
        # Check for strategic override
        strategic = layers.get(ReasoningLayer.STRATEGIC)
        if strategic and strategic.has_strategic_conflict:
            # Strategic conflict doesn't prevent decision, but logs warning
            pass
        
        # Customer requires manual review
        if context:
            profile = getattr(context, "profile", None)
            if profile and getattr(profile, "requires_manual_review", False):
                return False, "Customer flagged for manual review"
        
        # Check temporal urgency - if immediate, might want human check
        temporal = layers.get(ReasoningLayer.TEMPORAL)
        if temporal and temporal.urgency_level == "immediate":
            # Immediate urgency but quality is good - proceed
            pass
        
        # All checks passed
        return True, "All quality thresholds met"
    
    def _build_escalation_info(
        self,
        quality: dict,
        reason: str,
        layers: Dict[ReasoningLayer, LayerOutput],
    ) -> tuple[str, str, str]:
        """Build escalation trigger, reason, and urgency."""
        # Determine trigger type
        if "data quality" in reason.lower():
            trigger = "LOW_DATA_QUALITY"
        elif "confidence" in reason.lower():
            trigger = "LOW_CONFIDENCE"
        elif "warnings" in reason.lower():
            trigger = "QUALITY_WARNINGS"
        elif "robustness" in reason.lower():
            trigger = "LOW_ROBUSTNESS"
        elif "manual review" in reason.lower():
            trigger = "CUSTOMER_FLAG"
        else:
            trigger = "QUALITY_CHECK_FAILED"
        
        # Build detailed reason
        detailed_reason = reason
        if quality["flags"]:
            detailed_reason += f"\n\nFlags:\n- " + "\n- ".join(quality["flags"][:5])
        
        # Determine urgency
        temporal = layers.get(ReasoningLayer.TEMPORAL)
        if temporal:
            if temporal.urgency_level == "immediate":
                urgency = "high"
            elif temporal.urgency_level == "urgent":
                urgency = "medium"
            else:
                urgency = "low"
        else:
            urgency = "medium"
        
        return trigger, detailed_reason, urgency
    
    def _build_decision_info(
        self,
        layers: Dict[ReasoningLayer, LayerOutput],
    ) -> dict:
        """Build information for proceeding with decision."""
        info = {}
        
        # Get recommended action from counterfactual
        counterfactual = layers.get(ReasoningLayer.COUNTERFACTUAL)
        if counterfactual:
            if counterfactual.robust_action:
                info["action"] = counterfactual.robust_action
                info["source"] = "counterfactual_robust"
                info["robustness"] = counterfactual.robustness_score
            elif counterfactual.minimax_regret_action:
                info["action"] = counterfactual.minimax_regret_action
                info["source"] = "counterfactual_minimax"
        
        # Check for strategic override
        strategic = layers.get(ReasoningLayer.STRATEGIC)
        if strategic and strategic.strategic_override:
            info["strategic_override"] = strategic.strategic_override
            info["override_reason"] = strategic.strategic_override_reason
            # Use strategic override if present
            info["final_action"] = strategic.strategic_override
            info["source"] = "strategic_override"
        else:
            info["final_action"] = info.get("action", "monitor")
        
        return info
    
    def _get_reviewers(
        self,
        context: Any,
        quality: dict,
    ) -> list[str]:
        """Get recommended reviewers for escalation."""
        reviewers = []
        
        # Default reviewers based on quality issues
        if quality["overall_score"] < 0.4:
            reviewers.append("senior_analyst")
        else:
            reviewers.append("analyst")
        
        # Customer-specific reviewers
        if context:
            profile = getattr(context, "profile", None)
            if profile:
                account_manager = getattr(profile, "account_manager", None)
                if account_manager:
                    reviewers.append(account_manager)
        
        return reviewers
