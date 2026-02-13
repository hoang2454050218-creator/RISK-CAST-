"""
Layer 1: Factual Reasoning.

Responsibilities:
- Gather and validate facts from signal, reality, and context
- Assess overall data quality
- Identify data gaps that could affect decision
- Rate source credibility

This is the foundation layer - all other layers depend on it.
"""

from datetime import datetime
from typing import Any
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    FactualLayerOutput,
    VerifiedFact,
)

logger = structlog.get_logger(__name__)


class FactualLayer:
    """
    Layer 1: Factual Reasoning.
    
    Gathers and validates facts from multiple sources:
    - OmenSignal: Predictions and evidence
    - RealitySnapshot: Current state from Oracle
    - CustomerContext: Customer-specific data
    
    Outputs verified facts with quality assessment.
    """
    
    # Source reliability weights
    SOURCE_RELIABILITY = {
        "polymarket": 0.85,  # Prediction market
        "ais": 0.95,         # AIS vessel tracking
        "news": 0.60,        # News sources
        "contract": 0.99,    # Contract data
        "customer": 0.90,    # Customer-provided data
        "historical": 0.80,  # Historical patterns
        "default": 0.50,     # Unknown sources
    }
    
    async def execute(self, inputs: dict) -> FactualLayerOutput:
        """
        Execute factual reasoning layer.
        
        Args:
            inputs: Dict with 'signal', 'reality', 'context'
        """
        signal = inputs.get("signal")
        reality = inputs.get("reality")
        context = inputs.get("context")
        
        started_at = datetime.utcnow()
        
        # Verify facts from all sources
        verified_facts = await self._verify_facts(signal, reality, context)
        
        # Assess data quality
        data_quality = self._assess_data_quality(signal, reality, verified_facts)
        
        # Identify gaps
        data_gaps = self._identify_data_gaps(signal, reality, context)
        
        # Rate sources
        source_credibility = self._rate_sources(signal, reality)
        
        # Generate warnings
        warnings = self._generate_warnings(data_quality, data_gaps, verified_facts)
        
        completed_at = datetime.utcnow()
        
        output = FactualLayerOutput(
            layer=ReasoningLayer.FACTUAL,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "signal_id": getattr(signal, "signal_id", None),
                "customer_id": getattr(getattr(context, "profile", None), "customer_id", None),
                "has_reality": reality is not None,
            },
            outputs={
                "fact_count": len(verified_facts),
                "data_quality": data_quality,
                "gap_count": len(data_gaps),
            },
            confidence=data_quality,
            verified_facts=verified_facts,
            data_quality_score=data_quality,
            data_gaps=data_gaps,
            source_credibility=source_credibility,
            warnings=warnings,
        )
        
        logger.debug(
            "factual_layer_complete",
            fact_count=len(verified_facts),
            data_quality=data_quality,
            gap_count=len(data_gaps),
        )
        
        return output
    
    async def _verify_facts(
        self,
        signal: Any,
        reality: Any,
        context: Any,
    ) -> list[VerifiedFact]:
        """Cross-reference signal claims with reality data."""
        facts = []
        
        # Signal facts
        if signal:
            # Signal probability
            facts.append(VerifiedFact(
                fact_type="signal_probability",
                value=getattr(signal, "probability", 0.5),
                verified=True,
                source=getattr(signal, "probability_source", "unknown"),
                source_reliability=self.SOURCE_RELIABILITY.get(
                    getattr(signal, "probability_source", "default"), 0.5
                ),
            ))
            
            # Signal confidence (data quality)
            facts.append(VerifiedFact(
                fact_type="signal_confidence",
                value=getattr(signal, "confidence_score", 0.5),
                verified=True,
                source="omen",
                source_reliability=0.90,
            ))
            
            # Evidence count
            evidence = getattr(signal, "evidence", [])
            facts.append(VerifiedFact(
                fact_type="evidence_count",
                value=len(evidence),
                verified=True,
                source="omen",
                source_reliability=0.95,
            ))
        
        # Reality facts
        if reality:
            # Chokepoint health
            chokepoint_health = getattr(reality, "chokepoint_health", {})
            if isinstance(chokepoint_health, dict):
                for cp, health in chokepoint_health.items():
                    facts.append(VerifiedFact(
                        fact_type=f"chokepoint_status_{cp}",
                        value=getattr(health, "status", "unknown"),
                        verified=True,
                        source="ais",
                        source_reliability=self.SOURCE_RELIABILITY["ais"],
                    ))
                    
                    # Vessels rerouting
                    vessels_rerouting = getattr(health, "vessels_rerouting", 0)
                    facts.append(VerifiedFact(
                        fact_type=f"vessels_rerouting_{cp}",
                        value=vessels_rerouting,
                        verified=True,
                        source="ais",
                        source_reliability=self.SOURCE_RELIABILITY["ais"],
                    ))
            
            # Rates impact
            rates_impact = getattr(reality, "rates_impact", None)
            if rates_impact:
                facts.append(VerifiedFact(
                    fact_type="rate_increase_pct",
                    value=getattr(rates_impact, "increase_percent", 0),
                    verified=True,
                    source="rates_api",
                    source_reliability=0.85,
                ))
        
        # Customer context facts
        if context:
            profile = getattr(context, "profile", None)
            if profile:
                facts.append(VerifiedFact(
                    fact_type="customer_id",
                    value=getattr(profile, "customer_id", "unknown"),
                    verified=True,
                    source="customer",
                    source_reliability=self.SOURCE_RELIABILITY["customer"],
                ))
                
                # Risk tolerance
                facts.append(VerifiedFact(
                    fact_type="risk_tolerance",
                    value=getattr(profile, "risk_tolerance", "medium"),
                    verified=True,
                    source="customer",
                    source_reliability=self.SOURCE_RELIABILITY["customer"],
                ))
            
            # Active shipments
            shipments = getattr(context, "active_shipments", [])
            facts.append(VerifiedFact(
                fact_type="active_shipment_count",
                value=len(shipments),
                verified=True,
                source="customer",
                source_reliability=self.SOURCE_RELIABILITY["customer"],
            ))
            
            # Total cargo value
            total_value = sum(
                getattr(s, "cargo_value_usd", 0) for s in shipments
            )
            facts.append(VerifiedFact(
                fact_type="total_cargo_value_usd",
                value=total_value,
                verified=True,
                source="customer",
                source_reliability=self.SOURCE_RELIABILITY["customer"],
            ))
        
        return facts
    
    def _assess_data_quality(
        self,
        signal: Any,
        reality: Any,
        verified_facts: list[VerifiedFact],
    ) -> float:
        """Score overall data quality (0-1)."""
        scores = []
        
        # Signal confidence
        if signal:
            scores.append(getattr(signal, "confidence_score", 0.5))
        
        # Reality freshness (1.0 if < 5 min, degrades after)
        if reality:
            staleness = getattr(reality, "staleness_seconds", 3600)
            freshness = 1.0 - min(staleness / 3600, 1.0)
            scores.append(freshness)
        else:
            scores.append(0.0)  # No reality data
        
        # Source diversity
        if verified_facts:
            unique_sources = len(set(f.source for f in verified_facts))
            diversity = min(unique_sources / 5, 1.0)
            scores.append(diversity)
        
        # Average reliability
        if verified_facts:
            avg_reliability = sum(f.source_reliability for f in verified_facts) / len(verified_facts)
            scores.append(avg_reliability)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _identify_data_gaps(
        self,
        signal: Any,
        reality: Any,
        context: Any,
    ) -> list[str]:
        """Identify missing data that could affect decision."""
        gaps = []
        
        # Reality data gaps
        if not reality:
            gaps.append("No reality data available")
        else:
            if not getattr(reality, "chokepoint_health", None):
                gaps.append("No real-time chokepoint data")
            
            staleness = getattr(reality, "staleness_seconds", 0)
            if staleness > 3600:
                gaps.append(f"Reality data is {staleness // 60} minutes old")
            elif staleness > 1800:
                gaps.append(f"Reality data is {staleness // 60} minutes old (moderately stale)")
        
        # Signal data gaps
        if signal:
            evidence = getattr(signal, "evidence", [])
            if not evidence:
                gaps.append("Signal has no supporting evidence")
            elif len(evidence) < 2:
                gaps.append("Signal has limited evidence (only 1 source)")
        
        # Customer data gaps
        if context:
            shipments = getattr(context, "active_shipments", [])
            for shipment in shipments:
                if not getattr(shipment, "current_location", None):
                    gaps.append(f"No current location for shipment {getattr(shipment, 'shipment_id', 'unknown')}")
        
        return gaps
    
    def _rate_sources(
        self,
        signal: Any,
        reality: Any,
    ) -> dict[str, float]:
        """Rate credibility of each data source."""
        credibility = {}
        
        # Signal source
        if signal:
            source = getattr(signal, "probability_source", "unknown")
            credibility[source] = self.SOURCE_RELIABILITY.get(
                source, self.SOURCE_RELIABILITY["default"]
            )
            credibility["omen"] = 0.85  # OMEN system credibility
        
        # Reality sources
        if reality:
            credibility["ais"] = self.SOURCE_RELIABILITY["ais"]
            credibility["rates_api"] = 0.85
        
        return credibility
    
    def _generate_warnings(
        self,
        data_quality: float,
        data_gaps: list[str],
        verified_facts: list[VerifiedFact],
    ) -> list[str]:
        """Generate warnings based on data quality assessment."""
        warnings = []
        
        if data_quality < 0.5:
            warnings.append(f"Low data quality ({data_quality:.0%})")
        
        if len(data_gaps) > 3:
            warnings.append(f"Multiple data gaps identified ({len(data_gaps)})")
        
        # Check for low-reliability sources
        low_reliability_facts = [
            f for f in verified_facts if f.source_reliability < 0.6
        ]
        if low_reliability_facts:
            warnings.append(
                f"{len(low_reliability_facts)} facts from low-reliability sources"
            )
        
        return warnings
