"""
Backtesting Framework for RISKCAST Decision Validation.

Validates decision quality against historical events with known outcomes.

Usage:
    from app.backtest import BacktestFramework, BacktestEvent
    
    # Create framework
    framework = BacktestFramework()
    
    # Load historical events
    events = load_historical_events("2024-01-01", "2024-12-31")
    
    # Run backtest against customer context
    summary = await framework.run(events, customer_contexts)
    
    # Analyze results
    print(summary.get_summary_text())

Pipeline:
    1. BacktestEvent → Simulate OmenSignal
    2. OmenSignal → Create CorrelatedIntelligence
    3. Intelligence + Context → RISKCAST Decision
    4. Decision vs ActualImpact → Calculate accuracy & value
    5. Aggregate → BacktestSummary with calibration
"""

from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict
import uuid
import math

import structlog

from app.backtest.schemas import (
    BacktestEvent,
    BacktestResult,
    BacktestSummary,
    CalibrationBucket,
    AccuracyByCategory,
    PredictionVsActual,
    ValueAnalysis,
    EventOutcome,
    ActionTaken,
    DecisionQuality,
)
from app.omen.schemas import (
    OmenSignal,
    SignalCategory,
    Chokepoint,
    GeographicScope,
    TemporalScope,
    EvidenceItem,
)
from app.oracle.schemas import (
    CorrelatedIntelligence,
    CorrelationStatus,
    ChokepointHealth,
    RealitySnapshot,
)
from app.riskcast.composers import DecisionComposer, create_decision_composer
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import DecisionObject


logger = structlog.get_logger(__name__)


# =============================================================================
# BACKTEST FRAMEWORK
# =============================================================================


class BacktestFramework:
    """
    Framework for backtesting RISKCAST decisions against historical events.
    
    This is the core validation tool that measures:
    - Prediction accuracy (did we predict correctly?)
    - Calibration (are confidence scores reliable?)
    - Value delivered (did following advice save money?)
    
    The goal is to answer: "Would RISKCAST have given good advice?"
    """
    
    def __init__(
        self,
        decision_composer: Optional[DecisionComposer] = None,
        calibration_buckets: int = 10,
        value_threshold_usd: float = 1000.0,
    ):
        """
        Initialize backtest framework.
        
        Args:
            decision_composer: Custom decision composer (uses default if None)
            calibration_buckets: Number of buckets for calibration analysis
            value_threshold_usd: Minimum net value to count as "good" advice
        """
        self._composer = decision_composer or create_decision_composer()
        self._num_buckets = calibration_buckets
        self._value_threshold = value_threshold_usd
        
        # For tracking calibration
        self._predictions_by_bucket: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    async def run(
        self,
        events: list[BacktestEvent],
        customer_contexts: list[CustomerContext],
        filters: Optional[dict[str, Any]] = None,
    ) -> BacktestSummary:
        """
        Run backtest against historical events.
        
        Args:
            events: List of historical events with known outcomes
            customer_contexts: Customer contexts to test against
            filters: Optional filters (chokepoint, category, date_range, etc.)
        
        Returns:
            BacktestSummary with accuracy, calibration, and value metrics
        """
        # Apply filters
        filtered_events = self._apply_filters(events, filters or {})
        
        if not filtered_events:
            logger.warning("backtest_no_events", filters=filters)
            return self._empty_summary(filters or {})
        
        logger.info(
            "backtest_starting",
            total_events=len(filtered_events),
            customers=len(customer_contexts),
            filters=filters,
        )
        
        # Reset calibration tracking
        self._predictions_by_bucket = defaultdict(list)
        
        # Run backtest for each event-customer combination
        results: list[BacktestResult] = []
        
        for event in filtered_events:
            for context in customer_contexts:
                try:
                    result = await self._test_single_event(event, context)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(
                        "backtest_event_failed",
                        event_id=event.event_id,
                        customer_id=context.profile.customer_id,
                        error=str(e),
                    )
        
        # Calculate summary
        summary = self._calculate_summary(
            results=results,
            events=filtered_events,
            filters=filters or {},
        )
        
        logger.info(
            "backtest_complete",
            total_results=len(results),
            accuracy=summary.accuracy,
            value_captured=summary.total_value_captured_usd,
            grade=summary.grade,
        )
        
        return summary
    
    # =========================================================================
    # SINGLE EVENT TESTING
    # =========================================================================
    
    async def _test_single_event(
        self,
        event: BacktestEvent,
        context: CustomerContext,
    ) -> Optional[BacktestResult]:
        """
        Test RISKCAST against a single historical event.
        
        Args:
            event: Historical event with known outcome
            context: Customer context
            
        Returns:
            BacktestResult or None if no decision generated
        """
        # Step 1: Simulate OmenSignal from event
        signal = self._simulate_signal(event)
        
        # Step 2: Create CorrelatedIntelligence
        intelligence = self._create_intelligence(signal, event)
        
        # Step 3: Generate RISKCAST decision
        decision = self._composer.compose(intelligence, context)
        
        if not decision:
            # No exposure for this customer
            return None
        
        # Step 4: Compare decision to actual outcome
        result = self._evaluate_decision(event, decision, context)
        
        # Track for calibration
        bucket_idx = int(decision.q6_confidence.score * self._num_buckets)
        bucket_idx = min(bucket_idx, self._num_buckets - 1)
        actual_occurred = event.outcome in [
            EventOutcome.MATERIALIZED,
            EventOutcome.PARTIALLY_MATERIALIZED,
        ]
        self._predictions_by_bucket[bucket_idx].append(
            (decision.q6_confidence.score, actual_occurred)
        )
        
        return result
    
    # =========================================================================
    # SIGNAL SIMULATION
    # =========================================================================
    
    def _simulate_signal(self, event: BacktestEvent) -> OmenSignal:
        """
        Simulate an OmenSignal from a historical event.
        
        Recreates what OMEN would have output at the time.
        """
        # Map event category to signal category
        category_map = {
            "geopolitical": SignalCategory.GEOPOLITICAL,
            "weather": SignalCategory.WEATHER,
            "infrastructure": SignalCategory.INFRASTRUCTURE,
            "labor": SignalCategory.LABOR,
            "economic": SignalCategory.ECONOMIC,
            "security": SignalCategory.SECURITY,
        }
        category = category_map.get(event.category.lower(), SignalCategory.OTHER)
        
        # Map chokepoint
        try:
            chokepoint = Chokepoint(event.chokepoint)
        except ValueError:
            chokepoint = Chokepoint.RED_SEA  # Default
        
        # Calculate earliest impact
        lead_time = timedelta(hours=event.detection_lead_time_hours)
        earliest_impact = event.event_date - lead_time + timedelta(days=1)
        
        # Build evidence item
        evidence = EvidenceItem(
            source="Historical Data",
            source_type="backtest",
            title=f"Backtest event: {event.event_name}",
            snippet=event.notes,
            published_at=event.event_date - lead_time,
            probability=event.signal_probability,
        )
        
        return OmenSignal(
            signal_id=f"OMEN-BT-{event.event_id}",
            title=event.event_name,
            description=f"Backtest signal for historical event {event.event_id}",
            category=category,
            probability=event.signal_probability,
            confidence_score=event.signal_confidence,
            geographic=GeographicScope(
                primary_chokepoint=chokepoint,
                secondary_chokepoints=[
                    Chokepoint(cp) for cp in event.secondary_chokepoints
                    if cp in [c.value for c in Chokepoint]
                ],
                affected_regions=[event.chokepoint.replace("_", " ").title()],
            ),
            temporal=TemporalScope(
                detected_at=event.event_date - lead_time,
                earliest_impact=earliest_impact,
                latest_resolution=event.event_date + timedelta(days=30),
                is_ongoing=event.outcome == EventOutcome.ONGOING,
            ),
            evidence=[evidence],
            created_at=event.event_date - lead_time,
        )
    
    def _create_intelligence(
        self,
        signal: OmenSignal,
        event: BacktestEvent,
    ) -> CorrelatedIntelligence:
        """
        Create CorrelatedIntelligence from signal and event data.
        """
        # Determine correlation status based on outcome
        if event.outcome == EventOutcome.MATERIALIZED:
            status = CorrelationStatus.CONFIRMED
        elif event.outcome == EventOutcome.PARTIALLY_MATERIALIZED:
            status = CorrelationStatus.MATERIALIZING
        elif event.outcome == EventOutcome.ONGOING:
            status = CorrelationStatus.MATERIALIZING
        else:
            status = CorrelationStatus.PREDICTED_NOT_OBSERVED
        
        # Build reality snapshot
        chokepoint_health = ChokepointHealth(
            chokepoint=signal.geographic.primary_chokepoint.value,
            health_score=0.5 if event.outcome != EventOutcome.DID_NOT_MATERIALIZE else 0.8,
            congestion_level=0.6 if event.outcome != EventOutcome.DID_NOT_MATERIALIZE else 0.2,
            rate_index=event.market_conditions.get("rate_index", 1.0),
            vessels_affected=event.actual_impact.vessels_affected,
            avg_delay_hours=event.actual_impact.actual_delay_days * 24,
        )
        
        reality = RealitySnapshot(
            timestamp=event.event_date,
            chokepoint_health={signal.geographic.primary_chokepoint.value: chokepoint_health},
        )
        
        return CorrelatedIntelligence(
            signal=signal,
            reality=reality,
            correlation_status=status,
            combined_confidence=min(0.95, (event.signal_probability + event.signal_confidence) / 2),
            correlation_factors={
                "signal_probability": event.signal_probability,
                "signal_confidence": event.signal_confidence,
                "historical_accuracy": 0.85,  # Assumed baseline
            },
            correlated_at=event.event_date,
        )
    
    # =========================================================================
    # DECISION EVALUATION
    # =========================================================================
    
    def _evaluate_decision(
        self,
        event: BacktestEvent,
        decision: DecisionObject,
        context: CustomerContext,
    ) -> BacktestResult:
        """
        Evaluate a RISKCAST decision against actual outcomes.
        """
        actual = event.actual_impact
        
        # Extract predictions from decision
        predicted_delay = decision.q3_severity.expected_delay_days
        predicted_cost = decision.q3_severity.total_exposure_usd
        action_cost = decision.q5_action.estimated_cost_usd
        
        # Calculate prediction errors
        delay_error = predicted_delay - actual.actual_delay_days
        cost_error = predicted_cost - actual.actual_cost_usd
        cost_error_pct = (cost_error / actual.actual_cost_usd * 100) if actual.actual_cost_usd > 0 else 0
        
        # Determine if prediction was correct
        event_happened = event.outcome in [
            EventOutcome.MATERIALIZED,
            EventOutcome.PARTIALLY_MATERIALIZED,
        ]
        prediction_was_action = decision.q5_action.action_type not in ["MONITOR", "DO_NOTHING"]
        
        # Build prediction accuracy
        prediction_accuracy = PredictionVsActual(
            predicted_probability=decision.q6_confidence.score,
            actual_occurred=event_happened,
            predicted_delay_days=predicted_delay,
            actual_delay_days=actual.actual_delay_days,
            delay_error_days=delay_error,
            predicted_cost_usd=predicted_cost,
            actual_cost_usd=actual.actual_cost_usd,
            cost_error_usd=cost_error,
            cost_error_pct=cost_error_pct,
        )
        
        # Calculate value analysis
        # If event happened and we recommended action:
        #   - Value protected = actual cost that would have occurred - action cost
        # If event didn't happen and we recommended action:
        #   - Value = negative (we spent money unnecessarily)
        # If event happened and we recommended no action:
        #   - Value = negative (we missed opportunity to protect)
        
        if event_happened and prediction_was_action:
            # Good call - we recommended action and event happened
            loss_if_no_action = actual.actual_cost_usd
            value_protected = max(0, loss_if_no_action - action_cost)
            net_value = value_protected - action_cost
        elif event_happened and not prediction_was_action:
            # Bad call - event happened but we said monitor
            loss_if_no_action = actual.actual_cost_usd
            value_protected = 0
            net_value = -actual.actual_cost_usd  # Full loss
        elif not event_happened and prediction_was_action:
            # False alarm - we recommended action but nothing happened
            loss_if_no_action = 0
            value_protected = 0
            net_value = -action_cost  # Unnecessary spend
        else:
            # Correct non-action - nothing happened, we said monitor
            loss_if_no_action = 0
            value_protected = 0
            net_value = 0
        
        value_analysis = ValueAnalysis(
            action_cost_usd=action_cost,
            loss_if_no_action_usd=loss_if_no_action,
            value_protected_usd=value_protected,
            net_value_usd=net_value,
        )
        
        # Determine quality
        quality, reasons = self._assess_quality(
            event, decision, prediction_accuracy, value_analysis
        )
        
        return BacktestResult(
            result_id=f"bt_{uuid.uuid4().hex[:8]}",
            event_id=event.event_id,
            decision_id=decision.decision_id,
            recommended_action=decision.q5_action.action_type,
            action_deadline=decision.q5_action.deadline,
            estimated_cost_usd=action_cost,
            decision_confidence=decision.q6_confidence.score,
            prediction_accuracy=prediction_accuracy,
            value_analysis=value_analysis,
            quality=quality,
            quality_reasons=reasons,
        )
    
    def _assess_quality(
        self,
        event: BacktestEvent,
        decision: DecisionObject,
        prediction: PredictionVsActual,
        value: ValueAnalysis,
    ) -> tuple[DecisionQuality, list[str]]:
        """
        Assess the quality of a decision.
        
        Returns:
            Tuple of (quality rating, list of reasons)
        """
        reasons = []
        
        # Start with prediction accuracy
        was_correct = prediction.actual_occurred == (
            decision.q5_action.action_type not in ["MONITOR", "DO_NOTHING"]
        )
        
        # Check delay prediction accuracy
        delay_accurate = prediction.delay_error_abs <= 3
        cost_accurate = abs(prediction.cost_error_pct) <= 30
        
        # Check value delivered
        valuable = value.net_value_usd > self._value_threshold
        harmful = value.net_value_usd < -self._value_threshold
        
        # Determine quality
        if was_correct and valuable and delay_accurate and cost_accurate:
            quality = DecisionQuality.EXCELLENT
            reasons.append("Correct prediction with significant value")
            if delay_accurate:
                reasons.append("Delay prediction within 3 days")
            if cost_accurate:
                reasons.append("Cost prediction within 30%")
        
        elif was_correct and (valuable or (delay_accurate or cost_accurate)):
            quality = DecisionQuality.GOOD
            reasons.append("Correct prediction")
            if valuable:
                reasons.append("Positive value delivered")
        
        elif was_correct or abs(value.net_value_usd) < self._value_threshold:
            quality = DecisionQuality.NEUTRAL
            reasons.append("Prediction was close or neutral outcome")
        
        elif harmful:
            if abs(value.net_value_usd) > 5 * self._value_threshold:
                quality = DecisionQuality.HARMFUL
                reasons.append(f"Significant loss: ${abs(value.net_value_usd):,.0f}")
            else:
                quality = DecisionQuality.POOR
                reasons.append(f"Negative value: ${abs(value.net_value_usd):,.0f}")
        
        else:
            quality = DecisionQuality.POOR
            reasons.append("Incorrect prediction")
        
        # Add specific feedback
        if prediction.delay_error_abs > 7:
            reasons.append(f"Delay prediction off by {prediction.delay_error_abs} days")
        if abs(prediction.cost_error_pct) > 50:
            reasons.append(f"Cost prediction off by {abs(prediction.cost_error_pct):.0f}%")
        
        return quality, reasons
    
    # =========================================================================
    # SUMMARY CALCULATION
    # =========================================================================
    
    def _calculate_summary(
        self,
        results: list[BacktestResult],
        events: list[BacktestEvent],
        filters: dict[str, Any],
    ) -> BacktestSummary:
        """
        Calculate summary statistics from backtest results.
        """
        if not results:
            return self._empty_summary(filters)
        
        # Basic counts
        total = len(results)
        correct = sum(1 for r in results if r.was_correct_call)
        
        # Accuracy metrics
        accuracy = correct / total if total > 0 else 0
        
        # Calculate precision/recall
        true_positives = sum(
            1 for r in results
            if r.prediction_accuracy.actual_occurred and
            r.recommended_action not in ["MONITOR", "DO_NOTHING"]
        )
        false_positives = sum(
            1 for r in results
            if not r.prediction_accuracy.actual_occurred and
            r.recommended_action not in ["MONITOR", "DO_NOTHING"]
        )
        false_negatives = sum(
            1 for r in results
            if r.prediction_accuracy.actual_occurred and
            r.recommended_action in ["MONITOR", "DO_NOTHING"]
        )
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # Brier score (lower is better)
        brier_score = sum(
            (r.decision_confidence - (1.0 if r.prediction_accuracy.actual_occurred else 0.0)) ** 2
            for r in results
        ) / total
        
        # Calibration buckets
        calibration_buckets = self._calculate_calibration_buckets()
        
        # Prediction errors
        mean_delay_error = sum(
            abs(r.prediction_accuracy.delay_error_days) for r in results
        ) / total
        mean_cost_error = sum(
            abs(r.prediction_accuracy.cost_error_pct) for r in results
        ) / total
        
        # Value metrics
        total_value = sum(r.value_captured_usd for r in results)
        total_action_cost = sum(r.value_analysis.action_cost_usd for r in results)
        net_value = total_value - total_action_cost
        avg_value = total_value / total if total > 0 else 0
        roi = (total_value - total_action_cost) / total_action_cost if total_action_cost > 0 else 0
        
        # Quality distribution
        quality_dist = defaultdict(int)
        for r in results:
            quality_dist[r.quality.value] += 1
        
        # Category breakdowns
        accuracy_by_chokepoint = self._calculate_category_accuracy(
            results, "chokepoint", events
        )
        accuracy_by_event_type = self._calculate_category_accuracy(
            results, "event_type", events
        )
        accuracy_by_action = self._calculate_action_accuracy(results)
        
        # Identify weak/strong areas
        weak_areas = []
        strong_areas = []
        
        for cat in accuracy_by_chokepoint:
            if cat.accuracy < 0.65:
                weak_areas.append(f"Low accuracy on {cat.category_name} ({cat.accuracy:.0%})")
            elif cat.accuracy > 0.85:
                strong_areas.append(f"High accuracy on {cat.category_name} ({cat.accuracy:.0%})")
        
        if brier_score > 0.25:
            weak_areas.append("Confidence scores need calibration")
        elif brier_score < 0.15:
            strong_areas.append("Well-calibrated confidence scores")
        
        if mean_cost_error > 50:
            weak_areas.append(f"Cost predictions off by average {mean_cost_error:.0f}%")
        
        # Date range
        event_dates = [e.event_date for e in events]
        
        return BacktestSummary(
            summary_id=f"summary_{uuid.uuid4().hex[:8]}",
            total_events=total,
            date_range_start=min(event_dates),
            date_range_end=max(event_dates),
            filters_applied=filters,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            brier_score=brier_score,
            calibration_buckets=calibration_buckets,
            mean_delay_error_days=mean_delay_error,
            mean_cost_error_pct=mean_cost_error,
            total_value_captured_usd=total_value,
            avg_value_per_event_usd=avg_value,
            total_action_cost_usd=total_action_cost,
            net_value_usd=net_value,
            roi=roi,
            quality_distribution=dict(quality_dist),
            accuracy_by_chokepoint=accuracy_by_chokepoint,
            accuracy_by_event_type=accuracy_by_event_type,
            accuracy_by_action_type=accuracy_by_action,
            results=results,
            weak_areas=weak_areas,
            strong_areas=strong_areas,
        )
    
    def _calculate_calibration_buckets(self) -> list[CalibrationBucket]:
        """
        Calculate calibration buckets for Brier score analysis.
        """
        buckets = []
        
        for i in range(self._num_buckets):
            bucket_min = i / self._num_buckets
            bucket_max = (i + 1) / self._num_buckets
            
            predictions = self._predictions_by_bucket.get(i, [])
            
            if not predictions:
                continue
            
            avg_pred = sum(p[0] for p in predictions) / len(predictions)
            actual_freq = sum(1 for p in predictions if p[1]) / len(predictions)
            correct_count = sum(1 for p in predictions if p[1])
            
            buckets.append(CalibrationBucket(
                bucket_min=bucket_min,
                bucket_max=bucket_max,
                predicted_probability=avg_pred,
                actual_frequency=actual_freq,
                sample_count=len(predictions),
                correct_count=correct_count,
            ))
        
        return buckets
    
    def _calculate_category_accuracy(
        self,
        results: list[BacktestResult],
        category_type: str,
        events: list[BacktestEvent],
    ) -> list[AccuracyByCategory]:
        """
        Calculate accuracy broken down by category.
        """
        # Map results to events
        event_map = {e.event_id: e for e in events}
        
        # Group results by category
        category_results: dict[str, list[BacktestResult]] = defaultdict(list)
        
        for r in results:
            event = event_map.get(r.event_id)
            if not event:
                continue
            
            if category_type == "chokepoint":
                cat = event.chokepoint
            elif category_type == "event_type":
                cat = event.category
            else:
                cat = "unknown"
            
            category_results[cat].append(r)
        
        # Calculate accuracy for each category
        categories = []
        
        for cat_name, cat_results in category_results.items():
            total = len(cat_results)
            correct = sum(1 for r in cat_results if r.was_correct_call)
            total_value = sum(r.value_captured_usd for r in cat_results)
            
            quality_dist = defaultdict(int)
            for r in cat_results:
                quality_dist[r.quality.value] += 1
            
            categories.append(AccuracyByCategory(
                category_name=cat_name,
                category_type=category_type,
                total_events=total,
                correct_predictions=correct,
                accuracy=correct / total if total > 0 else 0,
                total_value_captured_usd=total_value,
                avg_value_captured_usd=total_value / total if total > 0 else 0,
                quality_distribution=dict(quality_dist),
            ))
        
        return sorted(categories, key=lambda c: c.accuracy, reverse=True)
    
    def _calculate_action_accuracy(
        self,
        results: list[BacktestResult],
    ) -> list[AccuracyByCategory]:
        """
        Calculate accuracy broken down by recommended action type.
        """
        # Group results by action type
        action_results: dict[str, list[BacktestResult]] = defaultdict(list)
        
        for r in results:
            action_results[r.recommended_action].append(r)
        
        # Calculate accuracy for each action type
        categories = []
        
        for action_name, action_res in action_results.items():
            total = len(action_res)
            correct = sum(1 for r in action_res if r.was_correct_call)
            total_value = sum(r.value_captured_usd for r in action_res)
            
            quality_dist = defaultdict(int)
            for r in action_res:
                quality_dist[r.quality.value] += 1
            
            categories.append(AccuracyByCategory(
                category_name=action_name,
                category_type="action_type",
                total_events=total,
                correct_predictions=correct,
                accuracy=correct / total if total > 0 else 0,
                total_value_captured_usd=total_value,
                avg_value_captured_usd=total_value / total if total > 0 else 0,
                quality_distribution=dict(quality_dist),
            ))
        
        return sorted(categories, key=lambda c: c.accuracy, reverse=True)
    
    def _apply_filters(
        self,
        events: list[BacktestEvent],
        filters: dict[str, Any],
    ) -> list[BacktestEvent]:
        """
        Apply filters to events.
        """
        filtered = events
        
        if "chokepoint" in filters:
            filtered = [e for e in filtered if e.chokepoint == filters["chokepoint"]]
        
        if "category" in filters:
            filtered = [e for e in filtered if e.category == filters["category"]]
        
        if "start_date" in filters:
            start = filters["start_date"]
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            filtered = [e for e in filtered if e.event_date >= start]
        
        if "end_date" in filters:
            end = filters["end_date"]
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            filtered = [e for e in filtered if e.event_date <= end]
        
        if "min_probability" in filters:
            filtered = [e for e in filtered if e.signal_probability >= filters["min_probability"]]
        
        if "outcome" in filters:
            filtered = [e for e in filtered if e.outcome.value == filters["outcome"]]
        
        return filtered
    
    def _empty_summary(self, filters: dict[str, Any]) -> BacktestSummary:
        """
        Create empty summary when no events match.
        """
        return BacktestSummary(
            summary_id=f"summary_empty_{uuid.uuid4().hex[:8]}",
            total_events=0,
            date_range_start=datetime.utcnow(),
            date_range_end=datetime.utcnow(),
            filters_applied=filters,
            accuracy=0,
            precision=0,
            recall=0,
            f1_score=0,
            brier_score=1.0,
            calibration_buckets=[],
            mean_delay_error_days=0,
            mean_cost_error_pct=0,
            total_value_captured_usd=0,
            avg_value_per_event_usd=0,
            total_action_cost_usd=0,
            net_value_usd=0,
            roi=0,
            quality_distribution={},
            accuracy_by_chokepoint=[],
            accuracy_by_event_type=[],
            accuracy_by_action_type=[],
            results=[],
            weak_areas=["No events to analyze"],
            strong_areas=[],
        )


# =============================================================================
# HISTORICAL EVENT LOADER
# =============================================================================


class HistoricalEventLoader:
    """
    Loads and manages historical events for backtesting.
    
    Events can be loaded from:
    - JSON files
    - Database
    - External APIs (for real historical data)
    """
    
    def __init__(self):
        self._events: list[BacktestEvent] = []
    
    def add_event(self, event: BacktestEvent) -> None:
        """Add a single event."""
        self._events.append(event)
    
    def add_events(self, events: list[BacktestEvent]) -> None:
        """Add multiple events."""
        self._events.extend(events)
    
    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        chokepoint: Optional[str] = None,
    ) -> list[BacktestEvent]:
        """
        Get events with optional filtering.
        """
        events = self._events
        
        if start_date:
            events = [e for e in events if e.event_date >= start_date]
        if end_date:
            events = [e for e in events if e.event_date <= end_date]
        if chokepoint:
            events = [e for e in events if e.chokepoint == chokepoint]
        
        return sorted(events, key=lambda e: e.event_date)
    
    def load_from_dict(self, data: dict) -> BacktestEvent:
        """
        Load a single event from dictionary.
        """
        from app.backtest.schemas import ActualImpact
        
        # Parse actual impact
        actual_data = data.get("actual_impact", {})
        actual_impact = ActualImpact(
            event_occurred=actual_data.get("event_occurred", True),
            severity_vs_prediction=actual_data.get("severity_vs_prediction", "as_predicted"),
            actual_delay_days=actual_data.get("actual_delay_days", 0),
            actual_cost_usd=actual_data.get("actual_cost_usd", 0),
            actual_rate_increase_pct=actual_data.get("actual_rate_increase_pct"),
            vessels_affected=actual_data.get("vessels_affected", 0),
            ports_disrupted=actual_data.get("ports_disrupted", []),
            impact_started_at=datetime.fromisoformat(actual_data["impact_started_at"]) if actual_data.get("impact_started_at") else None,
            impact_ended_at=datetime.fromisoformat(actual_data["impact_ended_at"]) if actual_data.get("impact_ended_at") else None,
        )
        
        # Parse event
        event = BacktestEvent(
            event_id=data["event_id"],
            event_name=data["event_name"],
            event_date=datetime.fromisoformat(data["event_date"]),
            chokepoint=data["chokepoint"],
            secondary_chokepoints=data.get("secondary_chokepoints", []),
            category=data["category"],
            signal_probability=data["signal_probability"],
            signal_confidence=data["signal_confidence"],
            detection_lead_time_hours=data.get("detection_lead_time_hours", 48),
            outcome=EventOutcome(data["outcome"]),
            actual_impact=actual_impact,
            market_conditions=data.get("market_conditions", {}),
            notes=data.get("notes"),
            source_url=data.get("source_url"),
        )
        
        return event
    
    def load_from_json(self, json_data: list[dict]) -> list[BacktestEvent]:
        """
        Load events from JSON data.
        """
        events = [self.load_from_dict(d) for d in json_data]
        self.add_events(events)
        return events


# =============================================================================
# SAMPLE EVENTS
# =============================================================================


def get_sample_events() -> list[BacktestEvent]:
    """
    Get sample historical events for testing.
    
    These are based on real supply chain disruptions.
    """
    from app.backtest.schemas import ActualImpact
    
    events = [
        # Red Sea 2024 - Major disruption
        BacktestEvent(
            event_id="RS2024-001",
            event_name="Red Sea Houthi Attacks - January 2024",
            event_date=datetime(2024, 1, 15),
            chokepoint="red_sea",
            secondary_chokepoints=["suez"],
            category="geopolitical",
            signal_probability=0.78,
            signal_confidence=0.85,
            detection_lead_time_hours=72,
            outcome=EventOutcome.MATERIALIZED,
            actual_impact=ActualImpact(
                event_occurred=True,
                severity_vs_prediction="worse_than_predicted",
                actual_delay_days=14,
                actual_cost_usd=85000,
                actual_rate_increase_pct=35,
                vessels_affected=150,
                ports_disrupted=["SAJED", "AEAUH", "EGPSD"],
                impact_started_at=datetime(2024, 1, 18),
                impact_ended_at=None,  # Ongoing
            ),
            market_conditions={"rate_index": 1.35, "congestion_index": 0.7},
            notes="Major carriers announced rerouting via Cape of Good Hope",
            source_url="https://example.com/red-sea-2024",
        ),
        
        # Panama Canal 2023 - Drought
        BacktestEvent(
            event_id="PC2023-001",
            event_name="Panama Canal Drought Restrictions",
            event_date=datetime(2023, 8, 15),
            chokepoint="panama",
            secondary_chokepoints=[],
            category="weather",
            signal_probability=0.65,
            signal_confidence=0.70,
            detection_lead_time_hours=168,  # 7 days
            outcome=EventOutcome.MATERIALIZED,
            actual_impact=ActualImpact(
                event_occurred=True,
                severity_vs_prediction="as_predicted",
                actual_delay_days=7,
                actual_cost_usd=45000,
                actual_rate_increase_pct=25,
                vessels_affected=80,
                ports_disrupted=[],
                impact_started_at=datetime(2023, 8, 20),
                impact_ended_at=datetime(2023, 11, 15),
            ),
            market_conditions={"rate_index": 1.20, "water_level": "low"},
            notes="Drought reduced daily transit capacity from 36 to 24 vessels",
        ),
        
        # False alarm example
        BacktestEvent(
            event_id="RS2023-002",
            event_name="Red Sea Potential Disruption - August 2023",
            event_date=datetime(2023, 8, 1),
            chokepoint="red_sea",
            secondary_chokepoints=[],
            category="geopolitical",
            signal_probability=0.55,
            signal_confidence=0.50,
            detection_lead_time_hours=48,
            outcome=EventOutcome.DID_NOT_MATERIALIZE,
            actual_impact=ActualImpact(
                event_occurred=False,
                severity_vs_prediction="did_not_occur",
                actual_delay_days=0,
                actual_cost_usd=0,
                vessels_affected=0,
            ),
            market_conditions={"rate_index": 1.0},
            notes="Signal detected but situation de-escalated",
        ),
        
        # Suez blockage 2021
        BacktestEvent(
            event_id="SU2021-001",
            event_name="Ever Given Suez Canal Blockage",
            event_date=datetime(2021, 3, 23),
            chokepoint="suez",
            secondary_chokepoints=["red_sea"],
            category="infrastructure",
            signal_probability=0.95,
            signal_confidence=0.98,
            detection_lead_time_hours=2,  # Very short notice
            outcome=EventOutcome.MATERIALIZED,
            actual_impact=ActualImpact(
                event_occurred=True,
                severity_vs_prediction="as_predicted",
                actual_delay_days=6,
                actual_cost_usd=120000,
                actual_rate_increase_pct=40,
                vessels_affected=400,
                ports_disrupted=["EGPSD"],
                impact_started_at=datetime(2021, 3, 23),
                impact_ended_at=datetime(2021, 3, 29),
            ),
            market_conditions={"rate_index": 1.5},
            notes="Complete blockage for 6 days",
        ),
        
        # Malacca minor incident
        BacktestEvent(
            event_id="ML2024-001",
            event_name="Malacca Strait Weather Delays",
            event_date=datetime(2024, 2, 10),
            chokepoint="malacca",
            secondary_chokepoints=[],
            category="weather",
            signal_probability=0.40,
            signal_confidence=0.60,
            detection_lead_time_hours=24,
            outcome=EventOutcome.PARTIALLY_MATERIALIZED,
            actual_impact=ActualImpact(
                event_occurred=True,
                severity_vs_prediction="less_than_predicted",
                actual_delay_days=2,
                actual_cost_usd=8000,
                vessels_affected=20,
            ),
            market_conditions={"rate_index": 1.05},
            notes="Monsoon delays less severe than predicted",
        ),
    ]
    
    return events


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_backtest_framework(
    decision_composer: Optional[DecisionComposer] = None,
    calibration_buckets: int = 10,
) -> BacktestFramework:
    """
    Create a backtest framework instance.
    
    Args:
        decision_composer: Custom decision composer (uses default if None)
        calibration_buckets: Number of buckets for calibration analysis
        
    Returns:
        BacktestFramework instance
    """
    return BacktestFramework(
        decision_composer=decision_composer,
        calibration_buckets=calibration_buckets,
    )


def create_event_loader() -> HistoricalEventLoader:
    """Create a historical event loader."""
    return HistoricalEventLoader()
