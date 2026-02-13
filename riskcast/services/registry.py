"""
Service Registry — Centralized dependency injection for RiskCast V2.

All service instances are created once and shared across the application.
This avoids per-request instantiation overhead and provides a single
point of configuration for all services.

Usage:
    from riskcast.services.registry import get_services
    services = get_services()
    engine = services.risk_engine
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Optional

from riskcast.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class ServiceRegistry:
    """
    Central registry of all V2 service instances.

    Lazy-initializes services on first access to avoid import cycles.
    All services are singletons within the application lifecycle.
    """

    _risk_engine: Optional[object] = field(default=None, repr=False)
    _decision_engine: Optional[object] = field(default=None, repr=False)
    _outcome_recorder: Optional[object] = field(default=None, repr=False)
    _accuracy_calculator: Optional[object] = field(default=None, repr=False)
    _roi_calculator: Optional[object] = field(default=None, repr=False)
    _flywheel_engine: Optional[object] = field(default=None, repr=False)
    _alert_engine: Optional[object] = field(default=None, repr=False)
    _signal_validator: Optional[object] = field(default=None, repr=False)
    _pipeline_health: Optional[object] = field(default=None, repr=False)
    _integrity_checker: Optional[object] = field(default=None, repr=False)
    _traceability_engine: Optional[object] = field(default=None, repr=False)

    @property
    def risk_engine(self):
        """Risk assessment engine (Phase 3)."""
        if self._risk_engine is None:
            from riskcast.engine.risk_engine import RiskEngine
            self._risk_engine = RiskEngine()
            logger.debug("service_initialized", service="RiskEngine")
        return self._risk_engine

    @property
    def decision_engine(self):
        """Decision support engine (Phase 4)."""
        if self._decision_engine is None:
            from riskcast.decisions.engine import DecisionEngine
            self._decision_engine = DecisionEngine()
            logger.debug("service_initialized", service="DecisionEngine")
        return self._decision_engine

    @property
    def outcome_recorder(self):
        """Outcome recorder (Phase 5)."""
        if self._outcome_recorder is None:
            from riskcast.outcomes.recorder import OutcomeRecorder
            self._outcome_recorder = OutcomeRecorder()
            logger.debug("service_initialized", service="OutcomeRecorder")
        return self._outcome_recorder

    @property
    def accuracy_calculator(self):
        """Accuracy calculator (Phase 5)."""
        if self._accuracy_calculator is None:
            from riskcast.outcomes.accuracy import AccuracyCalculator
            self._accuracy_calculator = AccuracyCalculator()
            logger.debug("service_initialized", service="AccuracyCalculator")
        return self._accuracy_calculator

    @property
    def roi_calculator(self):
        """ROI calculator (Phase 5)."""
        if self._roi_calculator is None:
            from riskcast.outcomes.roi import ROICalculator
            self._roi_calculator = ROICalculator()
            logger.debug("service_initialized", service="ROICalculator")
        return self._roi_calculator

    @property
    def flywheel_engine(self):
        """Flywheel learning engine (Phase 5)."""
        if self._flywheel_engine is None:
            from riskcast.outcomes.flywheel import FlywheelEngine
            self._flywheel_engine = FlywheelEngine()
            logger.debug("service_initialized", service="FlywheelEngine")
        return self._flywheel_engine

    @property
    def signal_validator(self):
        """OMEN signal validator (Phase 7)."""
        if self._signal_validator is None:
            from riskcast.pipeline.validator import SignalValidator
            self._signal_validator = SignalValidator()
            logger.debug("service_initialized", service="SignalValidator")
        return self._signal_validator

    @property
    def pipeline_health(self):
        """Pipeline health monitor (Phase 7)."""
        if self._pipeline_health is None:
            from riskcast.pipeline.health import PipelineHealthMonitor
            self._pipeline_health = PipelineHealthMonitor()
            logger.debug("service_initialized", service="PipelineHealthMonitor")
        return self._pipeline_health

    @property
    def integrity_checker(self):
        """Integrity checker (Phase 7)."""
        if self._integrity_checker is None:
            from riskcast.pipeline.integrity import IntegrityChecker
            self._integrity_checker = IntegrityChecker()
            logger.debug("service_initialized", service="IntegrityChecker")
        return self._integrity_checker

    @property
    def traceability_engine(self):
        """Traceability engine (Phase 7)."""
        if self._traceability_engine is None:
            from riskcast.pipeline.traceability import TraceabilityEngine
            self._traceability_engine = TraceabilityEngine()
            logger.debug("service_initialized", service="TraceabilityEngine")
        return self._traceability_engine


# ── Singleton ─────────────────────────────────────────────────────────

_registry: Optional[ServiceRegistry] = None


def get_services() -> ServiceRegistry:
    """Get the global service registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
        logger.info("service_registry_created")
    return _registry


def reset_services() -> None:
    """Reset the registry (for testing)."""
    global _registry
    _registry = None
