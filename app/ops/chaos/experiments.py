"""
Chaos Experiment Implementations.

Concrete implementations of chaos experiments for different failure modes.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio

import structlog
from pydantic import BaseModel, Field

from app.ops.chaos.scheduler import ChaosExperimentType

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class ExperimentStatus(str, Enum):
    """Status of experiment execution."""
    PENDING = "pending"
    INJECTING = "injecting"
    ACTIVE = "active"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# BASE EXPERIMENT
# ============================================================================


class ExperimentRunner(ABC):
    """Abstract base class for chaos experiment runners."""
    
    @property
    @abstractmethod
    def experiment_type(self) -> ChaosExperimentType:
        """Type of experiment this runner handles."""
        pass
    
    @abstractmethod
    async def inject(
        self,
        target: str,
        parameters: Dict[str, Any],
        namespace: str = "riskcast",
    ) -> str:
        """
        Inject chaos.
        
        Args:
            target: Target selector (pod, service, etc.)
            parameters: Experiment-specific parameters
            namespace: Kubernetes namespace
            
        Returns:
            Injection ID for tracking
        """
        pass
    
    @abstractmethod
    async def stop(self, injection_id: str) -> bool:
        """
        Stop chaos injection.
        
        Args:
            injection_id: ID from inject()
            
        Returns:
            True if stopped successfully
        """
        pass
    
    @abstractmethod
    async def status(self, injection_id: str) -> ExperimentStatus:
        """
        Get injection status.
        
        Args:
            injection_id: ID from inject()
            
        Returns:
            Current status
        """
        pass


# ============================================================================
# POD KILL EXPERIMENT
# ============================================================================


class PodKillExperiment(ExperimentRunner):
    """
    Pod kill chaos experiment.
    
    Kills random pods matching a selector to test:
    - Self-healing capabilities
    - Pod disruption budgets
    - Graceful shutdown
    - Session handling
    """
    
    @property
    def experiment_type(self) -> ChaosExperimentType:
        return ChaosExperimentType.POD_KILL
    
    def __init__(self, kubernetes_client: Optional[Any] = None):
        """
        Initialize pod kill experiment.
        
        Args:
            kubernetes_client: Kubernetes client (optional, uses default if not provided)
        """
        self._k8s = kubernetes_client
        self._active_injections: Dict[str, dict] = {}
    
    async def inject(
        self,
        target: str,
        parameters: Dict[str, Any],
        namespace: str = "riskcast",
    ) -> str:
        """
        Inject pod kill chaos.
        
        Parameters:
            count: Number of pods to kill (default: 1)
            interval: Time between kills (default: "60s")
            grace_period: Termination grace period (default: 30s)
        """
        import uuid
        injection_id = f"pk_{uuid.uuid4().hex[:8]}"
        
        count = parameters.get("count", 1)
        interval = parameters.get("interval", "60s")
        grace_period = parameters.get("grace_period", 30)
        
        logger.info(
            "pod_kill_injecting",
            injection_id=injection_id,
            target=target,
            namespace=namespace,
            count=count,
            interval=interval,
        )
        
        # In production, this would:
        # 1. List pods matching selector
        # 2. Randomly select 'count' pods
        # 3. Delete them with grace period
        # 4. Optionally repeat at interval
        
        self._active_injections[injection_id] = {
            "target": target,
            "namespace": namespace,
            "parameters": parameters,
            "status": ExperimentStatus.ACTIVE,
            "started_at": datetime.utcnow(),
            "pods_killed": [],
        }
        
        # Simulate killing pods
        await asyncio.sleep(0.5)
        
        return injection_id
    
    async def stop(self, injection_id: str) -> bool:
        """Stop pod kill chaos (cancels scheduled kills)."""
        if injection_id not in self._active_injections:
            return False
        
        logger.info("pod_kill_stopping", injection_id=injection_id)
        
        self._active_injections[injection_id]["status"] = ExperimentStatus.COMPLETED
        return True
    
    async def status(self, injection_id: str) -> ExperimentStatus:
        """Get pod kill status."""
        injection = self._active_injections.get(injection_id)
        if not injection:
            return ExperimentStatus.FAILED
        return injection["status"]


# ============================================================================
# NETWORK LATENCY EXPERIMENT
# ============================================================================


class NetworkLatencyExperiment(ExperimentRunner):
    """
    Network latency injection experiment.
    
    Adds artificial latency to network connections to test:
    - Timeout handling
    - Circuit breakers
    - Retry logic
    - User experience under slow conditions
    """
    
    @property
    def experiment_type(self) -> ChaosExperimentType:
        return ChaosExperimentType.NETWORK_LATENCY
    
    def __init__(self):
        self._active_injections: Dict[str, dict] = {}
    
    async def inject(
        self,
        target: str,
        parameters: Dict[str, Any],
        namespace: str = "riskcast",
    ) -> str:
        """
        Inject network latency.
        
        Parameters:
            latency_ms: Base latency to add (default: 100ms)
            jitter_ms: Jitter/variance (default: 0ms)
            correlation: Correlation with previous packet (default: 0%)
            direction: "egress" | "ingress" | "both" (default: "egress")
        """
        import uuid
        injection_id = f"nl_{uuid.uuid4().hex[:8]}"
        
        latency_ms = parameters.get("latency_ms", 100)
        jitter_ms = parameters.get("jitter_ms", 0)
        direction = parameters.get("direction", "egress")
        
        logger.info(
            "network_latency_injecting",
            injection_id=injection_id,
            target=target,
            namespace=namespace,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            direction=direction,
        )
        
        # In production, this would use:
        # - tc (traffic control) commands
        # - Chaos Mesh NetworkChaos
        # - Istio fault injection
        
        self._active_injections[injection_id] = {
            "target": target,
            "namespace": namespace,
            "parameters": parameters,
            "status": ExperimentStatus.ACTIVE,
            "started_at": datetime.utcnow(),
        }
        
        await asyncio.sleep(0.2)
        
        return injection_id
    
    async def stop(self, injection_id: str) -> bool:
        """Remove network latency injection."""
        if injection_id not in self._active_injections:
            return False
        
        logger.info("network_latency_stopping", injection_id=injection_id)
        
        # In production, would remove tc rules or delete NetworkChaos CR
        
        self._active_injections[injection_id]["status"] = ExperimentStatus.COMPLETED
        return True
    
    async def status(self, injection_id: str) -> ExperimentStatus:
        """Get network latency status."""
        injection = self._active_injections.get(injection_id)
        if not injection:
            return ExperimentStatus.FAILED
        return injection["status"]


# ============================================================================
# DEPENDENCY FAILURE EXPERIMENT
# ============================================================================


class DependencyFailureExperiment(ExperimentRunner):
    """
    Dependency failure injection experiment.
    
    Simulates failures in downstream dependencies to test:
    - Fallback mechanisms
    - Circuit breakers
    - Graceful degradation
    - Error handling
    """
    
    @property
    def experiment_type(self) -> ChaosExperimentType:
        return ChaosExperimentType.DEPENDENCY_FAILURE
    
    def __init__(self):
        self._active_injections: Dict[str, dict] = {}
    
    async def inject(
        self,
        target: str,
        parameters: Dict[str, Any],
        namespace: str = "riskcast",
    ) -> str:
        """
        Inject dependency failure.
        
        Parameters:
            failure_rate: Percentage of requests to fail (0.0-1.0)
            failure_type: "abort" | "delay" | "error" (default: "abort")
            http_status: HTTP status code for failures (default: 503)
            delay_ms: Delay before failure (default: 0)
        """
        import uuid
        injection_id = f"df_{uuid.uuid4().hex[:8]}"
        
        failure_rate = parameters.get("failure_rate", 0.5)
        failure_type = parameters.get("failure_type", "abort")
        http_status = parameters.get("http_status", 503)
        
        logger.info(
            "dependency_failure_injecting",
            injection_id=injection_id,
            target=target,
            namespace=namespace,
            failure_rate=failure_rate,
            failure_type=failure_type,
            http_status=http_status,
        )
        
        # In production, this would use:
        # - Istio VirtualService fault injection
        # - Service mesh failure injection
        # - Chaos Mesh HTTPChaos
        
        self._active_injections[injection_id] = {
            "target": target,
            "namespace": namespace,
            "parameters": parameters,
            "status": ExperimentStatus.ACTIVE,
            "started_at": datetime.utcnow(),
        }
        
        await asyncio.sleep(0.2)
        
        return injection_id
    
    async def stop(self, injection_id: str) -> bool:
        """Remove dependency failure injection."""
        if injection_id not in self._active_injections:
            return False
        
        logger.info("dependency_failure_stopping", injection_id=injection_id)
        
        self._active_injections[injection_id]["status"] = ExperimentStatus.COMPLETED
        return True
    
    async def status(self, injection_id: str) -> ExperimentStatus:
        """Get dependency failure status."""
        injection = self._active_injections.get(injection_id)
        if not injection:
            return ExperimentStatus.FAILED
        return injection["status"]


# ============================================================================
# CPU STRESS EXPERIMENT
# ============================================================================


class CPUStressExperiment(ExperimentRunner):
    """
    CPU stress experiment.
    
    Stresses CPU to test:
    - Auto-scaling behavior
    - Throttling impact
    - Resource limits
    """
    
    @property
    def experiment_type(self) -> ChaosExperimentType:
        return ChaosExperimentType.CPU_STRESS
    
    def __init__(self):
        self._active_injections: Dict[str, dict] = {}
    
    async def inject(
        self,
        target: str,
        parameters: Dict[str, Any],
        namespace: str = "riskcast",
    ) -> str:
        """
        Inject CPU stress.
        
        Parameters:
            workers: Number of CPU workers (default: 1)
            load: Target CPU load (default: 80)
        """
        import uuid
        injection_id = f"cs_{uuid.uuid4().hex[:8]}"
        
        workers = parameters.get("workers", 1)
        load = parameters.get("load", 80)
        
        logger.info(
            "cpu_stress_injecting",
            injection_id=injection_id,
            target=target,
            workers=workers,
            load=load,
        )
        
        self._active_injections[injection_id] = {
            "target": target,
            "namespace": namespace,
            "parameters": parameters,
            "status": ExperimentStatus.ACTIVE,
            "started_at": datetime.utcnow(),
        }
        
        await asyncio.sleep(0.2)
        
        return injection_id
    
    async def stop(self, injection_id: str) -> bool:
        """Stop CPU stress."""
        if injection_id not in self._active_injections:
            return False
        
        self._active_injections[injection_id]["status"] = ExperimentStatus.COMPLETED
        return True
    
    async def status(self, injection_id: str) -> ExperimentStatus:
        """Get CPU stress status."""
        injection = self._active_injections.get(injection_id)
        if not injection:
            return ExperimentStatus.FAILED
        return injection["status"]


# ============================================================================
# EXPERIMENT REGISTRY
# ============================================================================


class ExperimentRegistry:
    """Registry of available experiment runners."""
    
    def __init__(self):
        self._runners: Dict[ChaosExperimentType, ExperimentRunner] = {}
        
        # Register default runners
        self.register(PodKillExperiment())
        self.register(NetworkLatencyExperiment())
        self.register(DependencyFailureExperiment())
        self.register(CPUStressExperiment())
    
    def register(self, runner: ExperimentRunner) -> None:
        """Register an experiment runner."""
        self._runners[runner.experiment_type] = runner
    
    def get(self, experiment_type: ChaosExperimentType) -> Optional[ExperimentRunner]:
        """Get runner for experiment type."""
        return self._runners.get(experiment_type)
    
    def list_types(self) -> List[ChaosExperimentType]:
        """List registered experiment types."""
        return list(self._runners.keys())


# ============================================================================
# SINGLETON
# ============================================================================


_experiment_runner: Optional[ExperimentRegistry] = None


def get_experiment_runner() -> ExperimentRegistry:
    """Get global experiment registry."""
    global _experiment_runner
    if _experiment_runner is None:
        _experiment_runner = ExperimentRegistry()
    return _experiment_runner
