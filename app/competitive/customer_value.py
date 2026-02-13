"""
Customer Value Tracking Service.

Implements E3 Customer Success requirements:
- Customer value quantification
- Retention metrics
- ROI tracking
- Engagement analytics

E3 COMPLIANCE: Add customer value tracking and retention metrics.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# VALUE METRICS
# ============================================================================


class EngagementLevel(str, Enum):
    """Customer engagement levels."""
    INACTIVE = "inactive"     # No activity in 30+ days
    LOW = "low"               # < 1 decision/week
    MEDIUM = "medium"         # 1-5 decisions/week
    HIGH = "high"             # 5-20 decisions/week
    POWER = "power"           # 20+ decisions/week


class RetentionRisk(str, Enum):
    """Customer retention risk levels."""
    LOW = "low"               # Highly engaged, positive outcomes
    MEDIUM = "medium"         # Moderate engagement or mixed outcomes
    HIGH = "high"             # Declining engagement or poor outcomes
    CRITICAL = "critical"     # At risk of churning


@dataclass
class CustomerValueMetrics:
    """Value metrics for a customer."""
    
    customer_id: str
    timestamp: datetime
    
    # Financial value
    total_value_protected_usd: float = 0.0
    total_cost_savings_usd: float = 0.0
    total_delays_avoided_days: float = 0.0
    estimated_annual_value_usd: float = 0.0
    
    # Engagement
    decisions_received: int = 0
    decisions_acted_on: int = 0
    action_rate: float = 0.0
    avg_response_time_minutes: float = 0.0
    
    # Quality
    decisions_accurate: int = 0
    accuracy_rate: float = 0.0
    avg_confidence_score: float = 0.0
    
    # Retention
    days_since_signup: int = 0
    days_since_last_activity: int = 0
    engagement_level: EngagementLevel = EngagementLevel.LOW
    retention_risk: RetentionRisk = RetentionRisk.MEDIUM
    
    # ROI
    roi_multiple: float = 0.0  # Value delivered / Cost paid


@dataclass 
class CustomerHealthScore:
    """Overall customer health score."""
    
    customer_id: str
    timestamp: datetime
    
    # Component scores (0-100)
    engagement_score: float = 0.0
    value_score: float = 0.0
    accuracy_score: float = 0.0
    retention_score: float = 0.0
    
    # Overall (weighted average)
    overall_score: float = 0.0
    
    # Trend
    score_change_30d: float = 0.0
    trend: str = "stable"  # improving, stable, declining
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)


# ============================================================================
# CUSTOMER VALUE TRACKER
# ============================================================================


class CustomerValueTracker:
    """
    Track and analyze customer value metrics.
    
    Provides insights into customer ROI, engagement, and retention risk.
    """
    
    # Weights for health score calculation
    HEALTH_WEIGHTS = {
        "engagement": 0.25,
        "value": 0.35,
        "accuracy": 0.25,
        "retention": 0.15,
    }
    
    def __init__(self, session_factory=None):
        self._session_factory = session_factory
        self._cache: Dict[str, CustomerValueMetrics] = {}
        self._history: Dict[str, List[CustomerHealthScore]] = {}
    
    async def calculate_metrics(
        self,
        customer_id: str,
        days: int = 90,
    ) -> CustomerValueMetrics:
        """
        Calculate value metrics for a customer.
        
        Args:
            customer_id: Customer identifier
            days: Number of days to analyze
            
        Returns:
            CustomerValueMetrics
        """
        metrics = CustomerValueMetrics(
            customer_id=customer_id,
            timestamp=datetime.utcnow(),
        )
        
        if not self._session_factory:
            logger.warning("no_session_factory_using_mock_data")
            return self._mock_metrics(customer_id)
        
        try:
            from sqlalchemy import select, func, and_
            from app.db.models import DecisionModel, DecisionOutcomeModel, CustomerModel
            
            async with self._session_factory() as session:
                cutoff = datetime.utcnow() - timedelta(days=days)
                
                # Get customer info
                customer_result = await session.execute(
                    select(CustomerModel).where(CustomerModel.customer_id == customer_id)
                )
                customer = customer_result.scalar_one_or_none()
                
                if customer:
                    metrics.days_since_signup = (datetime.utcnow() - customer.created_at).days
                
                # Count decisions
                decision_count = await session.execute(
                    select(func.count(DecisionModel.id)).where(
                        and_(
                            DecisionModel.customer_id == customer_id,
                            DecisionModel.created_at >= cutoff,
                        )
                    )
                )
                metrics.decisions_received = decision_count.scalar() or 0
                
                # Get outcome data
                outcomes = await session.execute(
                    select(DecisionOutcomeModel).where(
                        and_(
                            DecisionOutcomeModel.customer_id == customer_id,
                            DecisionOutcomeModel.created_at >= cutoff,
                        )
                    )
                )
                outcome_list = list(outcomes.scalars().all())
                
                # Calculate value metrics from outcomes
                for outcome in outcome_list:
                    if outcome.actual_cost_usd and outcome.predicted_cost_usd:
                        # Cost savings = predicted impact - actual impact
                        savings = outcome.predicted_cost_usd - outcome.actual_cost_usd
                        if savings > 0:
                            metrics.total_cost_savings_usd += savings
                    
                    if outcome.actual_delay_days and outcome.predicted_delay_days:
                        # Delays avoided = predicted - actual (if positive)
                        avoided = outcome.predicted_delay_days - outcome.actual_delay_days
                        if avoided > 0:
                            metrics.total_delays_avoided_days += avoided
                    
                    if outcome.was_accurate:
                        metrics.decisions_accurate += 1
                
                # Calculate rates
                if metrics.decisions_received > 0:
                    metrics.accuracy_rate = metrics.decisions_accurate / metrics.decisions_received
                
                # Estimate annual value
                days_factor = 365 / max(1, days)
                metrics.estimated_annual_value_usd = metrics.total_cost_savings_usd * days_factor
                
                # Calculate engagement level
                decisions_per_week = metrics.decisions_received / max(1, days / 7)
                if decisions_per_week >= 20:
                    metrics.engagement_level = EngagementLevel.POWER
                elif decisions_per_week >= 5:
                    metrics.engagement_level = EngagementLevel.HIGH
                elif decisions_per_week >= 1:
                    metrics.engagement_level = EngagementLevel.MEDIUM
                elif decisions_per_week > 0:
                    metrics.engagement_level = EngagementLevel.LOW
                else:
                    metrics.engagement_level = EngagementLevel.INACTIVE
                
                # Calculate retention risk
                metrics.retention_risk = self._calculate_retention_risk(metrics)
                
        except Exception as e:
            logger.error("value_metrics_calculation_failed", customer_id=customer_id, error=str(e))
        
        # Cache result
        self._cache[customer_id] = metrics
        
        return metrics
    
    def _mock_metrics(self, customer_id: str) -> CustomerValueMetrics:
        """Generate mock metrics for testing."""
        import random
        
        return CustomerValueMetrics(
            customer_id=customer_id,
            timestamp=datetime.utcnow(),
            total_value_protected_usd=random.uniform(100000, 1000000),
            total_cost_savings_usd=random.uniform(10000, 100000),
            total_delays_avoided_days=random.uniform(5, 30),
            estimated_annual_value_usd=random.uniform(50000, 500000),
            decisions_received=random.randint(10, 100),
            decisions_acted_on=random.randint(5, 50),
            action_rate=random.uniform(0.3, 0.8),
            decisions_accurate=random.randint(8, 80),
            accuracy_rate=random.uniform(0.7, 0.95),
            days_since_signup=random.randint(30, 365),
            engagement_level=random.choice(list(EngagementLevel)),
            retention_risk=random.choice(list(RetentionRisk)),
        )
    
    def _calculate_retention_risk(self, metrics: CustomerValueMetrics) -> RetentionRisk:
        """Calculate retention risk based on metrics."""
        risk_score = 0
        
        # Engagement factor
        if metrics.engagement_level == EngagementLevel.INACTIVE:
            risk_score += 40
        elif metrics.engagement_level == EngagementLevel.LOW:
            risk_score += 20
        
        # Accuracy factor
        if metrics.accuracy_rate < 0.5:
            risk_score += 30
        elif metrics.accuracy_rate < 0.7:
            risk_score += 15
        
        # Value factor
        if metrics.total_cost_savings_usd <= 0:
            risk_score += 20
        
        # Recency factor
        if metrics.days_since_last_activity > 30:
            risk_score += 30
        elif metrics.days_since_last_activity > 14:
            risk_score += 15
        
        # Map to risk level
        if risk_score >= 60:
            return RetentionRisk.CRITICAL
        elif risk_score >= 40:
            return RetentionRisk.HIGH
        elif risk_score >= 20:
            return RetentionRisk.MEDIUM
        else:
            return RetentionRisk.LOW
    
    async def calculate_health_score(
        self,
        customer_id: str,
    ) -> CustomerHealthScore:
        """
        Calculate overall health score for a customer.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            CustomerHealthScore
        """
        metrics = await self.calculate_metrics(customer_id)
        
        # Calculate component scores (0-100)
        engagement_score = self._score_engagement(metrics)
        value_score = self._score_value(metrics)
        accuracy_score = self._score_accuracy(metrics)
        retention_score = self._score_retention(metrics)
        
        # Weighted overall score
        overall = (
            engagement_score * self.HEALTH_WEIGHTS["engagement"] +
            value_score * self.HEALTH_WEIGHTS["value"] +
            accuracy_score * self.HEALTH_WEIGHTS["accuracy"] +
            retention_score * self.HEALTH_WEIGHTS["retention"]
        )
        
        # Calculate trend
        history = self._history.get(customer_id, [])
        score_change = 0.0
        trend = "stable"
        
        if len(history) > 0:
            old_score = history[-1].overall_score
            score_change = overall - old_score
            if score_change > 5:
                trend = "improving"
            elif score_change < -5:
                trend = "declining"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            engagement_score, value_score, accuracy_score, retention_score, metrics
        )
        
        health = CustomerHealthScore(
            customer_id=customer_id,
            timestamp=datetime.utcnow(),
            engagement_score=engagement_score,
            value_score=value_score,
            accuracy_score=accuracy_score,
            retention_score=retention_score,
            overall_score=overall,
            score_change_30d=score_change,
            trend=trend,
            recommendations=recommendations,
        )
        
        # Update history
        if customer_id not in self._history:
            self._history[customer_id] = []
        self._history[customer_id].append(health)
        
        return health
    
    def _score_engagement(self, metrics: CustomerValueMetrics) -> float:
        """Score engagement (0-100)."""
        level_scores = {
            EngagementLevel.INACTIVE: 0,
            EngagementLevel.LOW: 25,
            EngagementLevel.MEDIUM: 50,
            EngagementLevel.HIGH: 75,
            EngagementLevel.POWER: 100,
        }
        return level_scores.get(metrics.engagement_level, 50)
    
    def _score_value(self, metrics: CustomerValueMetrics) -> float:
        """Score value delivery (0-100)."""
        # Scale based on annual value
        if metrics.estimated_annual_value_usd >= 500000:
            return 100
        elif metrics.estimated_annual_value_usd >= 100000:
            return 80
        elif metrics.estimated_annual_value_usd >= 50000:
            return 60
        elif metrics.estimated_annual_value_usd >= 10000:
            return 40
        elif metrics.estimated_annual_value_usd > 0:
            return 20
        else:
            return 0
    
    def _score_accuracy(self, metrics: CustomerValueMetrics) -> float:
        """Score prediction accuracy (0-100)."""
        return min(100, metrics.accuracy_rate * 100)
    
    def _score_retention(self, metrics: CustomerValueMetrics) -> float:
        """Score retention likelihood (0-100)."""
        risk_scores = {
            RetentionRisk.LOW: 100,
            RetentionRisk.MEDIUM: 70,
            RetentionRisk.HIGH: 40,
            RetentionRisk.CRITICAL: 10,
        }
        return risk_scores.get(metrics.retention_risk, 50)
    
    def _generate_recommendations(
        self,
        engagement: float,
        value: float,
        accuracy: float,
        retention: float,
        metrics: CustomerValueMetrics,
    ) -> List[str]:
        """Generate improvement recommendations."""
        recs = []
        
        if engagement < 50:
            recs.append("Increase touchpoints: schedule weekly check-ins")
        
        if value < 50:
            recs.append("Review shipment coverage: may be missing high-value routes")
        
        if accuracy < 70:
            recs.append("Calibrate predictions: accuracy below target threshold")
        
        if retention < 50:
            recs.append("URGENT: Customer at churn risk - executive outreach needed")
        
        if metrics.action_rate < 0.3:
            recs.append("Improve actionability: decisions may not be relevant enough")
        
        return recs
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get summary of entire customer portfolio.
        
        Returns:
            Portfolio-level metrics and insights
        """
        all_metrics = list(self._cache.values())
        
        if not all_metrics:
            return {
                "total_customers": 0,
                "total_value_delivered_usd": 0,
                "avg_health_score": 0,
                "at_risk_customers": 0,
            }
        
        total_value = sum(m.total_cost_savings_usd for m in all_metrics)
        
        # Count by engagement level
        engagement_dist = {}
        for level in EngagementLevel:
            engagement_dist[level.value] = sum(
                1 for m in all_metrics if m.engagement_level == level
            )
        
        # Count by retention risk
        risk_dist = {}
        for risk in RetentionRisk:
            risk_dist[risk.value] = sum(
                1 for m in all_metrics if m.retention_risk == risk
            )
        
        at_risk = risk_dist.get("critical", 0) + risk_dist.get("high", 0)
        
        return {
            "total_customers": len(all_metrics),
            "total_value_delivered_usd": total_value,
            "avg_accuracy_rate": sum(m.accuracy_rate for m in all_metrics) / len(all_metrics),
            "engagement_distribution": engagement_dist,
            "risk_distribution": risk_dist,
            "at_risk_customers": at_risk,
            "power_users": engagement_dist.get("power", 0),
        }


# ============================================================================
# VALUE TRACKING JOB
# ============================================================================


class CustomerValueJob:
    """
    Scheduled job for customer value tracking.
    
    Periodically recalculates metrics and identifies at-risk customers.
    """
    
    def __init__(
        self,
        value_tracker: CustomerValueTracker,
        run_interval_hours: int = 24,
    ):
        self._tracker = value_tracker
        self._interval = timedelta(hours=run_interval_hours)
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the value tracking job."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name="customer_value_tracking"
        )
        logger.info("customer_value_job_started")
    
    async def stop(self):
        """Stop the value tracking job."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("customer_value_job_stopped")
    
    async def _run_loop(self):
        """Main tracking loop."""
        while self._running:
            try:
                await self._run_analysis()
            except Exception as e:
                logger.error("value_tracking_error", error=str(e))
            
            await asyncio.sleep(self._interval.total_seconds())
    
    async def _run_analysis(self):
        """Run full customer analysis."""
        logger.info("customer_value_analysis_started")
        
        # Get customer list (would come from DB in production)
        # For now, use cached customers
        customer_ids = list(self._tracker._cache.keys())
        
        at_risk = []
        for customer_id in customer_ids:
            health = await self._tracker.calculate_health_score(customer_id)
            
            if health.overall_score < 50:
                at_risk.append({
                    "customer_id": customer_id,
                    "score": health.overall_score,
                    "recommendations": health.recommendations,
                })
        
        if at_risk:
            logger.warning(
                "at_risk_customers_identified",
                count=len(at_risk),
                customers=[c["customer_id"] for c in at_risk],
            )
        
        portfolio = await self._tracker.get_portfolio_summary()
        logger.info(
            "customer_value_analysis_completed",
            total_customers=portfolio["total_customers"],
            total_value=portfolio["total_value_delivered_usd"],
            at_risk=portfolio["at_risk_customers"],
        )


# ============================================================================
# SINGLETON
# ============================================================================


_value_tracker: Optional[CustomerValueTracker] = None
_value_job: Optional[CustomerValueJob] = None


def get_value_tracker(session_factory=None) -> CustomerValueTracker:
    """Get global value tracker."""
    global _value_tracker
    if _value_tracker is None:
        _value_tracker = CustomerValueTracker(session_factory)
    return _value_tracker


def get_value_job(session_factory=None) -> CustomerValueJob:
    """Get global value tracking job."""
    global _value_job
    if _value_job is None:
        tracker = get_value_tracker(session_factory)
        _value_job = CustomerValueJob(tracker)
    return _value_job
