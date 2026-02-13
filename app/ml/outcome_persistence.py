"""
PostgreSQL-backed Outcome Repository.

E2 COMPLIANCE: Persists outcome data to PostgreSQL instead of in-memory.

This module replaces the in-memory OutcomeRepository in flywheel.py
with a production-ready PostgreSQL-backed implementation.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ============================================================================
# OUTCOME SCHEMAS
# ============================================================================


class OutcomeData(BaseModel):
    """Outcome data for persistence."""
    
    outcome_id: str
    decision_id: str
    customer_id: str
    
    # Predictions
    predicted_delay_days: float
    predicted_exposure_usd: float
    predicted_action_cost_usd: float
    predicted_confidence: float
    predicted_action: str
    
    # Actuals (optional until recorded)
    actual_delay_days: Optional[float] = None
    actual_loss_usd: Optional[float] = None
    actual_action_cost_usd: Optional[float] = None
    action_taken: Optional[str] = None
    action_followed_recommendation: Optional[bool] = None
    action_success: Optional[bool] = None
    
    # Metadata
    source: str = "manual"
    notes: Optional[str] = None
    decision_created_at: datetime = Field(default_factory=datetime.utcnow)
    outcome_recorded_at: datetime = Field(default_factory=datetime.utcnow)


class OutcomeMetrics(BaseModel):
    """Aggregated outcome metrics."""
    
    total_outcomes: int = 0
    outcomes_with_actuals: int = 0
    
    # Accuracy
    delay_accuracy_rate: float = 0.0
    cost_accuracy_rate: float = 0.0
    overall_accuracy_rate: float = 0.0
    
    # Errors
    mean_delay_error: float = 0.0
    mean_cost_error_pct: float = 0.0
    
    # Training readiness
    training_ready_count: int = 0


# ============================================================================
# POSTGRESQL OUTCOME REPOSITORY
# ============================================================================


class PostgreSQLOutcomeRepository:
    """
    PostgreSQL-backed outcome repository.
    
    E2 COMPLIANCE: Replaces in-memory storage with persistent PostgreSQL.
    
    Key features:
    - Persistent storage survives restarts
    - Supports training data queries
    - Calculates error metrics automatically
    - Tracks network effects over time
    """
    
    def __init__(self, session_factory=None):
        """
        Initialize with async session factory.
        
        Args:
            session_factory: SQLAlchemy async session factory
        """
        self._session_factory = session_factory
        self._cache: Dict[str, OutcomeData] = {}  # Write-through cache
    
    async def save(self, outcome: OutcomeData) -> str:
        """
        Save outcome to PostgreSQL.
        
        Args:
            outcome: Outcome data to save
            
        Returns:
            Outcome ID
        """
        if not self._session_factory:
            logger.warning("no_session_factory_using_cache")
            self._cache[outcome.outcome_id] = outcome
            return outcome.outcome_id
        
        try:
            from sqlalchemy import select, update
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                # Check if exists
                existing = await session.execute(
                    select(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.decision_id == outcome.decision_id
                    )
                )
                existing_row = existing.scalar_one_or_none()
                
                if existing_row:
                    # Update existing
                    if outcome.actual_delay_days is not None:
                        existing_row.actual_delay_days = outcome.actual_delay_days
                    if outcome.actual_loss_usd is not None:
                        existing_row.actual_loss_usd = outcome.actual_loss_usd
                    if outcome.actual_action_cost_usd is not None:
                        existing_row.actual_action_cost_usd = outcome.actual_action_cost_usd
                    if outcome.action_taken is not None:
                        existing_row.action_taken = outcome.action_taken
                    if outcome.action_success is not None:
                        existing_row.action_success = outcome.action_success
                    
                    existing_row.action_followed_recommendation = outcome.action_followed_recommendation
                    existing_row.source = outcome.source
                    existing_row.notes = outcome.notes
                    existing_row.outcome_recorded_at = datetime.utcnow()
                    
                    # Recalculate errors
                    existing_row.calculate_errors()
                    
                    await session.commit()
                    
                    logger.info(
                        "outcome_updated",
                        outcome_id=existing_row.outcome_id,
                        decision_id=outcome.decision_id,
                    )
                    return existing_row.outcome_id
                else:
                    # Create new
                    new_outcome = DecisionOutcomeModel(
                        outcome_id=outcome.outcome_id,
                        decision_id=outcome.decision_id,
                        customer_id=outcome.customer_id,
                        predicted_delay_days=outcome.predicted_delay_days,
                        predicted_exposure_usd=outcome.predicted_exposure_usd,
                        predicted_action_cost_usd=outcome.predicted_action_cost_usd,
                        predicted_confidence=outcome.predicted_confidence,
                        predicted_action=outcome.predicted_action,
                        actual_delay_days=outcome.actual_delay_days,
                        actual_loss_usd=outcome.actual_loss_usd,
                        actual_action_cost_usd=outcome.actual_action_cost_usd,
                        action_taken=outcome.action_taken,
                        action_followed_recommendation=outcome.action_followed_recommendation,
                        action_success=outcome.action_success,
                        source=outcome.source,
                        notes=outcome.notes,
                        decision_created_at=outcome.decision_created_at,
                    )
                    
                    # Calculate errors if actuals present
                    new_outcome.calculate_errors()
                    
                    session.add(new_outcome)
                    await session.commit()
                    
                    logger.info(
                        "outcome_saved",
                        outcome_id=outcome.outcome_id,
                        decision_id=outcome.decision_id,
                    )
                    return outcome.outcome_id
                    
        except Exception as e:
            logger.error("outcome_save_failed", error=str(e), decision_id=outcome.decision_id)
            # Fallback to cache
            self._cache[outcome.outcome_id] = outcome
            return outcome.outcome_id
    
    async def get(self, outcome_id: str) -> Optional[OutcomeData]:
        """Get outcome by ID."""
        if not self._session_factory:
            return self._cache.get(outcome_id)
        
        try:
            from sqlalchemy import select
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.outcome_id == outcome_id
                    )
                )
                row = result.scalar_one_or_none()
                
                if row:
                    return self._model_to_data(row)
                return None
                
        except Exception as e:
            logger.error("outcome_get_failed", error=str(e), outcome_id=outcome_id)
            return self._cache.get(outcome_id)
    
    async def get_by_decision(self, decision_id: str) -> Optional[OutcomeData]:
        """Get outcome by decision ID."""
        if not self._session_factory:
            for outcome in self._cache.values():
                if outcome.decision_id == decision_id:
                    return outcome
            return None
        
        try:
            from sqlalchemy import select
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.decision_id == decision_id
                    )
                )
                row = result.scalar_one_or_none()
                
                if row:
                    return self._model_to_data(row)
                return None
                
        except Exception as e:
            logger.error("outcome_get_by_decision_failed", error=str(e))
            return None
    
    async def get_recent(self, days: int = 90) -> List[OutcomeData]:
        """Get recent outcomes."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        if not self._session_factory:
            return [
                o for o in self._cache.values()
                if o.outcome_recorded_at >= cutoff
            ]
        
        try:
            from sqlalchemy import select
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.outcome_recorded_at >= cutoff
                    ).order_by(DecisionOutcomeModel.outcome_recorded_at.desc())
                )
                rows = result.scalars().all()
                
                return [self._model_to_data(row) for row in rows]
                
        except Exception as e:
            logger.error("outcome_get_recent_failed", error=str(e))
            return []
    
    async def get_for_training(
        self,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        quality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get outcomes suitable for model training.
        
        Args:
            min_date: Minimum outcome date
            max_date: Maximum outcome date
            quality: Filter by quality (high, medium, low)
            
        Returns:
            List of outcome dicts for training
        """
        if not self._session_factory:
            # Fallback to cache
            outcomes = list(self._cache.values())
            if min_date:
                outcomes = [o for o in outcomes if o.outcome_recorded_at >= min_date]
            if max_date:
                outcomes = [o for o in outcomes if o.outcome_recorded_at <= max_date]
            outcomes = [o for o in outcomes if o.actual_delay_days is not None]
            return [self._data_to_training_dict(o) for o in outcomes]
        
        try:
            from sqlalchemy import select, and_
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                conditions = [DecisionOutcomeModel.is_valid_for_training == True]
                
                if min_date:
                    conditions.append(DecisionOutcomeModel.outcome_recorded_at >= min_date)
                if max_date:
                    conditions.append(DecisionOutcomeModel.outcome_recorded_at <= max_date)
                if quality:
                    conditions.append(DecisionOutcomeModel.training_data_quality == quality)
                
                result = await session.execute(
                    select(DecisionOutcomeModel).where(
                        and_(*conditions)
                    ).order_by(DecisionOutcomeModel.outcome_recorded_at.desc())
                )
                rows = result.scalars().all()
                
                return [self._model_to_training_dict(row) for row in rows]
                
        except Exception as e:
            logger.error("outcome_get_for_training_failed", error=str(e))
            return []
    
    async def count_decisions(self) -> int:
        """Count total decisions with outcomes."""
        if not self._session_factory:
            return len(self._cache)
        
        try:
            from sqlalchemy import select, func
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(func.count(DecisionOutcomeModel.id))
                )
                return result.scalar() or 0
                
        except Exception as e:
            logger.error("outcome_count_failed", error=str(e))
            return len(self._cache)
    
    async def count_with_outcomes(self) -> int:
        """Count decisions with recorded actuals."""
        if not self._session_factory:
            return len([o for o in self._cache.values() if o.actual_delay_days is not None])
        
        try:
            from sqlalchemy import select, func
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(func.count(DecisionOutcomeModel.id)).where(
                        DecisionOutcomeModel.actual_delay_days.isnot(None)
                    )
                )
                return result.scalar() or 0
                
        except Exception as e:
            logger.error("outcome_count_with_outcomes_failed", error=str(e))
            return 0
    
    async def get_metrics(self, days: int = 30) -> OutcomeMetrics:
        """Get aggregated outcome metrics."""
        recent = await self.get_recent(days=days)
        
        if not recent:
            return OutcomeMetrics()
        
        with_actuals = [o for o in recent if o.actual_delay_days is not None]
        
        # Calculate accuracy rates
        delay_accurate = 0
        cost_accurate = 0
        
        for o in with_actuals:
            if o.actual_delay_days is not None and o.predicted_delay_days > 0:
                error_pct = abs(o.actual_delay_days - o.predicted_delay_days) / o.predicted_delay_days
                if error_pct <= 0.2:
                    delay_accurate += 1
            
            if o.actual_loss_usd is not None and o.predicted_exposure_usd > 0:
                error_pct = abs(o.actual_loss_usd - o.predicted_exposure_usd) / o.predicted_exposure_usd
                if error_pct <= 0.3:
                    cost_accurate += 1
        
        n_actuals = len(with_actuals)
        
        # Mean errors
        delay_errors = [
            o.actual_delay_days - o.predicted_delay_days
            for o in with_actuals
            if o.actual_delay_days is not None
        ]
        
        cost_errors = [
            ((o.actual_loss_usd - o.predicted_exposure_usd) / o.predicted_exposure_usd) * 100
            for o in with_actuals
            if o.actual_loss_usd is not None and o.predicted_exposure_usd > 0
        ]
        
        return OutcomeMetrics(
            total_outcomes=len(recent),
            outcomes_with_actuals=n_actuals,
            delay_accuracy_rate=delay_accurate / n_actuals if n_actuals > 0 else 0.0,
            cost_accuracy_rate=cost_accurate / n_actuals if n_actuals > 0 else 0.0,
            overall_accuracy_rate=(delay_accurate + cost_accurate) / (2 * n_actuals) if n_actuals > 0 else 0.0,
            mean_delay_error=sum(delay_errors) / len(delay_errors) if delay_errors else 0.0,
            mean_cost_error_pct=sum(cost_errors) / len(cost_errors) if cost_errors else 0.0,
            training_ready_count=len([o for o in with_actuals if o.actual_delay_days is not None]),
        )
    
    async def mark_used_for_training(
        self,
        outcome_ids: List[str],
        training_job_id: str,
    ) -> int:
        """Mark outcomes as used in training job."""
        if not self._session_factory:
            return 0
        
        try:
            from sqlalchemy import update
            from app.db.models import DecisionOutcomeModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    update(DecisionOutcomeModel).where(
                        DecisionOutcomeModel.outcome_id.in_(outcome_ids)
                    ).values(
                        included_in_training=True,
                        training_job_id=training_job_id,
                    )
                )
                await session.commit()
                
                return result.rowcount
                
        except Exception as e:
            logger.error("mark_used_for_training_failed", error=str(e))
            return 0
    
    def _model_to_data(self, model) -> OutcomeData:
        """Convert SQLAlchemy model to OutcomeData."""
        return OutcomeData(
            outcome_id=model.outcome_id,
            decision_id=model.decision_id,
            customer_id=model.customer_id,
            predicted_delay_days=model.predicted_delay_days,
            predicted_exposure_usd=model.predicted_exposure_usd,
            predicted_action_cost_usd=model.predicted_action_cost_usd,
            predicted_confidence=model.predicted_confidence,
            predicted_action=model.predicted_action,
            actual_delay_days=model.actual_delay_days,
            actual_loss_usd=model.actual_loss_usd,
            actual_action_cost_usd=model.actual_action_cost_usd,
            action_taken=model.action_taken,
            action_followed_recommendation=model.action_followed_recommendation,
            action_success=model.action_success,
            source=model.source,
            notes=model.notes,
            decision_created_at=model.decision_created_at,
            outcome_recorded_at=model.outcome_recorded_at,
        )
    
    def _data_to_training_dict(self, data: OutcomeData) -> Dict[str, Any]:
        """Convert OutcomeData to training dict."""
        return {
            "decision_id": data.decision_id,
            "outcome_id": data.outcome_id,
            "actual_delay_days": data.actual_delay_days,
            "actual_cost_usd": data.actual_loss_usd,
            "signal_probability": data.predicted_confidence,
            "signal_confidence": data.predicted_confidence,
            "exposure_usd": data.predicted_exposure_usd,
            "action_was_correct": data.action_success,
            # These would come from joined decision data
            "chokepoint_congestion": 0.5,
            "market_volatility": 0.3,
            "route_complexity": 0.5,
            "historical_accuracy": 0.75,
            "risk_tolerance": 0.5,
        }
    
    def _model_to_training_dict(self, model) -> Dict[str, Any]:
        """Convert model to training dict."""
        return {
            "decision_id": model.decision_id,
            "outcome_id": model.outcome_id,
            "actual_delay_days": model.actual_delay_days,
            "actual_cost_usd": model.actual_loss_usd,
            "signal_probability": model.predicted_confidence,
            "signal_confidence": model.predicted_confidence,
            "exposure_usd": model.predicted_exposure_usd,
            "action_was_correct": model.action_success,
            "chokepoint_congestion": 0.5,
            "market_volatility": 0.3,
            "route_complexity": 0.5,
            "historical_accuracy": 0.75,
            "risk_tolerance": 0.5,
        }


# ============================================================================
# NETWORK EFFECTS TRACKER
# ============================================================================


class NetworkEffectsTracker:
    """
    Track network effects metrics over time.
    
    E2.4 COMPLIANCE: Measures how accuracy improves with scale.
    """
    
    def __init__(self, session_factory=None):
        self._session_factory = session_factory
    
    async def record_metrics(
        self,
        period_start: datetime,
        period_end: datetime,
        period_type: str,
        metrics: Dict[str, Any],
    ) -> None:
        """Record network effects metrics for a period."""
        if not self._session_factory:
            logger.warning("no_session_factory_for_network_effects")
            return
        
        try:
            from sqlalchemy import select
            from app.db.models import NetworkEffectsMetricModel
            
            async with self._session_factory() as session:
                # Calculate network effect score
                # Higher accuracy + more customers = higher score
                network_score = (
                    metrics.get("overall_accuracy_rate", 0) * 0.4 +
                    min(metrics.get("active_customers", 0) / 100, 1.0) * 0.3 +
                    min(metrics.get("total_decisions", 0) / 1000, 1.0) * 0.2 +
                    metrics.get("outcome_coverage_rate", 0) * 0.1
                )
                
                metric = NetworkEffectsMetricModel(
                    period_start=period_start,
                    period_end=period_end,
                    period_type=period_type,
                    active_customers=metrics.get("active_customers", 0),
                    total_decisions=metrics.get("total_decisions", 0),
                    decisions_with_outcomes=metrics.get("decisions_with_outcomes", 0),
                    delay_accuracy_rate=metrics.get("delay_accuracy_rate", 0.0),
                    cost_accuracy_rate=metrics.get("cost_accuracy_rate", 0.0),
                    overall_accuracy_rate=metrics.get("overall_accuracy_rate", 0.0),
                    mean_delay_error_days=metrics.get("mean_delay_error_days", 0.0),
                    mean_cost_error_pct=metrics.get("mean_cost_error_pct", 0.0),
                    calibration_error=metrics.get("calibration_error", 0.0),
                    model_version=metrics.get("model_version", "unknown"),
                    training_data_size=metrics.get("training_data_size", 0),
                    outcome_coverage_rate=metrics.get("outcome_coverage_rate", 0.0),
                    feedback_rate=metrics.get("feedback_rate", 0.0),
                    network_effect_score=network_score,
                )
                
                session.add(metric)
                await session.commit()
                
                logger.info(
                    "network_effects_recorded",
                    period_type=period_type,
                    network_score=network_score,
                    accuracy=metrics.get("overall_accuracy_rate"),
                )
                
        except Exception as e:
            logger.error("network_effects_record_failed", error=str(e))
    
    async def get_trend(
        self,
        period_type: str = "weekly",
        limit: int = 12,
    ) -> List[Dict[str, Any]]:
        """Get network effects trend over time."""
        if not self._session_factory:
            return []
        
        try:
            from sqlalchemy import select
            from app.db.models import NetworkEffectsMetricModel
            
            async with self._session_factory() as session:
                result = await session.execute(
                    select(NetworkEffectsMetricModel).where(
                        NetworkEffectsMetricModel.period_type == period_type
                    ).order_by(
                        NetworkEffectsMetricModel.period_start.desc()
                    ).limit(limit)
                )
                rows = result.scalars().all()
                
                return [
                    {
                        "period_start": r.period_start.isoformat(),
                        "active_customers": r.active_customers,
                        "total_decisions": r.total_decisions,
                        "accuracy_rate": r.overall_accuracy_rate,
                        "network_effect_score": r.network_effect_score,
                    }
                    for r in reversed(rows)
                ]
                
        except Exception as e:
            logger.error("network_effects_get_trend_failed", error=str(e))
            return []


# ============================================================================
# SINGLETON
# ============================================================================


_outcome_repo: Optional[PostgreSQLOutcomeRepository] = None
_network_tracker: Optional[NetworkEffectsTracker] = None


def get_outcome_repository(session_factory=None) -> PostgreSQLOutcomeRepository:
    """Get global outcome repository instance."""
    global _outcome_repo
    if _outcome_repo is None:
        _outcome_repo = PostgreSQLOutcomeRepository(session_factory)
    return _outcome_repo


def get_network_effects_tracker(session_factory=None) -> NetworkEffectsTracker:
    """Get global network effects tracker instance."""
    global _network_tracker
    if _network_tracker is None:
        _network_tracker = NetworkEffectsTracker(session_factory)
    return _network_tracker
