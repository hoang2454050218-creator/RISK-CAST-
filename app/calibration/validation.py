"""
Confidence Interval Coverage Validation.

Validates that confidence intervals are well-calibrated:
- 90% CIs should contain true value ~90% of the time
- 95% CIs should contain true value ~95% of the time

If actual coverage differs significantly from target, CIs need adjustment.

Addresses audit gap A2.2: "Interval coverage validation - CIs computed but not validated"
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from sqlalchemy import select, func, and_, case
from pydantic import BaseModel, Field, computed_field
import structlog

from app.calibration.models import CICoverageRecordModel, PredictionRecordModel

logger = structlog.get_logger(__name__)


# =============================================================================
# SCHEMAS
# =============================================================================


class CoverageResult(BaseModel):
    """Result of CI coverage validation for a single CI level."""
    
    ci_level: str = Field(description="CI level (90% or 95%)")
    target_coverage: float = Field(description="Expected coverage (0.90 or 0.95)")
    actual_coverage: float = Field(ge=0, le=1, description="Observed coverage rate")
    sample_size: int = Field(ge=0, description="Number of predictions validated")
    
    # Calibration assessment
    calibration_error: float = Field(description="actual_coverage - target_coverage")
    is_calibrated: bool = Field(description="Whether within acceptable error (±5%)")
    
    # Breakdown
    covered_count: int = Field(ge=0)
    not_covered_count: int = Field(ge=0)
    
    # By category
    coverage_by_chokepoint: Dict[str, float] = Field(default_factory=dict)
    coverage_by_event_type: Dict[str, float] = Field(default_factory=dict)
    coverage_by_metric_type: Dict[str, float] = Field(default_factory=dict)
    
    @computed_field
    @property
    def is_over_covering(self) -> bool:
        """Are CIs too wide? (actual > target + tolerance)"""
        return self.calibration_error > 0.05
    
    @computed_field
    @property
    def is_under_covering(self) -> bool:
        """Are CIs too narrow? (actual < target - tolerance)"""
        return self.calibration_error < -0.05


class CalibrationReport(BaseModel):
    """Complete calibration report including CI coverage."""
    
    report_date: datetime
    sample_size: int
    
    # CI coverage results
    ci_90_coverage: CoverageResult
    ci_95_coverage: Optional[CoverageResult] = None
    
    # Calibration curve data
    calibration_curve: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Overall assessment
    overall_calibrated: bool
    recommendations: List[str] = Field(default_factory=list)
    
    # Trends
    coverage_trend_7d: Optional[float] = Field(
        default=None,
        description="Change in coverage over last 7 days"
    )
    coverage_trend_30d: Optional[float] = Field(
        default=None,
        description="Change in coverage over last 30 days"
    )


# =============================================================================
# CI VALIDATOR
# =============================================================================


class CIValidator:
    """
    Validates confidence interval coverage.
    
    A well-calibrated 90% CI should contain the true value ~90% of time.
    If actual coverage is significantly different, CIs are miscalibrated:
    - Under-coverage (<85%): CIs too narrow, over-confident
    - Over-coverage (>95%): CIs too wide, under-confident
    """
    
    ACCEPTABLE_ERROR = 0.05  # ±5% is acceptable
    MIN_SAMPLES = 20  # Minimum samples for meaningful analysis
    
    def __init__(self, session_factory):
        self._session_factory = session_factory
    
    async def validate_coverage(
        self,
        ci_level: str = "90%",
        metric_type: Optional[str] = None,
        chokepoint: Optional[str] = None,
        days: int = 90,
    ) -> CoverageResult:
        """
        Validate CI coverage against actual outcomes.
        
        Args:
            ci_level: Which CI to validate ("90%" or "95%")
            metric_type: Filter by metric type (exposure, delay, cost, inaction)
            chokepoint: Filter by chokepoint
            days: Number of days to look back
            
        Returns:
            CoverageResult with coverage statistics
        """
        target = 0.90 if ci_level == "90%" else 0.95
        
        async with self._session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = select(CICoverageRecordModel).where(
                and_(
                    CICoverageRecordModel.ci_level == ci_level,
                    CICoverageRecordModel.resolved_at.isnot(None),
                    CICoverageRecordModel.recorded_at >= cutoff,
                )
            )
            
            if metric_type:
                query = query.where(CICoverageRecordModel.metric_type == metric_type)
            if chokepoint:
                query = query.where(CICoverageRecordModel.chokepoint == chokepoint)
            
            result = await session.execute(query)
            records = result.scalars().all()
        
        if not records:
            return CoverageResult(
                ci_level=ci_level,
                target_coverage=target,
                actual_coverage=0.0,
                sample_size=0,
                calibration_error=0.0,
                is_calibrated=True,  # No data to say otherwise
                covered_count=0,
                not_covered_count=0,
            )
        
        # Calculate coverage
        covered = sum(1 for r in records if r.is_covered)
        not_covered = len(records) - covered
        actual_coverage = covered / len(records)
        calibration_error = actual_coverage - target
        
        # Calculate by category
        by_chokepoint = self._group_coverage(records, "chokepoint")
        by_event_type = self._group_coverage(records, "event_type")
        by_metric = self._group_coverage(records, "metric_type")
        
        return CoverageResult(
            ci_level=ci_level,
            target_coverage=target,
            actual_coverage=round(actual_coverage, 4),
            sample_size=len(records),
            calibration_error=round(calibration_error, 4),
            is_calibrated=abs(calibration_error) <= self.ACCEPTABLE_ERROR,
            covered_count=covered,
            not_covered_count=not_covered,
            coverage_by_chokepoint=by_chokepoint,
            coverage_by_event_type=by_event_type,
            coverage_by_metric_type=by_metric,
        )
    
    def _group_coverage(
        self,
        records: List[CICoverageRecordModel],
        attribute: str,
    ) -> Dict[str, float]:
        """Calculate coverage grouped by attribute."""
        groups: Dict[str, List[bool]] = {}
        
        for record in records:
            key = getattr(record, attribute) or "unknown"
            if key not in groups:
                groups[key] = []
            groups[key].append(record.is_covered)
        
        return {
            k: round(sum(v) / len(v), 4) if v else 0.0
            for k, v in groups.items()
        }
    
    async def generate_calibration_report(
        self,
        days: int = 90,
    ) -> CalibrationReport:
        """
        Generate comprehensive calibration report.
        
        Includes:
        - CI coverage for 90% and 95% levels
        - Calibration curve
        - Trend analysis
        - Recommendations
        """
        # Validate both CI levels
        ci_90_result = await self.validate_coverage("90%", days=days)
        ci_95_result = await self.validate_coverage("95%", days=days)
        
        # Calculate calibration curve
        calibration_curve = await self._calculate_calibration_curve(days)
        
        # Calculate trends
        coverage_7d = await self._calculate_coverage_trend(7)
        coverage_30d = await self._calculate_coverage_trend(30)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            ci_90_result, ci_95_result, calibration_curve
        )
        
        # Overall assessment
        overall_calibrated = (
            ci_90_result.is_calibrated and
            (ci_95_result is None or ci_95_result.sample_size == 0 or ci_95_result.is_calibrated)
        )
        
        return CalibrationReport(
            report_date=datetime.utcnow(),
            sample_size=ci_90_result.sample_size,
            ci_90_coverage=ci_90_result,
            ci_95_coverage=ci_95_result if ci_95_result.sample_size > 0 else None,
            calibration_curve=calibration_curve,
            overall_calibrated=overall_calibrated,
            recommendations=recommendations,
            coverage_trend_7d=coverage_7d,
            coverage_trend_30d=coverage_30d,
        )
    
    async def _calculate_calibration_curve(
        self,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """
        Calculate calibration curve data.
        
        For each confidence bucket, calculate predicted vs actual frequency.
        """
        async with self._session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(PredictionRecordModel).where(
                    and_(
                        PredictionRecordModel.resolved_at.isnot(None),
                        PredictionRecordModel.recorded_at >= cutoff,
                    )
                )
            )
            records = result.scalars().all()
        
        if not records:
            return []
        
        # Group into buckets
        buckets: Dict[str, List[tuple]] = {}
        for record in records:
            bucket_idx = int(record.predicted_confidence * 10)
            bucket_name = f"{bucket_idx * 10}-{(bucket_idx + 1) * 10}%"
            if bucket_name not in buckets:
                buckets[bucket_name] = []
            buckets[bucket_name].append(
                (record.predicted_confidence, record.actual_outcome)
            )
        
        # Calculate for each bucket
        curve = []
        for bucket_name in sorted(buckets.keys()):
            data = buckets[bucket_name]
            avg_predicted = sum(p[0] for p in data) / len(data)
            actual_frequency = sum(1 for p in data if p[1]) / len(data)
            
            curve.append({
                "bucket": bucket_name,
                "predicted_probability": round(avg_predicted, 3),
                "actual_frequency": round(actual_frequency, 3),
                "sample_count": len(data),
                "calibration_error": round(actual_frequency - avg_predicted, 3),
            })
        
        return curve
    
    async def _calculate_coverage_trend(
        self,
        days: int,
    ) -> Optional[float]:
        """Calculate trend in CI coverage over time period."""
        async with self._session_factory() as session:
            now = datetime.utcnow()
            period_start = now - timedelta(days=days)
            period_mid = now - timedelta(days=days // 2)
            
            # First half
            first_half = await session.execute(
                select(
                    func.count(case((CICoverageRecordModel.is_covered == True, 1))),
                    func.count(CICoverageRecordModel.id),
                ).where(
                    and_(
                        CICoverageRecordModel.resolved_at >= period_start,
                        CICoverageRecordModel.resolved_at < period_mid,
                        CICoverageRecordModel.ci_level == "90%",
                    )
                )
            )
            first_covered, first_total = first_half.one()
            
            # Second half
            second_half = await session.execute(
                select(
                    func.count(case((CICoverageRecordModel.is_covered == True, 1))),
                    func.count(CICoverageRecordModel.id),
                ).where(
                    and_(
                        CICoverageRecordModel.resolved_at >= period_mid,
                        CICoverageRecordModel.resolved_at <= now,
                        CICoverageRecordModel.ci_level == "90%",
                    )
                )
            )
            second_covered, second_total = second_half.one()
        
        if first_total < 10 or second_total < 10:
            return None
        
        first_rate = first_covered / first_total
        second_rate = second_covered / second_total
        
        return round(second_rate - first_rate, 4)
    
    def _generate_recommendations(
        self,
        ci_90: CoverageResult,
        ci_95: CoverageResult,
        curve: List[Dict],
    ) -> List[str]:
        """Generate calibration improvement recommendations."""
        recommendations = []
        
        # Check sample size
        if ci_90.sample_size < self.MIN_SAMPLES:
            recommendations.append(
                f"Insufficient data ({ci_90.sample_size} samples). "
                f"Need at least {self.MIN_SAMPLES} resolved predictions for reliable analysis."
            )
            return recommendations
        
        # Check 90% CI coverage
        if ci_90.is_under_covering:
            recommendations.append(
                f"90% CIs are too narrow (actual coverage {ci_90.actual_coverage:.1%}). "
                f"Widen intervals by ~{abs(ci_90.calibration_error) * 100:.0f}% to improve coverage."
            )
        elif ci_90.is_over_covering:
            recommendations.append(
                f"90% CIs are too wide (actual coverage {ci_90.actual_coverage:.1%}). "
                f"Consider narrowing intervals by ~{ci_90.calibration_error * 100:.0f}%."
            )
        
        # Check for category-specific issues
        for chokepoint, coverage in ci_90.coverage_by_chokepoint.items():
            if abs(coverage - ci_90.target_coverage) > 0.15:
                recommendations.append(
                    f"Chokepoint '{chokepoint}' has significant miscalibration "
                    f"({coverage:.1%} coverage). Consider chokepoint-specific CI widths."
                )
        
        for metric, coverage in ci_90.coverage_by_metric_type.items():
            if abs(coverage - ci_90.target_coverage) > 0.15:
                recommendations.append(
                    f"Metric '{metric}' has miscalibrated CIs ({coverage:.1%} coverage). "
                    f"Review uncertainty model for this metric."
                )
        
        # Check calibration curve
        poorly_calibrated = [
            p for p in curve
            if abs(p["calibration_error"]) > 0.15 and p["sample_count"] >= 10
        ]
        if poorly_calibrated:
            buckets = ", ".join(p["bucket"] for p in poorly_calibrated[:3])
            recommendations.append(
                f"Confidence poorly calibrated in buckets: {buckets}. "
                f"Review confidence calculation for these ranges."
            )
        
        if not recommendations:
            recommendations.append(
                "CI coverage is well-calibrated. Continue monitoring."
            )
        
        return recommendations


# =============================================================================
# FACTORY
# =============================================================================


def create_ci_validator(session_factory) -> CIValidator:
    """Create CI validator instance."""
    return CIValidator(session_factory)
