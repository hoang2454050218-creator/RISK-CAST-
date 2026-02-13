"""
Competitive Benchmarking Service.

Implements E1 Competitive Advantage requirements:
- Competitor feature comparison
- Market positioning analysis
- Differentiation tracking
- Benchmarking metrics

E1 COMPLIANCE: Add competitor benchmarking data and comparison.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# FEATURE CATEGORIES
# ============================================================================


class FeatureCategory(str, Enum):
    """Feature categories for benchmarking."""
    SIGNAL_INTELLIGENCE = "signal_intelligence"
    DECISION_QUALITY = "decision_quality"
    PERSONALIZATION = "personalization"
    DELIVERY_CHANNELS = "delivery_channels"
    COVERAGE = "coverage"
    PRICING = "pricing"
    INTEGRATION = "integration"
    COMPLIANCE = "compliance"


class CapabilityLevel(str, Enum):
    """Capability maturity levels."""
    NONE = "none"           # Feature not available
    BASIC = "basic"         # Basic implementation
    STANDARD = "standard"   # Industry standard
    ADVANCED = "advanced"   # Above average
    LEADING = "leading"     # Industry leading
    UNIQUE = "unique"       # Unique to RISKCAST


# ============================================================================
# COMPETITOR PROFILES
# ============================================================================


@dataclass
class CompetitorCapability:
    """Single capability assessment."""
    
    feature: str
    category: FeatureCategory
    competitor_level: CapabilityLevel
    riskcast_level: CapabilityLevel
    notes: str = ""
    riskcast_advantage: bool = False
    
    @property
    def advantage_score(self) -> int:
        """Calculate advantage score (-2 to +2)."""
        levels = [CapabilityLevel.NONE, CapabilityLevel.BASIC, 
                  CapabilityLevel.STANDARD, CapabilityLevel.ADVANCED,
                  CapabilityLevel.LEADING, CapabilityLevel.UNIQUE]
        
        rc_idx = levels.index(self.riskcast_level)
        comp_idx = levels.index(self.competitor_level)
        
        return min(2, max(-2, rc_idx - comp_idx))


@dataclass
class CompetitorProfile:
    """Competitor analysis profile."""
    
    name: str
    description: str
    website: str
    founded: int
    funding_usd: Optional[float] = None
    employee_count: Optional[int] = None
    
    # Market position
    target_market: str = ""
    pricing_model: str = ""
    estimated_customers: Optional[int] = None
    
    # Capabilities
    capabilities: List[CompetitorCapability] = field(default_factory=list)
    
    # Strengths/Weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    @property
    def overall_advantage_score(self) -> float:
        """Calculate overall advantage vs this competitor."""
        if not self.capabilities:
            return 0.0
        return sum(c.advantage_score for c in self.capabilities) / len(self.capabilities)


# ============================================================================
# COMPETITOR DATABASE
# ============================================================================


# Known competitors in supply chain risk/intelligence space
COMPETITORS: Dict[str, CompetitorProfile] = {
    "project44": CompetitorProfile(
        name="Project44",
        description="Real-time visibility platform for shippers and logistics",
        website="project44.com",
        founded=2014,
        funding_usd=1_100_000_000,
        employee_count=1000,
        target_market="Enterprise shippers, 3PLs, carriers",
        pricing_model="SaaS subscription",
        estimated_customers=1000,
        strengths=[
            "Strong carrier network",
            "Real-time visibility",
            "Enterprise integrations",
            "Large funding/scale",
        ],
        weaknesses=[
            "Limited predictive capabilities",
            "Generic alerts (not personalized)",
            "No decision recommendations",
            "Expensive for SMBs",
        ],
        capabilities=[
            CompetitorCapability(
                feature="Real-time tracking",
                category=FeatureCategory.SIGNAL_INTELLIGENCE,
                competitor_level=CapabilityLevel.LEADING,
                riskcast_level=CapabilityLevel.STANDARD,
                notes="Project44 has extensive carrier integration",
            ),
            CompetitorCapability(
                feature="Predictive ETAs",
                category=FeatureCategory.DECISION_QUALITY,
                competitor_level=CapabilityLevel.ADVANCED,
                riskcast_level=CapabilityLevel.ADVANCED,
            ),
            CompetitorCapability(
                feature="Personalized decisions",
                category=FeatureCategory.PERSONALIZATION,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.UNIQUE,
                notes="RISKCAST unique moat - customer-specific recommendations",
                riskcast_advantage=True,
            ),
            CompetitorCapability(
                feature="Cost quantification",
                category=FeatureCategory.DECISION_QUALITY,
                competitor_level=CapabilityLevel.BASIC,
                riskcast_level=CapabilityLevel.LEADING,
                notes="RISKCAST provides $ amounts, competitors give %",
                riskcast_advantage=True,
            ),
            CompetitorCapability(
                feature="WhatsApp delivery",
                category=FeatureCategory.DELIVERY_CHANNELS,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.LEADING,
                riskcast_advantage=True,
            ),
        ],
    ),
    
    "flexport": CompetitorProfile(
        name="Flexport",
        description="Digital freight forwarder with visibility tools",
        website="flexport.com",
        founded=2013,
        funding_usd=2_300_000_000,
        employee_count=3000,
        target_market="Importers, e-commerce",
        pricing_model="Freight + Platform fees",
        estimated_customers=10000,
        strengths=[
            "End-to-end freight services",
            "Strong tech platform",
            "E-commerce focus",
            "Customs expertise",
        ],
        weaknesses=[
            "Tied to Flexport freight",
            "Limited to their ecosystem",
            "No standalone risk product",
            "Recent layoffs/instability",
        ],
        capabilities=[
            CompetitorCapability(
                feature="Real-time tracking",
                category=FeatureCategory.SIGNAL_INTELLIGENCE,
                competitor_level=CapabilityLevel.ADVANCED,
                riskcast_level=CapabilityLevel.STANDARD,
            ),
            CompetitorCapability(
                feature="Personalized decisions",
                category=FeatureCategory.PERSONALIZATION,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.UNIQUE,
                riskcast_advantage=True,
            ),
            CompetitorCapability(
                feature="Carrier agnostic",
                category=FeatureCategory.INTEGRATION,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.LEADING,
                notes="Flexport only works with their freight",
                riskcast_advantage=True,
            ),
        ],
    ),
    
    "everstream": CompetitorProfile(
        name="Everstream Analytics",
        description="Supply chain risk analytics platform",
        website="everstream.ai",
        founded=2018,
        funding_usd=50_000_000,
        employee_count=150,
        target_market="Enterprise procurement, supply chain",
        pricing_model="SaaS subscription",
        estimated_customers=200,
        strengths=[
            "Strong risk analytics",
            "Supplier risk focus",
            "News/event monitoring",
            "ESG tracking",
        ],
        weaknesses=[
            "Complex implementation",
            "Generic risk scores",
            "No actionable recommendations",
            "Limited real-time capabilities",
        ],
        capabilities=[
            CompetitorCapability(
                feature="Risk event monitoring",
                category=FeatureCategory.SIGNAL_INTELLIGENCE,
                competitor_level=CapabilityLevel.LEADING,
                riskcast_level=CapabilityLevel.ADVANCED,
            ),
            CompetitorCapability(
                feature="Actionable recommendations",
                category=FeatureCategory.DECISION_QUALITY,
                competitor_level=CapabilityLevel.BASIC,
                riskcast_level=CapabilityLevel.UNIQUE,
                notes="RISKCAST provides specific actions with costs/deadlines",
                riskcast_advantage=True,
            ),
            CompetitorCapability(
                feature="7 Questions framework",
                category=FeatureCategory.DECISION_QUALITY,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.UNIQUE,
                riskcast_advantage=True,
            ),
        ],
    ),
    
    "resilinc": CompetitorProfile(
        name="Resilinc",
        description="Supply chain mapping and monitoring",
        website="resilinc.com",
        founded=2010,
        funding_usd=60_000_000,
        employee_count=300,
        target_market="Large enterprises, manufacturing",
        pricing_model="SaaS subscription",
        estimated_customers=300,
        strengths=[
            "Deep supplier mapping",
            "Event monitoring",
            "Established brand",
            "Manufacturing focus",
        ],
        weaknesses=[
            "Manual data collection",
            "Slow to update",
            "No predictive AI",
            "Generic recommendations",
        ],
        capabilities=[
            CompetitorCapability(
                feature="Supplier mapping",
                category=FeatureCategory.SIGNAL_INTELLIGENCE,
                competitor_level=CapabilityLevel.LEADING,
                riskcast_level=CapabilityLevel.BASIC,
            ),
            CompetitorCapability(
                feature="Real-time intelligence",
                category=FeatureCategory.SIGNAL_INTELLIGENCE,
                competitor_level=CapabilityLevel.STANDARD,
                riskcast_level=CapabilityLevel.ADVANCED,
                riskcast_advantage=True,
            ),
            CompetitorCapability(
                feature="Personalized decisions",
                category=FeatureCategory.PERSONALIZATION,
                competitor_level=CapabilityLevel.NONE,
                riskcast_level=CapabilityLevel.UNIQUE,
                riskcast_advantage=True,
            ),
        ],
    ),
}


# ============================================================================
# BENCHMARKING SERVICE
# ============================================================================


@dataclass
class BenchmarkResult:
    """Result of benchmarking analysis."""
    
    timestamp: datetime
    competitor: str
    overall_score: float  # -2 to +2
    advantages: List[str]
    disadvantages: List[str]
    opportunities: List[str]
    category_scores: Dict[str, float]


class BenchmarkingService:
    """
    Service for competitive benchmarking.
    
    Provides analysis of RISKCAST positioning vs competitors.
    """
    
    def __init__(self):
        self._competitors = COMPETITORS
        self._last_update = datetime.utcnow()
    
    def get_competitor(self, name: str) -> Optional[CompetitorProfile]:
        """Get competitor profile by name."""
        return self._competitors.get(name.lower())
    
    def list_competitors(self) -> List[str]:
        """List all tracked competitors."""
        return list(self._competitors.keys())
    
    def benchmark_against(self, competitor_name: str) -> Optional[BenchmarkResult]:
        """
        Benchmark RISKCAST against a specific competitor.
        
        Args:
            competitor_name: Name of competitor
            
        Returns:
            BenchmarkResult with detailed comparison
        """
        competitor = self.get_competitor(competitor_name)
        if not competitor:
            return None
        
        # Calculate category scores
        category_scores: Dict[str, List[int]] = {}
        for cap in competitor.capabilities:
            cat = cap.category.value
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(cap.advantage_score)
        
        avg_category_scores = {
            cat: sum(scores) / len(scores) 
            for cat, scores in category_scores.items()
        }
        
        # Identify advantages and disadvantages
        advantages = []
        disadvantages = []
        
        for cap in competitor.capabilities:
            if cap.advantage_score > 0:
                advantages.append(f"{cap.feature}: {cap.notes or 'RISKCAST advantage'}")
            elif cap.advantage_score < 0:
                disadvantages.append(f"{cap.feature}: {cap.notes or 'Competitor advantage'}")
        
        # Identify opportunities
        opportunities = []
        for weakness in competitor.weaknesses:
            opportunities.append(f"Exploit: {weakness}")
        
        return BenchmarkResult(
            timestamp=datetime.utcnow(),
            competitor=competitor.name,
            overall_score=competitor.overall_advantage_score,
            advantages=advantages,
            disadvantages=disadvantages,
            opportunities=opportunities,
            category_scores=avg_category_scores,
        )
    
    def get_competitive_matrix(self) -> Dict[str, Any]:
        """
        Generate competitive feature matrix.
        
        Returns:
            Matrix showing feature coverage across competitors
        """
        # Collect all unique features
        all_features = set()
        for comp in self._competitors.values():
            for cap in comp.capabilities:
                all_features.add(cap.feature)
        
        # Build matrix
        matrix = {
            "features": list(all_features),
            "riskcast": {},
            "competitors": {},
        }
        
        # RISKCAST capabilities
        for comp in self._competitors.values():
            for cap in comp.capabilities:
                if cap.feature not in matrix["riskcast"]:
                    matrix["riskcast"][cap.feature] = cap.riskcast_level.value
        
        # Competitor capabilities
        for name, comp in self._competitors.items():
            matrix["competitors"][name] = {}
            for cap in comp.capabilities:
                matrix["competitors"][name][cap.feature] = cap.competitor_level.value
        
        return matrix
    
    def get_unique_advantages(self) -> List[Dict[str, str]]:
        """
        Get features where RISKCAST has unique advantage.
        
        Returns:
            List of unique RISKCAST advantages
        """
        unique = []
        seen = set()
        
        for comp in self._competitors.values():
            for cap in comp.capabilities:
                if cap.riskcast_advantage and cap.feature not in seen:
                    unique.append({
                        "feature": cap.feature,
                        "category": cap.category.value,
                        "riskcast_level": cap.riskcast_level.value,
                        "description": cap.notes,
                    })
                    seen.add(cap.feature)
        
        return unique
    
    def get_market_positioning(self) -> Dict[str, Any]:
        """
        Get RISKCAST market positioning summary.
        
        Returns:
            Market positioning analysis
        """
        unique_advantages = self.get_unique_advantages()
        
        # Calculate average scores by category
        category_totals: Dict[str, List[float]] = {}
        for comp in self._competitors.values():
            for cap in comp.capabilities:
                cat = cap.category.value
                if cat not in category_totals:
                    category_totals[cat] = []
                category_totals[cat].append(cap.advantage_score)
        
        category_averages = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_totals.items()
        }
        
        # Strongest and weakest categories
        sorted_cats = sorted(category_averages.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "unique_advantages": len(unique_advantages),
            "unique_advantage_features": [a["feature"] for a in unique_advantages],
            "strongest_category": sorted_cats[0] if sorted_cats else None,
            "weakest_category": sorted_cats[-1] if sorted_cats else None,
            "category_scores": category_averages,
            "competitors_analyzed": len(self._competitors),
            "positioning_statement": self._generate_positioning_statement(
                unique_advantages, sorted_cats
            ),
        }
    
    def _generate_positioning_statement(
        self,
        unique_advantages: List[Dict],
        category_scores: List[tuple],
    ) -> str:
        """Generate positioning statement."""
        unique_features = [a["feature"] for a in unique_advantages[:3]]
        
        if not unique_features:
            return "RISKCAST provides competitive supply chain risk intelligence."
        
        strongest = category_scores[0][0] if category_scores else "decision quality"
        
        return (
            f"RISKCAST is the only supply chain intelligence platform offering "
            f"{', '.join(unique_features)}. Our strongest differentiation is in "
            f"{strongest.replace('_', ' ')}, where we lead the market with "
            f"customer-specific, actionable recommendations."
        )


# ============================================================================
# RISKCAST MOAT DEFINITION
# ============================================================================


RISKCAST_MOAT = {
    "core_moat": "Personalized Decision Intelligence",
    "description": (
        "While competitors provide generic risk alerts and scores, RISKCAST "
        "transforms intelligence into customer-specific decisions with exact "
        "costs, deadlines, and action recommendations."
    ),
    "unique_capabilities": [
        {
            "name": "7 Questions Framework",
            "description": "Every decision answers: What, When, How Bad, Why, What to Do, Confidence, If Nothing",
            "competitor_equivalent": None,
        },
        {
            "name": "Dollar Quantification",
            "description": "All impacts in $ amounts, not percentages or scores",
            "competitor_equivalent": None,
        },
        {
            "name": "Deadline-Driven Actions",
            "description": "Specific action deadlines with inaction costs",
            "competitor_equivalent": None,
        },
        {
            "name": "Customer Context Integration",
            "description": "Decisions based on customer's actual shipments, routes, and values",
            "competitor_equivalent": "Generic alerts only",
        },
        {
            "name": "WhatsApp-First Delivery",
            "description": "Instant delivery where decisions makers actually are",
            "competitor_equivalent": "Email and dashboards only",
        },
    ],
    "flywheel_effect": (
        "Every decision improves future decisions through outcome tracking, "
        "calibration updates, and customer feedback integration."
    ),
    "network_effects": (
        "As more customers use RISKCAST on similar routes, prediction accuracy "
        "improves for everyone - creating a defensible data advantage."
    ),
}


# ============================================================================
# SINGLETON
# ============================================================================


_benchmarking_service: Optional[BenchmarkingService] = None


def get_benchmarking_service() -> BenchmarkingService:
    """Get global benchmarking service."""
    global _benchmarking_service
    if _benchmarking_service is None:
        _benchmarking_service = BenchmarkingService()
    return _benchmarking_service
