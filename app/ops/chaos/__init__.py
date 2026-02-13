"""
Chaos Engineering Module.

Provides scheduled chaos experiments to test system resilience.

Addresses audit gap: D2.4 Chaos Engineering (+7 points)
"""

from app.ops.chaos.scheduler import (
    ChaosExperimentType,
    ChaosExperiment,
    ExperimentResult,
    ChaosScheduler,
    get_chaos_scheduler,
    STANDARD_EXPERIMENTS,
)

from app.ops.chaos.experiments import (
    ExperimentRunner,
    ExperimentStatus,
    PodKillExperiment,
    NetworkLatencyExperiment,
    DependencyFailureExperiment,
    get_experiment_runner,
)

__all__ = [
    "ChaosExperimentType",
    "ChaosExperiment",
    "ExperimentResult",
    "ChaosScheduler",
    "get_chaos_scheduler",
    "STANDARD_EXPERIMENTS",
    "ExperimentRunner",
    "ExperimentStatus",
    "PodKillExperiment",
    "NetworkLatencyExperiment",
    "DependencyFailureExperiment",
    "get_experiment_runner",
]
