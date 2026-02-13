"""
Cross-reference validation for OMEN signals.

Stage 4 of the 4-stage validation pipeline.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CrossReferenceResult:
    """Result of cross-reference validation."""
    valid: bool
    consistency_score: float  # 0-1
    corroborating_signals: List[str]
    conflicting_signals: List[str]
    errors: List[str]
    warnings: List[str]


class CrossReferenceValidator:
    """
    Validates signals against other recent signals.
    
    Ensures consistency and identifies corroboration/conflicts.
    """
    
    def __init__(self):
        # Recent signals cache (in production, would query DB)
        self._recent_signals: List[Dict[str, Any]] = []
        self._cache_duration = timedelta(hours=24)
    
    def add_signal(self, signal: Dict[str, Any]) -> None:
        """Add a signal to the recent cache."""
        signal["_cached_at"] = datetime.utcnow()
        self._recent_signals.append(signal)
        
        # Clean old signals
        self._clean_cache()
    
    def _clean_cache(self) -> None:
        """Remove old signals from cache."""
        cutoff = datetime.utcnow() - self._cache_duration
        self._recent_signals = [
            s for s in self._recent_signals
            if s.get("_cached_at", datetime.min) > cutoff
        ]
    
    def validate(
        self,
        signal: Dict[str, Any],
        min_corroboration: int = 0,
    ) -> CrossReferenceResult:
        """
        Validate a signal against recent signals.
        
        Args:
            signal: Signal to validate
            min_corroboration: Minimum corroborating signals required
            
        Returns:
            CrossReferenceResult
        """
        errors = []
        warnings = []
        corroborating = []
        conflicting = []
        
        # Get relevant fields from the signal
        chokepoint = signal.get("chokepoint")
        event_type = signal.get("event_type") or signal.get("signal_type")
        probability = signal.get("probability", 0.5)
        
        # Find related signals
        for other in self._recent_signals:
            if other.get("signal_id") == signal.get("signal_id"):
                continue
            
            # Check if same chokepoint
            if other.get("chokepoint") != chokepoint:
                continue
            
            other_prob = other.get("probability", 0.5)
            other_event = other.get("event_type") or other.get("signal_type")
            
            # Check for corroboration (same direction)
            if abs(probability - other_prob) < 0.2:
                corroborating.append(other.get("signal_id", "unknown"))
            
            # Check for conflict (opposite direction)
            elif abs(probability - other_prob) > 0.5:
                conflicting.append(other.get("signal_id", "unknown"))
                warnings.append(
                    f"Conflicts with signal {other.get('signal_id')}: "
                    f"prob {probability:.2f} vs {other_prob:.2f}"
                )
        
        # Check minimum corroboration
        if min_corroboration > 0 and len(corroborating) < min_corroboration:
            warnings.append(
                f"Insufficient corroboration: {len(corroborating)} < {min_corroboration}"
            )
        
        # Calculate consistency score
        total_related = len(corroborating) + len(conflicting)
        if total_related > 0:
            consistency_score = len(corroborating) / total_related
        else:
            consistency_score = 0.5  # Neutral if no related signals
        
        # Major conflicts reduce validity
        if len(conflicting) > len(corroborating):
            consistency_score *= 0.5
        
        valid = len(errors) == 0
        
        logger.debug(
            "cross_reference_validation_completed",
            signal_id=signal.get("signal_id"),
            valid=valid,
            corroborating=len(corroborating),
            conflicting=len(conflicting),
            consistency_score=consistency_score,
        )
        
        return CrossReferenceResult(
            valid=valid,
            consistency_score=consistency_score,
            corroborating_signals=corroborating,
            conflicting_signals=conflicting,
            errors=errors,
            warnings=warnings,
        )
