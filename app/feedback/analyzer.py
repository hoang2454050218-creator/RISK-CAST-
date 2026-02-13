"""
Feedback Analyzer for RISKCAST.

Analyzes feedback and outcomes to measure system performance and identify improvements.

Key analyses:
1. Accuracy Reports - How accurate are predictions?
2. Calibration Reports - Are confidence scores reliable?
3. Trend Analysis - Is the system improving over time?
4. Improvement Insights - What specific areas need work?

Usage:
    from app.feedback import FeedbackAnalyzer, create_feedback_analyzer
    
    analyzer = create_feedback_analyzer(feedback_service)
    
    # Get accuracy report
    report = await analyzer.generate_accuracy_report(days=30)
    print(f"Accuracy: {report.overall_accuracy:.0%}")
    
    # Get calibration analysis
    calibration = await analyzer.generate_calibration_report(days=30)
    print(f"Brier Score: {calibration.brier_score:.3f}")
    
    # Get improvement insights
    insights = await analyzer.get_improvement_insights()
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict
import uuid
import math
import statistics

import structlog

from app.feedback.schemas import (
    OutcomeRecord,
    AccuracyReport,
    CalibrationReport,
    TrendAnalysis,
    ImprovementSignal,
    ImprovementArea,
)
from app.feedback.service import FeedbackService

logger = structlog.get_logger(__name__)


# =============================================================================
# FEEDBACK ANALYZER
# =============================================================================


class FeedbackAnalyzer:
    """
    Analyzes feedback data to measure and improve system performance.
    
    This is the brain of the self-improving system.
    """
    
    def __init__(
        self,
        feedback_service: FeedbackService,
        calibration_buckets: int = 10,
    ):
        """
        Initialize feedback analyzer.
        
        Args:
            feedback_service: FeedbackService for data access
            calibration_buckets: Number of buckets for calibration analysis
        """
        self._service = feedback_service
        self._num_buckets = calibration_buckets
    
    # =========================================================================
    # ACCURACY REPORTS
    # =========================================================================
    
    async def generate_accuracy_report(
        self,
        days: int = 30,
        customer_id: Optional[str] = None,
    ) -> AccuracyReport:
        """
        Generate comprehensive accuracy report.
        
        Args:
            days: Number of days to analyze
            customer_id: Optional customer filter
            
        Returns:
            AccuracyReport with all metrics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Get outcomes
        outcomes = await self._service.get_outcomes(
            customer_id=customer_id,
            since=since,
            limit=10000,
        )
        
        if not outcomes:
            return self._empty_accuracy_report(days)
        
        # Get feedback for satisfaction metrics
        feedback_stats = await self._service.get_feedback_stats(
            customer_id=customer_id,
            days=days,
        )
        
        # Calculate accuracy metrics
        correct = [o for o in outcomes if o.prediction_correct]
        
        # True positives: predicted event AND event occurred
        true_positives = sum(
            1 for o in outcomes
            if o.predicted_event and o.event_occurred
        )
        
        # False positives: predicted event BUT event didn't occur
        false_positives = sum(
            1 for o in outcomes
            if o.predicted_event and not o.event_occurred
        )
        
        # False negatives: didn't predict event BUT event occurred
        false_negatives = sum(
            1 for o in outcomes
            if not o.predicted_event and o.event_occurred
        )
        
        # True negatives: didn't predict AND didn't occur
        true_negatives = sum(
            1 for o in outcomes
            if not o.predicted_event and not o.event_occurred
        )
        
        # Calculate precision, recall, F1
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        overall_accuracy = len(correct) / len(outcomes) if outcomes else 0
        
        # Delay accuracy
        delay_errors = [
            o.delay_error_abs for o in outcomes
            if o.delay_error_abs is not None
        ]
        delay_accurate = [o for o in outcomes if o.delay_accurate]
        
        # Cost accuracy
        cost_errors = [
            o.cost_error_abs for o in outcomes
            if o.cost_error_abs is not None
        ]
        cost_pct_errors = [
            abs(o.cost_error_pct) for o in outcomes
            if o.cost_error_pct is not None
        ]
        cost_accurate = [o for o in outcomes if o.cost_accurate]
        
        # By category breakdowns
        accuracy_by_chokepoint = self._calculate_accuracy_by_field(
            outcomes, self._extract_chokepoint
        )
        accuracy_by_action = self._calculate_accuracy_by_field(
            outcomes, lambda o: o.recommended_action
        )
        
        # Value metrics
        values = [
            o.value_delivered_usd for o in outcomes
            if o.value_delivered_usd is not None and o.value_delivered_usd > 0
        ]
        total_value = sum(values) if values else 0
        
        report = AccuracyReport(
            report_id=f"acc_{datetime.utcnow().strftime('%Y%m%d')}",
            period_start=since,
            period_end=datetime.utcnow(),
            period_days=days,
            # Counts
            total_decisions=len(outcomes),
            decisions_with_outcome=len(outcomes),
            # Overall accuracy
            overall_accuracy=overall_accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            # Delay
            delay_accuracy_mean=(
                len(delay_accurate) / len(outcomes) if outcomes else None
            ),
            delay_mae_days=(
                sum(delay_errors) / len(delay_errors) if delay_errors else None
            ),
            # Cost
            cost_accuracy_mean=(
                len(cost_accurate) / len(outcomes) if outcomes else None
            ),
            cost_mae_usd=(
                sum(cost_errors) / len(cost_errors) if cost_errors else None
            ),
            cost_mape=(
                sum(cost_pct_errors) / len(cost_pct_errors) if cost_pct_errors else None
            ),
            # By category
            accuracy_by_chokepoint=accuracy_by_chokepoint,
            accuracy_by_event_type={},  # Would need event type data
            accuracy_by_action=accuracy_by_action,
            # Customer metrics
            action_uptake_rate=feedback_stats.get("action_uptake_rate", 0),
            avg_satisfaction=feedback_stats.get("avg_satisfaction"),
            nps_score=None,  # Would need NPS data
            # Value
            total_value_delivered_usd=total_value,
            avg_value_per_decision_usd=(
                total_value / len(values) if values else 0
            ),
        )
        
        logger.info(
            "accuracy_report_generated",
            report_id=report.report_id,
            period_days=days,
            total_decisions=len(outcomes),
            overall_accuracy=overall_accuracy,
            grade=report.grade,
        )
        
        return report
    
    def _empty_accuracy_report(self, days: int) -> AccuracyReport:
        """Create empty accuracy report."""
        now = datetime.utcnow()
        return AccuracyReport(
            report_id=f"acc_{now.strftime('%Y%m%d')}_empty",
            period_start=now - timedelta(days=days),
            period_end=now,
            period_days=days,
            total_decisions=0,
            decisions_with_outcome=0,
            overall_accuracy=0,
            precision=0,
            recall=0,
            f1_score=0,
            action_uptake_rate=0,
            total_value_delivered_usd=0,
            avg_value_per_decision_usd=0,
        )
    
    def _calculate_accuracy_by_field(
        self,
        outcomes: list[OutcomeRecord],
        field_extractor,
    ) -> dict[str, float]:
        """Calculate accuracy grouped by a field."""
        grouped: dict[str, list[bool]] = defaultdict(list)
        
        for o in outcomes:
            field_value = field_extractor(o)
            if field_value:
                grouped[field_value].append(o.prediction_correct)
        
        return {
            field: sum(accuracies) / len(accuracies)
            for field, accuracies in grouped.items()
            if len(accuracies) >= 5  # Minimum sample size
        }
    
    def _extract_chokepoint(self, outcome: OutcomeRecord) -> Optional[str]:
        """Extract chokepoint from outcome."""
        signal_id = outcome.signal_id.lower()
        
        chokepoints = ["red_sea", "suez", "panama", "malacca", "hormuz"]
        for cp in chokepoints:
            if cp.replace("_", "") in signal_id or cp in signal_id:
                return cp
        
        return None
    
    # =========================================================================
    # CALIBRATION REPORTS
    # =========================================================================
    
    async def generate_calibration_report(
        self,
        days: int = 30,
        customer_id: Optional[str] = None,
    ) -> CalibrationReport:
        """
        Generate confidence calibration report.
        
        Perfect calibration: 70% confidence = 70% accuracy
        
        Args:
            days: Number of days to analyze
            customer_id: Optional customer filter
            
        Returns:
            CalibrationReport with Brier score and bucket analysis
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        outcomes = await self._service.get_outcomes(
            customer_id=customer_id,
            since=since,
            limit=10000,
        )
        
        if not outcomes:
            return self._empty_calibration_report(days)
        
        # Group by confidence bucket
        buckets: dict[int, list[tuple[float, bool]]] = defaultdict(list)
        
        for o in outcomes:
            bucket_idx = int(o.predicted_confidence * self._num_buckets)
            bucket_idx = min(bucket_idx, self._num_buckets - 1)
            buckets[bucket_idx].append((o.predicted_confidence, o.event_occurred))
        
        # Calculate Brier score
        brier_sum = sum(
            (o.predicted_confidence - (1.0 if o.event_occurred else 0.0)) ** 2
            for o in outcomes
        )
        brier_score = brier_sum / len(outcomes)
        
        # Calculate log loss
        log_loss = self._calculate_log_loss(outcomes)
        
        # Analyze buckets
        bucket_data = []
        overconfident = []
        underconfident = []
        adjustments = {}
        
        for i in range(self._num_buckets):
            bucket_outcomes = buckets.get(i, [])
            if not bucket_outcomes:
                continue
            
            bucket_min = i / self._num_buckets
            bucket_max = (i + 1) / self._num_buckets
            bucket_name = f"{int(bucket_min * 100)}-{int(bucket_max * 100)}%"
            
            avg_confidence = sum(p[0] for p in bucket_outcomes) / len(bucket_outcomes)
            actual_accuracy = sum(1 for p in bucket_outcomes if p[1]) / len(bucket_outcomes)
            
            calibration_error = avg_confidence - actual_accuracy
            
            bucket_data.append({
                "bucket": bucket_name,
                "bucket_min": bucket_min,
                "bucket_max": bucket_max,
                "sample_count": len(bucket_outcomes),
                "avg_confidence": avg_confidence,
                "actual_accuracy": actual_accuracy,
                "calibration_error": calibration_error,
            })
            
            # Identify mis-calibrated buckets
            if calibration_error > 0.10:
                overconfident.append(bucket_name)
                adjustments[bucket_name] = -calibration_error
            elif calibration_error < -0.10:
                underconfident.append(bucket_name)
                adjustments[bucket_name] = -calibration_error
        
        report = CalibrationReport(
            report_id=f"cal_{datetime.utcnow().strftime('%Y%m%d')}",
            period_start=since,
            period_end=datetime.utcnow(),
            brier_score=brier_score,
            log_loss=log_loss,
            buckets=bucket_data,
            overconfident_buckets=overconfident,
            underconfident_buckets=underconfident,
            recommended_adjustments=adjustments,
            sample_count=len(outcomes),
        )
        
        logger.info(
            "calibration_report_generated",
            report_id=report.report_id,
            brier_score=brier_score,
            is_well_calibrated=report.is_well_calibrated,
            overconfident_buckets=len(overconfident),
            underconfident_buckets=len(underconfident),
        )
        
        return report
    
    def _empty_calibration_report(self, days: int) -> CalibrationReport:
        """Create empty calibration report."""
        now = datetime.utcnow()
        return CalibrationReport(
            report_id=f"cal_{now.strftime('%Y%m%d')}_empty",
            period_start=now - timedelta(days=days),
            period_end=now,
            brier_score=1.0,
            buckets=[],
            overconfident_buckets=[],
            underconfident_buckets=[],
            recommended_adjustments={},
            sample_count=0,
        )
    
    def _calculate_log_loss(self, outcomes: list[OutcomeRecord]) -> Optional[float]:
        """Calculate logarithmic loss."""
        if not outcomes:
            return None
        
        eps = 1e-15  # Small epsilon to avoid log(0)
        total_loss = 0
        
        for o in outcomes:
            p = max(eps, min(1 - eps, o.predicted_confidence))
            y = 1 if o.event_occurred else 0
            
            loss = -(y * math.log(p) + (1 - y) * math.log(1 - p))
            total_loss += loss
        
        return total_loss / len(outcomes)
    
    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================
    
    async def analyze_trend(
        self,
        metric: str,
        periods: int = 8,
        period_type: str = "weekly",
    ) -> TrendAnalysis:
        """
        Analyze trend for a specific metric.
        
        Args:
            metric: Metric name (e.g., "overall_accuracy", "delay_mae_days")
            periods: Number of periods to analyze
            period_type: "daily", "weekly", or "monthly"
            
        Returns:
            TrendAnalysis with trend direction and data points
        """
        # Determine period length
        if period_type == "daily":
            period_days = 1
        elif period_type == "weekly":
            period_days = 7
        else:  # monthly
            period_days = 30
        
        # Collect data points
        data_points = []
        
        for i in range(periods):
            period_end = datetime.utcnow() - timedelta(days=i * period_days)
            period_start = period_end - timedelta(days=period_days)
            
            # Get report for this period
            outcomes = await self._service.get_outcomes(
                since=period_start,
                limit=10000,
            )
            
            # Filter to this period
            outcomes = [
                o for o in outcomes
                if period_start <= o.observed_at < period_end
            ]
            
            if not outcomes:
                continue
            
            # Calculate metric value
            value = self._calculate_metric(outcomes, metric)
            
            if value is not None:
                data_points.append({
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "value": value,
                    "sample_count": len(outcomes),
                })
        
        # Sort chronologically
        data_points.sort(key=lambda x: x["period_start"])
        
        if len(data_points) < 2:
            return TrendAnalysis(
                metric=metric,
                trend="stable",
                change_pct=0,
                data_points=data_points,
                current_value=data_points[-1]["value"] if data_points else 0,
                previous_value=data_points[-2]["value"] if len(data_points) >= 2 else 0,
                period_type=period_type,
                periods_analyzed=len(data_points),
            )
        
        # Calculate trend
        current = data_points[-1]["value"]
        previous = data_points[-2]["value"]
        
        if previous == 0:
            change_pct = 0
        else:
            change_pct = ((current - previous) / previous) * 100
        
        # Determine trend direction (considering if higher is better)
        higher_is_better = metric in [
            "overall_accuracy", "precision", "recall", "f1_score",
            "delay_accuracy_mean", "cost_accuracy_mean",
        ]
        
        if abs(change_pct) < 2:
            trend = "stable"
        elif (change_pct > 0 and higher_is_better) or (change_pct < 0 and not higher_is_better):
            trend = "improving"
        else:
            trend = "declining"
        
        # Calculate baseline (average of all points except last)
        baseline_values = [p["value"] for p in data_points[:-1]]
        baseline = statistics.mean(baseline_values) if baseline_values else None
        
        return TrendAnalysis(
            metric=metric,
            trend=trend,
            change_pct=change_pct,
            data_points=data_points,
            current_value=current,
            previous_value=previous,
            baseline_value=baseline,
            is_significant=abs(change_pct) > 5,
            period_type=period_type,
            periods_analyzed=len(data_points),
        )
    
    def _calculate_metric(
        self,
        outcomes: list[OutcomeRecord],
        metric: str,
    ) -> Optional[float]:
        """Calculate a specific metric from outcomes."""
        if not outcomes:
            return None
        
        if metric == "overall_accuracy":
            correct = sum(1 for o in outcomes if o.prediction_correct)
            return correct / len(outcomes)
        
        elif metric == "delay_mae_days":
            errors = [o.delay_error_abs for o in outcomes if o.delay_error_abs is not None]
            return statistics.mean(errors) if errors else None
        
        elif metric == "cost_mape":
            errors = [abs(o.cost_error_pct) for o in outcomes if o.cost_error_pct is not None]
            return statistics.mean(errors) if errors else None
        
        elif metric == "value_delivered_usd":
            values = [o.value_delivered_usd for o in outcomes if o.value_delivered_usd]
            return sum(values) if values else 0
        
        return None
    
    # =========================================================================
    # IMPROVEMENT INSIGHTS
    # =========================================================================
    
    async def get_improvement_insights(
        self,
        days: int = 30,
        min_samples: int = 10,
    ) -> dict[str, Any]:
        """
        Get comprehensive improvement insights.
        
        Returns actionable recommendations based on all analyses.
        """
        # Get reports
        accuracy_report = await self.generate_accuracy_report(days=days)
        calibration_report = await self.generate_calibration_report(days=days)
        
        # Get improvement signals from service
        improvement_signals = await self._service.check_for_improvement_signals(
            min_samples=min_samples
        )
        
        # Analyze trends
        accuracy_trend = await self.analyze_trend("overall_accuracy", periods=4)
        delay_trend = await self.analyze_trend("delay_mae_days", periods=4)
        
        # Compile insights
        insights = {
            "summary": {
                "overall_grade": accuracy_report.grade,
                "accuracy": accuracy_report.overall_accuracy,
                "calibration_quality": "Good" if calibration_report.is_well_calibrated else "Needs Improvement",
                "trend": accuracy_trend.trend,
                "period_days": days,
            },
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "improvement_signals": [
                {
                    "area": s.area.value,
                    "severity": s.severity,
                    "message": s.message,
                    "recommendation": s.recommended_action,
                }
                for s in improvement_signals
            ],
        }
        
        # Identify strengths
        if accuracy_report.overall_accuracy >= 0.80:
            insights["strengths"].append(
                f"Strong overall accuracy: {accuracy_report.overall_accuracy:.0%}"
            )
        
        if calibration_report.is_well_calibrated:
            insights["strengths"].append(
                f"Well-calibrated confidence scores (Brier: {calibration_report.brier_score:.3f})"
            )
        
        if accuracy_trend.is_improving:
            insights["strengths"].append(
                f"Accuracy is improving: +{accuracy_trend.change_pct:.1f}%"
            )
        
        if accuracy_report.action_uptake_rate >= 0.70:
            insights["strengths"].append(
                f"High customer action uptake: {accuracy_report.action_uptake_rate:.0%}"
            )
        
        # High-performing chokepoints
        for cp, acc in accuracy_report.accuracy_by_chokepoint.items():
            if acc >= 0.85:
                insights["strengths"].append(f"Excellent accuracy for {cp}: {acc:.0%}")
        
        # Identify weaknesses
        if accuracy_report.overall_accuracy < 0.70:
            insights["weaknesses"].append(
                f"Low overall accuracy: {accuracy_report.overall_accuracy:.0%}"
            )
        
        if not calibration_report.is_well_calibrated:
            insights["weaknesses"].append(
                f"Poor confidence calibration (Brier: {calibration_report.brier_score:.3f})"
            )
        
        if accuracy_trend.is_concerning:
            insights["weaknesses"].append(
                f"Accuracy is declining: {accuracy_trend.change_pct:.1f}%"
            )
        
        if calibration_report.overconfident_buckets:
            insights["weaknesses"].append(
                f"Overconfident in buckets: {', '.join(calibration_report.overconfident_buckets)}"
            )
        
        # Low-performing chokepoints
        for cp, acc in accuracy_report.accuracy_by_chokepoint.items():
            if acc < 0.65:
                insights["weaknesses"].append(f"Low accuracy for {cp}: {acc:.0%}")
        
        # Generate recommendations
        if calibration_report.recommended_adjustments:
            for bucket, adj in calibration_report.recommended_adjustments.items():
                direction = "Reduce" if adj < 0 else "Increase"
                insights["recommendations"].append(
                    f"{direction} confidence by {abs(adj):.0%} for {bucket} predictions"
                )
        
        if accuracy_report.cost_mape and accuracy_report.cost_mape > 30:
            insights["recommendations"].append(
                f"Improve cost estimation (current MAPE: {accuracy_report.cost_mape:.0f}%)"
            )
        
        if accuracy_report.delay_mae_days and accuracy_report.delay_mae_days > 3:
            insights["recommendations"].append(
                f"Improve delay estimation (current MAE: {accuracy_report.delay_mae_days:.1f} days)"
            )
        
        if accuracy_report.action_uptake_rate < 0.50:
            insights["recommendations"].append(
                "Investigate low action uptake - recommendations may not be actionable enough"
            )
        
        logger.info(
            "improvement_insights_generated",
            grade=insights["summary"]["overall_grade"],
            strengths=len(insights["strengths"]),
            weaknesses=len(insights["weaknesses"]),
            recommendations=len(insights["recommendations"]),
        )
        
        return insights


# =============================================================================
# FACTORY
# =============================================================================


def create_feedback_analyzer(
    feedback_service: Optional[FeedbackService] = None,
    calibration_buckets: int = 10,
) -> FeedbackAnalyzer:
    """
    Create feedback analyzer instance.
    
    Args:
        feedback_service: FeedbackService (creates new if None)
        calibration_buckets: Number of buckets for calibration
        
    Returns:
        FeedbackAnalyzer instance
    """
    from app.feedback.service import get_feedback_service
    
    service = feedback_service or get_feedback_service()
    
    return FeedbackAnalyzer(
        feedback_service=service,
        calibration_buckets=calibration_buckets,
    )
