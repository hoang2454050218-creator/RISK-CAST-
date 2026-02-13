"""
Testing utilities for RISKCAST.

Provides:
- Chaos engineering tools
- Contract testing helpers
- Load testing utilities
"""

from app.testing.chaos import (
    ChaosConfig,
    ChaosError,
    ChaosMonkey,
    ChaosScenario,
    FaultType,
    ResilienceAssertions,
    chaos_enabled,
    chaos_scope,
    get_chaos_config,
    with_chaos,
)

from app.testing.contracts import (
    Contract,
    ContractBuilder,
    ContractRequest,
    ContractResponse,
    ContractVerifier,
    HttpMethod,
    Interaction,
    RequestMatcher,
    ResponseDefinition,
    VerificationResult,
    create_riskcast_api_contract,
)

from app.testing.load_tests import (
    LoadTestMetrics,
    LoadTestRunner,
    LoadTestScenarios,
    PerformanceAssertions,
    RequestGenerator,
    RequestMetrics,
)

__all__ = [
    # Chaos
    "ChaosConfig",
    "ChaosError",
    "ChaosMonkey",
    "ChaosScenario",
    "FaultType",
    "ResilienceAssertions",
    "chaos_enabled",
    "chaos_scope",
    "get_chaos_config",
    "with_chaos",
    # Contracts
    "Contract",
    "ContractBuilder",
    "ContractRequest",
    "ContractResponse",
    "ContractVerifier",
    "HttpMethod",
    "Interaction",
    "RequestMatcher",
    "ResponseDefinition",
    "VerificationResult",
    "create_riskcast_api_contract",
    # Load tests
    "LoadTestMetrics",
    "LoadTestRunner",
    "LoadTestScenarios",
    "PerformanceAssertions",
    "RequestGenerator",
    "RequestMetrics",
]
