"""
Validation pipeline for OMEN signals.

Orchestrates the 4-stage validation process.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
import structlog

from app.omen.validators.schema import SchemaValidator, SchemaValidationResult
from app.omen.validators.source import SourceValidator, SourceValidationResult
from app.omen.validators.content import ContentValidator, ContentValidationResult
from app.omen.validators.cross_reference import CrossReferenceValidator, CrossReferenceResult

logger = structlog.get_logger(__name__)


@dataclass
class ValidationStageResult:
    """Result from a single validation stage."""
    stage: str
    passed: bool
    score: float
    errors: List[str]
    warnings: List[str]
    duration_ms: float


@dataclass
class PipelineResult:
    """Complete pipeline validation result."""
    signal_id: str
    valid: bool
    overall_score: float
    stages: List[ValidationStageResult]
    all_errors: List[str]
    all_warnings: List[str]
    validated_data: Optional[Dict[str, Any]] = None
    
    @property
    def stage_summary(self) -> Dict[str, bool]:
        return {stage.stage: stage.passed for stage in self.stages}


class ValidationPipeline:
    """
    4-Stage validation pipeline for OMEN signals.
    
    Stages:
    1. Schema - Structural correctness
    2. Source - Credibility and freshness
    3. Content - Semantic validity
    4. Cross-Reference - Consistency with other signals
    """
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.source_validator = SourceValidator()
        self.content_validator = ContentValidator()
        self.cross_reference_validator = CrossReferenceValidator()
        
        # Stage weights for overall score
        self._stage_weights = {
            "schema": 0.25,
            "source": 0.25,
            "content": 0.30,
            "cross_reference": 0.20,
        }
        
        # Minimum scores to pass
        self._min_scores = {
            "schema": 1.0,  # Must fully pass
            "source": 0.3,
            "content": 0.5,
            "cross_reference": 0.3,
        }
    
    def register_schema(self, signal_type: str, schema: Type[BaseModel]) -> None:
        """Register a schema for validation."""
        self.schema_validator.register_schema(signal_type, schema)
    
    async def validate(
        self,
        signal: Dict[str, Any],
        strict: bool = False,
    ) -> PipelineResult:
        """
        Run full validation pipeline on a signal.
        
        Args:
            signal: Signal data to validate
            strict: If True, fail on warnings too
            
        Returns:
            PipelineResult with all stage results
        """
        import time
        
        signal_id = signal.get("signal_id", "unknown")
        stages: List[ValidationStageResult] = []
        all_errors: List[str] = []
        all_warnings: List[str] = []
        validated_data = signal.copy()
        
        logger.info("validation_pipeline_started", signal_id=signal_id)
        
        # Stage 1: Schema Validation
        start = time.time()
        signal_type = signal.get("signal_type", "generic")
        schema_result = self.schema_validator.validate(signal_type, signal)
        duration = (time.time() - start) * 1000
        
        stages.append(ValidationStageResult(
            stage="schema",
            passed=schema_result.valid,
            score=1.0 if schema_result.valid else 0.0,
            errors=schema_result.errors,
            warnings=schema_result.warnings,
            duration_ms=duration,
        ))
        all_errors.extend(schema_result.errors)
        all_warnings.extend(schema_result.warnings)
        
        if schema_result.validated_data:
            validated_data = schema_result.validated_data
        
        # Stage 2: Source Validation
        start = time.time()
        source = signal.get("source", "unknown")
        timestamp_str = signal.get("timestamp", datetime.utcnow().isoformat())
        if isinstance(timestamp_str, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = timestamp_str
        
        source_result = self.source_validator.validate(source, timestamp)
        duration = (time.time() - start) * 1000
        
        source_score = source_result.credibility.credibility_score if source_result.credibility else 0.0
        stages.append(ValidationStageResult(
            stage="source",
            passed=source_result.valid,
            score=source_score,
            errors=source_result.errors,
            warnings=source_result.warnings,
            duration_ms=duration,
        ))
        all_errors.extend(source_result.errors)
        all_warnings.extend(source_result.warnings)
        
        # Stage 3: Content Validation
        start = time.time()
        content_result = self.content_validator.validate(signal)
        duration = (time.time() - start) * 1000
        
        stages.append(ValidationStageResult(
            stage="content",
            passed=content_result.valid,
            score=content_result.semantic_score,
            errors=content_result.errors,
            warnings=content_result.warnings,
            duration_ms=duration,
        ))
        all_errors.extend(content_result.errors)
        all_warnings.extend(content_result.warnings)
        
        # Stage 4: Cross-Reference Validation
        start = time.time()
        xref_result = self.cross_reference_validator.validate(signal)
        duration = (time.time() - start) * 1000
        
        stages.append(ValidationStageResult(
            stage="cross_reference",
            passed=xref_result.valid,
            score=xref_result.consistency_score,
            errors=xref_result.errors,
            warnings=xref_result.warnings,
            duration_ms=duration,
        ))
        all_errors.extend(xref_result.errors)
        all_warnings.extend(xref_result.warnings)
        
        # Add to cross-reference cache
        self.cross_reference_validator.add_signal(signal)
        
        # Calculate overall score
        overall_score = sum(
            stage.score * self._stage_weights.get(stage.stage, 0.25)
            for stage in stages
        )
        
        # Determine validity
        valid = len(all_errors) == 0
        if strict and all_warnings:
            valid = False
        
        # Check minimum scores
        for stage in stages:
            min_score = self._min_scores.get(stage.stage, 0.0)
            if stage.score < min_score:
                valid = False
        
        logger.info(
            "validation_pipeline_completed",
            signal_id=signal_id,
            valid=valid,
            overall_score=overall_score,
            errors=len(all_errors),
            warnings=len(all_warnings),
        )
        
        return PipelineResult(
            signal_id=signal_id,
            valid=valid,
            overall_score=overall_score,
            stages=stages,
            all_errors=all_errors,
            all_warnings=all_warnings,
            validated_data=validated_data if valid else None,
        )
