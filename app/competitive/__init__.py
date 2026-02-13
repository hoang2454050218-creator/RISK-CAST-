"""
Competitive Intelligence Module.

Provides competitive benchmarking, customer value tracking,
and market positioning analysis.

Components:
- BenchmarkingService: Competitor analysis and comparison
- CustomerValueTracker: Customer ROI and retention metrics
- RISKCAST_MOAT: Documented competitive advantages
"""

from app.competitive.benchmarking import (
    BenchmarkingService,
    CompetitorProfile,
    BenchmarkResult,
    CapabilityLevel,
    FeatureCategory,
    COMPETITORS,
    RISKCAST_MOAT,
    get_benchmarking_service,
)

from app.competitive.customer_value import (
    CustomerValueTracker,
    CustomerValueMetrics,
    CustomerHealthScore,
    CustomerValueJob,
    EngagementLevel,
    RetentionRisk,
    get_value_tracker,
    get_value_job,
)

__all__ = [
    # Benchmarking
    "BenchmarkingService",
    "CompetitorProfile",
    "BenchmarkResult",
    "CapabilityLevel",
    "FeatureCategory",
    "COMPETITORS",
    "RISKCAST_MOAT",
    "get_benchmarking_service",
    
    # Customer Value
    "CustomerValueTracker",
    "CustomerValueMetrics",
    "CustomerHealthScore",
    "CustomerValueJob",
    "EngagementLevel",
    "RetentionRisk",
    "get_value_tracker",
    "get_value_job",
]
