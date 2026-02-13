"""
Content validation for OMEN signals.

Stage 3 of the 4-stage validation pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import re
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ContentValidationResult:
    """Result of content validation."""
    valid: bool
    semantic_score: float  # 0-1
    errors: List[str]
    warnings: List[str]
    extracted_entities: Dict[str, Any]


class ContentValidator:
    """
    Validates signal content for semantic validity.
    
    Ensures signal content makes sense and contains valid information.
    """
    
    def __init__(self):
        # Valid chokepoints
        self._valid_chokepoints = {
            "red_sea", "suez", "panama", "malacca", "hormuz",
            "gibraltar", "english_channel", "cape_of_good_hope"
        }
        
        # Valid event types
        self._valid_event_types = {
            "disruption", "attack", "weather", "closure",
            "congestion", "strike", "accident"
        }
        
        # Probability range
        self._probability_range = (0.0, 1.0)
        
        # Confidence range
        self._confidence_range = (0.0, 1.0)
    
    def validate(
        self,
        content: Dict[str, Any],
    ) -> ContentValidationResult:
        """
        Validate signal content.
        
        Args:
            content: Signal content to validate
            
        Returns:
            ContentValidationResult
        """
        errors = []
        warnings = []
        extracted = {}
        
        # Validate probability if present
        if "probability" in content:
            prob = content["probability"]
            if not isinstance(prob, (int, float)):
                errors.append("Probability must be numeric")
            elif not (self._probability_range[0] <= prob <= self._probability_range[1]):
                errors.append(f"Probability {prob} out of range [0, 1]")
            else:
                extracted["probability"] = prob
        
        # Validate confidence if present
        if "confidence" in content:
            conf = content["confidence"]
            if not isinstance(conf, (int, float)):
                errors.append("Confidence must be numeric")
            elif not (self._confidence_range[0] <= conf <= self._confidence_range[1]):
                errors.append(f"Confidence {conf} out of range [0, 1]")
            else:
                extracted["confidence"] = conf
        
        # Validate chokepoint if present
        if "chokepoint" in content:
            cp = content["chokepoint"]
            if cp not in self._valid_chokepoints:
                warnings.append(f"Unknown chokepoint: {cp}")
            extracted["chokepoint"] = cp
        
        # Validate event type if present
        if "event_type" in content or "signal_type" in content:
            event = content.get("event_type") or content.get("signal_type")
            if event and event not in self._valid_event_types:
                warnings.append(f"Unknown event type: {event}")
            extracted["event_type"] = event
        
        # Validate dates
        for date_field in ["timestamp", "event_date", "expires_at"]:
            if date_field in content:
                date_val = content[date_field]
                if isinstance(date_val, str):
                    try:
                        parsed = datetime.fromisoformat(date_val.replace("Z", "+00:00"))
                        extracted[date_field] = parsed
                    except ValueError:
                        errors.append(f"Invalid date format for {date_field}: {date_val}")
                elif isinstance(date_val, datetime):
                    extracted[date_field] = date_val
        
        # Calculate semantic score
        total_fields = len(content)
        valid_fields = len(extracted)
        semantic_score = valid_fields / total_fields if total_fields > 0 else 0.0
        
        # Penalize for errors
        if errors:
            semantic_score *= 0.5
        
        valid = len(errors) == 0
        
        logger.debug(
            "content_validation_completed",
            valid=valid,
            semantic_score=semantic_score,
            errors=len(errors),
        )
        
        return ContentValidationResult(
            valid=valid,
            semantic_score=semantic_score,
            errors=errors,
            warnings=warnings,
            extracted_entities=extracted,
        )
    
    def validate_text_content(
        self,
        text: str,
        min_length: int = 10,
        max_length: int = 10000,
    ) -> ContentValidationResult:
        """Validate free-text content."""
        errors = []
        warnings = []
        
        if len(text) < min_length:
            errors.append(f"Text too short: {len(text)} < {min_length}")
        
        if len(text) > max_length:
            errors.append(f"Text too long: {len(text)} > {max_length}")
        
        # Check for suspicious patterns
        if re.search(r"<script|javascript:|data:", text, re.IGNORECASE):
            errors.append("Suspicious content detected")
        
        return ContentValidationResult(
            valid=len(errors) == 0,
            semantic_score=1.0 if not errors else 0.0,
            errors=errors,
            warnings=warnings,
            extracted_entities={},
        )
