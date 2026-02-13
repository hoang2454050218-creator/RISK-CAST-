"""
Error taxonomy for prediction error classification and analysis.

This module implements GAP A3.2: Error taxonomy incomplete.
Provides formal classification of prediction errors for learning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import structlog

logger = structlog.get_logger(__name__)


class ErrorCategory(str, Enum):
    """Primary error categories."""
    # Signal errors
    SIGNAL_MISS = "signal_miss"           # Failed to detect signal
    SIGNAL_FALSE_POSITIVE = "signal_fp"   # Detected non-existent signal
    SIGNAL_MISCLASSIFY = "signal_misclass" # Detected but wrong type
    
    # Probability errors
    OVERCONFIDENT = "overconfident"       # Predicted higher prob than actual
    UNDERCONFIDENT = "underconfident"     # Predicted lower prob than actual
    CALIBRATION = "calibration"           # Systematic probability bias
    
    # Timing errors
    TIMING_EARLY = "timing_early"         # Predicted too early
    TIMING_LATE = "timing_late"           # Predicted too late
    TIMING_DURATION = "timing_duration"   # Wrong event duration
    
    # Impact errors
    IMPACT_OVERESTIMATE = "impact_over"   # Overestimated severity
    IMPACT_UNDERESTIMATE = "impact_under" # Underestimated severity
    IMPACT_SCOPE = "impact_scope"         # Wrong affected areas
    
    # Action errors
    ACTION_WRONG = "action_wrong"         # Recommended wrong action
    ACTION_TIMING = "action_timing"       # Right action, wrong time
    ACTION_INCOMPLETE = "action_incomplete" # Missing action components
    
    # Data errors
    DATA_STALE = "data_stale"            # Used outdated data
    DATA_MISSING = "data_missing"         # Missing critical data
    DATA_CORRUPT = "data_corrupt"         # Corrupted input data
    
    # Model errors
    MODEL_DRIFT = "model_drift"           # Model assumptions no longer valid
    MODEL_EDGE_CASE = "model_edge"        # Edge case not handled
    MODEL_EXTRAPOLATION = "model_extrap"  # Extrapolated beyond training


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"    # Caused significant harm
    MAJOR = "major"          # Caused moderate harm
    MINOR = "minor"          # Caused minor harm
    NEGLIGIBLE = "negligible" # No significant harm


class RootCause(str, Enum):
    """Root cause categories."""
    # Data issues
    DATA_QUALITY = "data_quality"
    DATA_COVERAGE = "data_coverage"
    DATA_TIMELINESS = "data_timeliness"
    
    # Model issues
    MODEL_ARCHITECTURE = "model_architecture"
    MODEL_TRAINING = "model_training"
    MODEL_VALIDATION = "model_validation"
    
    # Process issues
    PROCESS_LATENCY = "process_latency"
    PROCESS_THRESHOLD = "process_threshold"
    PROCESS_LOGIC = "process_logic"
    
    # External issues
    EXTERNAL_UNPRECEDENTED = "external_unprecedented"
    EXTERNAL_RAPID_CHANGE = "external_rapid"
    EXTERNAL_BLACK_SWAN = "external_black_swan"
    
    # Human factors
    HUMAN_OVERRIDE = "human_override"
    HUMAN_DELAY = "human_delay"
    HUMAN_MISCONFIG = "human_misconfig"


@dataclass
class ErrorInstance:
    """A single error instance."""
    error_id: str
    occurred_at: datetime
    detected_at: datetime
    
    # Classification
    category: ErrorCategory
    severity: ErrorSeverity
    root_causes: List[RootCause]
    
    # Context
    decision_id: Optional[str] = None
    signal_id: Optional[str] = None
    prediction_id: Optional[str] = None
    
    # Error details
    predicted_value: Any = None
    actual_value: Any = None
    deviation: float = 0.0
    deviation_pct: float = 0.0
    
    # Impact
    cost_impact_usd: float = 0.0
    delay_impact_days: float = 0.0
    affected_shipments: int = 0
    
    # Analysis
    description: str = ""
    contributing_factors: List[str] = field(default_factory=list)
    mitigation_applied: Optional[str] = None
    lessons_learned: List[str] = field(default_factory=list)
    
    # Status
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


@dataclass
class ErrorPattern:
    """Pattern detected across multiple errors."""
    pattern_id: str
    description: str
    categories: Set[ErrorCategory]
    root_causes: Set[RootCause]
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    total_cost_impact_usd: float
    recommended_fix: str
    fix_priority: ErrorSeverity


@dataclass
class TaxonomyReport:
    """Error taxonomy analysis report."""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # Summary statistics
    total_errors: int
    errors_by_category: Dict[str, int]
    errors_by_severity: Dict[str, int]
    errors_by_root_cause: Dict[str, int]
    
    # Impact
    total_cost_impact_usd: float
    total_delay_impact_days: float
    total_affected_shipments: int
    
    # Trends
    category_trends: Dict[str, List[Tuple[datetime, int]]]
    
    # Patterns
    patterns: List[ErrorPattern]
    
    # Recommendations
    top_recommendations: List[str]


class ErrorTaxonomyEngine:
    """
    Classifies, analyzes, and learns from prediction errors.
    
    Provides systematic error analysis for continuous improvement.
    """
    
    def __init__(self):
        self._errors: List[ErrorInstance] = []
        self._patterns: Dict[str, ErrorPattern] = {}
        
        # Classification rules
        self._severity_thresholds = {
            "cost_critical": 100_000,
            "cost_major": 25_000,
            "cost_minor": 5_000,
            "delay_critical": 14,
            "delay_major": 7,
            "delay_minor": 2,
        }
        
        # Category detection rules
        self._deviation_thresholds = {
            "overconfident": 0.15,  # Predicted 15%+ higher
            "underconfident": 0.15, # Predicted 15%+ lower
            "timing_early": 24,     # Hours early
            "timing_late": 24,      # Hours late
        }
    
    def classify_error(
        self,
        predicted: Any,
        actual: Any,
        context: Dict[str, Any],
    ) -> ErrorInstance:
        """
        Classify a prediction error.
        
        Args:
            predicted: What was predicted
            actual: What actually happened
            context: Additional context (decision_id, signal_id, etc.)
            
        Returns:
            Classified ErrorInstance
        """
        import uuid
        
        now = datetime.utcnow()
        
        # Determine category
        category = self._determine_category(predicted, actual, context)
        
        # Calculate deviation
        deviation, deviation_pct = self._calculate_deviation(predicted, actual)
        
        # Determine root causes
        root_causes = self._identify_root_causes(category, context)
        
        # Determine severity
        severity = self._determine_severity(
            deviation_pct,
            context.get("cost_impact_usd", 0),
            context.get("delay_impact_days", 0),
        )
        
        error = ErrorInstance(
            error_id=f"err_{uuid.uuid4().hex[:16]}",
            occurred_at=context.get("occurred_at", now),
            detected_at=now,
            category=category,
            severity=severity,
            root_causes=root_causes,
            decision_id=context.get("decision_id"),
            signal_id=context.get("signal_id"),
            prediction_id=context.get("prediction_id"),
            predicted_value=predicted,
            actual_value=actual,
            deviation=deviation,
            deviation_pct=deviation_pct,
            cost_impact_usd=context.get("cost_impact_usd", 0),
            delay_impact_days=context.get("delay_impact_days", 0),
            affected_shipments=context.get("affected_shipments", 0),
            description=self._generate_description(category, predicted, actual),
            contributing_factors=context.get("contributing_factors", []),
        )
        
        self._errors.append(error)
        self._update_patterns(error)
        
        logger.info(
            "error_classified",
            error_id=error.error_id,
            category=error.category.value,
            severity=error.severity.value,
            deviation_pct=error.deviation_pct,
        )
        
        return error
    
    def _determine_category(
        self,
        predicted: Any,
        actual: Any,
        context: Dict[str, Any],
    ) -> ErrorCategory:
        """Determine error category based on prediction type."""
        
        error_type = context.get("error_type", "probability")
        
        if error_type == "signal":
            if actual is None and predicted is not None:
                return ErrorCategory.SIGNAL_FALSE_POSITIVE
            elif actual is not None and predicted is None:
                return ErrorCategory.SIGNAL_MISS
            else:
                return ErrorCategory.SIGNAL_MISCLASSIFY
        
        elif error_type == "probability":
            if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                if predicted > actual:
                    return ErrorCategory.OVERCONFIDENT
                else:
                    return ErrorCategory.UNDERCONFIDENT
            return ErrorCategory.CALIBRATION
        
        elif error_type == "timing":
            pred_time = context.get("predicted_time")
            actual_time = context.get("actual_time")
            if pred_time and actual_time:
                if pred_time < actual_time:
                    return ErrorCategory.TIMING_EARLY
                else:
                    return ErrorCategory.TIMING_LATE
            return ErrorCategory.TIMING_DURATION
        
        elif error_type == "impact":
            if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                if predicted > actual:
                    return ErrorCategory.IMPACT_OVERESTIMATE
                else:
                    return ErrorCategory.IMPACT_UNDERESTIMATE
            return ErrorCategory.IMPACT_SCOPE
        
        elif error_type == "action":
            return ErrorCategory.ACTION_WRONG
        
        elif error_type == "data":
            data_issue = context.get("data_issue", "missing")
            if data_issue == "stale":
                return ErrorCategory.DATA_STALE
            elif data_issue == "corrupt":
                return ErrorCategory.DATA_CORRUPT
            return ErrorCategory.DATA_MISSING
        
        else:
            # Default to model error
            if context.get("is_edge_case"):
                return ErrorCategory.MODEL_EDGE_CASE
            elif context.get("is_extrapolation"):
                return ErrorCategory.MODEL_EXTRAPOLATION
            return ErrorCategory.MODEL_DRIFT
    
    def _calculate_deviation(
        self,
        predicted: Any,
        actual: Any,
    ) -> Tuple[float, float]:
        """Calculate deviation between predicted and actual."""
        
        if predicted is None or actual is None:
            return 0.0, 100.0
        
        try:
            if isinstance(predicted, (int, float)) and isinstance(actual, (int, float)):
                deviation = abs(float(predicted) - float(actual))
                if actual != 0:
                    deviation_pct = (deviation / abs(actual)) * 100
                elif predicted != 0:
                    deviation_pct = 100.0
                else:
                    deviation_pct = 0.0
                return deviation, deviation_pct
        except (TypeError, ValueError):
            pass
        
        return 0.0, 0.0
    
    def _identify_root_causes(
        self,
        category: ErrorCategory,
        context: Dict[str, Any],
    ) -> List[RootCause]:
        """Identify likely root causes for an error."""
        
        causes = []
        
        # Data-related categories
        if category in [
            ErrorCategory.DATA_STALE,
            ErrorCategory.DATA_MISSING,
            ErrorCategory.DATA_CORRUPT,
        ]:
            causes.append(RootCause.DATA_QUALITY)
            if context.get("data_age_hours", 0) > 24:
                causes.append(RootCause.DATA_TIMELINESS)
        
        # Model-related categories
        if category in [
            ErrorCategory.MODEL_DRIFT,
            ErrorCategory.MODEL_EDGE_CASE,
            ErrorCategory.MODEL_EXTRAPOLATION,
        ]:
            causes.append(RootCause.MODEL_VALIDATION)
            if context.get("is_unprecedented"):
                causes.append(RootCause.EXTERNAL_UNPRECEDENTED)
        
        # Timing-related categories
        if category in [
            ErrorCategory.TIMING_EARLY,
            ErrorCategory.TIMING_LATE,
            ErrorCategory.TIMING_DURATION,
        ]:
            causes.append(RootCause.PROCESS_LATENCY)
            if context.get("rapid_change"):
                causes.append(RootCause.EXTERNAL_RAPID_CHANGE)
        
        # Probability-related categories
        if category in [
            ErrorCategory.OVERCONFIDENT,
            ErrorCategory.UNDERCONFIDENT,
            ErrorCategory.CALIBRATION,
        ]:
            causes.append(RootCause.MODEL_TRAINING)
            if context.get("low_sample_count"):
                causes.append(RootCause.DATA_COVERAGE)
        
        # Human factors
        if context.get("human_override"):
            causes.append(RootCause.HUMAN_OVERRIDE)
        if context.get("config_error"):
            causes.append(RootCause.HUMAN_MISCONFIG)
        
        return causes or [RootCause.PROCESS_LOGIC]
    
    def _determine_severity(
        self,
        deviation_pct: float,
        cost_impact_usd: float,
        delay_impact_days: float,
    ) -> ErrorSeverity:
        """Determine error severity based on impact."""
        
        # Check cost impact
        if cost_impact_usd >= self._severity_thresholds["cost_critical"]:
            return ErrorSeverity.CRITICAL
        if cost_impact_usd >= self._severity_thresholds["cost_major"]:
            return ErrorSeverity.MAJOR
        
        # Check delay impact
        if delay_impact_days >= self._severity_thresholds["delay_critical"]:
            return ErrorSeverity.CRITICAL
        if delay_impact_days >= self._severity_thresholds["delay_major"]:
            return ErrorSeverity.MAJOR
        
        # Check deviation
        if deviation_pct >= 50:
            return ErrorSeverity.MAJOR
        if deviation_pct >= 25:
            return ErrorSeverity.MINOR
        
        # Minimum based on cost
        if cost_impact_usd >= self._severity_thresholds["cost_minor"]:
            return ErrorSeverity.MINOR
        
        return ErrorSeverity.NEGLIGIBLE
    
    def _generate_description(
        self,
        category: ErrorCategory,
        predicted: Any,
        actual: Any,
    ) -> str:
        """Generate human-readable error description."""
        
        descriptions = {
            ErrorCategory.SIGNAL_MISS: f"Failed to detect signal. Actual: {actual}",
            ErrorCategory.SIGNAL_FALSE_POSITIVE: f"False positive signal: {predicted}",
            ErrorCategory.SIGNAL_MISCLASSIFY: f"Misclassified signal: predicted {predicted}, actual {actual}",
            ErrorCategory.OVERCONFIDENT: f"Overconfident prediction: {predicted} vs actual {actual}",
            ErrorCategory.UNDERCONFIDENT: f"Underconfident prediction: {predicted} vs actual {actual}",
            ErrorCategory.CALIBRATION: f"Calibration error: {predicted} vs {actual}",
            ErrorCategory.TIMING_EARLY: f"Predicted too early: {predicted} vs {actual}",
            ErrorCategory.TIMING_LATE: f"Predicted too late: {predicted} vs {actual}",
            ErrorCategory.TIMING_DURATION: f"Duration error: {predicted} vs {actual}",
            ErrorCategory.IMPACT_OVERESTIMATE: f"Overestimated impact: {predicted} vs {actual}",
            ErrorCategory.IMPACT_UNDERESTIMATE: f"Underestimated impact: {predicted} vs {actual}",
            ErrorCategory.IMPACT_SCOPE: f"Wrong impact scope: {predicted} vs {actual}",
            ErrorCategory.ACTION_WRONG: f"Wrong action recommended: {predicted}",
            ErrorCategory.ACTION_TIMING: f"Wrong action timing: {predicted}",
            ErrorCategory.ACTION_INCOMPLETE: f"Incomplete action: {predicted}",
            ErrorCategory.DATA_STALE: "Used stale data for prediction",
            ErrorCategory.DATA_MISSING: "Missing critical data for prediction",
            ErrorCategory.DATA_CORRUPT: "Corrupted input data affected prediction",
            ErrorCategory.MODEL_DRIFT: "Model drift detected - assumptions no longer valid",
            ErrorCategory.MODEL_EDGE_CASE: "Edge case not handled by model",
            ErrorCategory.MODEL_EXTRAPOLATION: "Model extrapolated beyond training range",
        }
        
        return descriptions.get(category, f"Error: {predicted} vs {actual}")
    
    def _update_patterns(self, error: ErrorInstance) -> None:
        """Update pattern detection with new error."""
        
        # Create pattern key from category + root causes
        cause_key = "_".join(sorted(rc.value for rc in error.root_causes))
        pattern_key = f"{error.category.value}:{cause_key}"
        
        if pattern_key in self._patterns:
            pattern = self._patterns[pattern_key]
            pattern.occurrence_count += 1
            pattern.last_seen = error.detected_at
            pattern.total_cost_impact_usd += error.cost_impact_usd
        else:
            self._patterns[pattern_key] = ErrorPattern(
                pattern_id=f"pat_{pattern_key[:20]}",
                description=f"Recurring {error.category.value} errors",
                categories={error.category},
                root_causes=set(error.root_causes),
                occurrence_count=1,
                first_seen=error.detected_at,
                last_seen=error.detected_at,
                total_cost_impact_usd=error.cost_impact_usd,
                recommended_fix=self._generate_fix_recommendation(
                    error.category,
                    error.root_causes,
                ),
                fix_priority=error.severity,
            )
    
    def _generate_fix_recommendation(
        self,
        category: ErrorCategory,
        root_causes: List[RootCause],
    ) -> str:
        """Generate fix recommendation based on error analysis."""
        
        recommendations = {
            ErrorCategory.OVERCONFIDENT: "Recalibrate probability model with recent data",
            ErrorCategory.UNDERCONFIDENT: "Review threshold settings and confidence intervals",
            ErrorCategory.SIGNAL_MISS: "Add new signal sources or lower detection thresholds",
            ErrorCategory.TIMING_LATE: "Reduce processing latency or adjust lead times",
            ErrorCategory.MODEL_DRIFT: "Retrain model with recent data or add drift detection",
            ErrorCategory.DATA_STALE: "Increase data refresh frequency",
            ErrorCategory.DATA_MISSING: "Add fallback data sources",
        }
        
        base_rec = recommendations.get(
            category,
            "Review and analyze error pattern for specific fixes"
        )
        
        # Add root cause specific advice
        if RootCause.EXTERNAL_BLACK_SWAN in root_causes:
            base_rec += ". Consider adding black swan detection."
        if RootCause.HUMAN_OVERRIDE in root_causes:
            base_rec += ". Review override policies."
        
        return base_rec
    
    def generate_report(
        self,
        period_days: int = 30,
    ) -> TaxonomyReport:
        """Generate error taxonomy report."""
        import uuid
        from collections import defaultdict
        
        now = datetime.utcnow()
        period_start = now - timedelta(days=period_days)
        
        # Filter errors in period
        period_errors = [
            e for e in self._errors
            if e.occurred_at >= period_start
        ]
        
        # Aggregate statistics
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        by_root_cause = defaultdict(int)
        
        total_cost = 0.0
        total_delay = 0.0
        total_shipments = 0
        
        for error in period_errors:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1
            for cause in error.root_causes:
                by_root_cause[cause.value] += 1
            total_cost += error.cost_impact_usd
            total_delay += error.delay_impact_days
            total_shipments += error.affected_shipments
        
        # Get top patterns
        patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.total_cost_impact_usd,
            reverse=True,
        )[:10]
        
        # Generate recommendations
        recommendations = []
        if patterns:
            for pattern in patterns[:3]:
                recommendations.append(pattern.recommended_fix)
        
        if by_category:
            top_category = max(by_category.items(), key=lambda x: x[1])
            recommendations.append(
                f"Focus on reducing {top_category[0]} errors "
                f"({top_category[1]} occurrences)"
            )
        
        return TaxonomyReport(
            report_id=f"tax_{uuid.uuid4().hex[:12]}",
            generated_at=now,
            period_start=period_start,
            period_end=now,
            total_errors=len(period_errors),
            errors_by_category=dict(by_category),
            errors_by_severity=dict(by_severity),
            errors_by_root_cause=dict(by_root_cause),
            total_cost_impact_usd=total_cost,
            total_delay_impact_days=total_delay,
            total_affected_shipments=total_shipments,
            category_trends={},  # Would need time series data
            patterns=patterns,
            top_recommendations=recommendations,
        )
    
    def get_errors(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        limit: int = 100,
    ) -> List[ErrorInstance]:
        """Get errors with optional filters."""
        
        filtered = self._errors
        
        if category:
            filtered = [e for e in filtered if e.category == category]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        
        return sorted(
            filtered,
            key=lambda e: e.detected_at,
            reverse=True,
        )[:limit]
    
    def get_patterns(
        self,
        min_occurrences: int = 2,
    ) -> List[ErrorPattern]:
        """Get detected error patterns."""
        
        return [
            p for p in self._patterns.values()
            if p.occurrence_count >= min_occurrences
        ]
