"""
Source validation for OMEN signals.

Stage 2 of the 4-stage validation pipeline.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SourceCredibility:
    """Credibility assessment for a source."""
    source_id: str
    credibility_score: float  # 0-1
    historical_accuracy: float  # 0-1
    recency_score: float  # 0-1
    is_trusted: bool


@dataclass
class SourceValidationResult:
    """Result of source validation."""
    valid: bool
    credibility: Optional[SourceCredibility]
    errors: List[str]
    warnings: List[str]


class SourceValidator:
    """
    Validates signal sources for credibility and freshness.
    
    Ensures signals come from trustworthy sources with recent data.
    """
    
    def __init__(self):
        # Source credibility scores (would be loaded from DB in production)
        self._source_scores: Dict[str, float] = {
            "polymarket": 0.85,
            "reuters": 0.95,
            "bloomberg": 0.92,
            "ais_data": 0.90,
            "user_report": 0.60,
            "social_media": 0.40,
        }
        
        # Maximum age for fresh data (by source type)
        self._max_age_hours: Dict[str, int] = {
            "polymarket": 1,
            "reuters": 4,
            "bloomberg": 4,
            "ais_data": 1,
            "user_report": 24,
            "social_media": 1,
        }
        
        # Trusted sources
        self._trusted_sources = {"polymarket", "reuters", "bloomberg", "ais_data"}
    
    def validate(
        self,
        source: str,
        data_timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SourceValidationResult:
        """
        Validate a signal source.
        
        Args:
            source: Source identifier
            data_timestamp: When the data was generated
            metadata: Additional source metadata
            
        Returns:
            SourceValidationResult
        """
        errors = []
        warnings = []
        
        # Get credibility score
        base_credibility = self._source_scores.get(source, 0.5)
        
        # Check freshness
        max_age = self._max_age_hours.get(source, 6)
        age = datetime.utcnow() - data_timestamp
        age_hours = age.total_seconds() / 3600
        
        if age_hours > max_age:
            recency_score = max(0, 1 - (age_hours - max_age) / max_age)
            warnings.append(f"Data is {age_hours:.1f} hours old (max: {max_age}h)")
        else:
            recency_score = 1.0
        
        # Check if source is trusted
        is_trusted = source in self._trusted_sources
        
        # Calculate historical accuracy (would come from tracking in production)
        historical_accuracy = base_credibility  # Simplified
        
        # Build credibility assessment
        credibility = SourceCredibility(
            source_id=source,
            credibility_score=base_credibility * recency_score,
            historical_accuracy=historical_accuracy,
            recency_score=recency_score,
            is_trusted=is_trusted,
        )
        
        # Validation rules
        if credibility.credibility_score < 0.3:
            errors.append(f"Source credibility too low: {credibility.credibility_score:.2f}")
        
        if not is_trusted:
            warnings.append(f"Source '{source}' is not in trusted sources list")
        
        valid = len(errors) == 0
        
        logger.debug(
            "source_validation_completed",
            source=source,
            valid=valid,
            credibility=credibility.credibility_score,
        )
        
        return SourceValidationResult(
            valid=valid,
            credibility=credibility,
            errors=errors,
            warnings=warnings,
        )
    
    def add_source(
        self,
        source_id: str,
        credibility_score: float,
        max_age_hours: int = 6,
        trusted: bool = False,
    ) -> None:
        """Add or update a source configuration."""
        self._source_scores[source_id] = credibility_score
        self._max_age_hours[source_id] = max_age_hours
        if trusted:
            self._trusted_sources.add(source_id)
