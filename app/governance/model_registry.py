"""
Model Registry with Model Cards.

Documents all AI/ML models in the system per EU AI Act transparency requirements.

Model Cards follow Google's Model Cards for Model Reporting standard:
- Mitchell et al., "Model Cards for Model Reporting" (2019)
- Extended for EU AI Act compliance

This module provides:
- Standardized model documentation
- Model lifecycle management
- Performance tracking
- Fairness documentation

Addresses audit gap C4.3 (Transparency): +12 points target
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class ModelStatus(str, Enum):
    """Model lifecycle status."""
    DEVELOPMENT = "development"    # In development, not deployed
    STAGING = "staging"           # In testing/staging
    PRODUCTION = "production"     # Live in production
    DEPRECATED = "deprecated"     # Scheduled for retirement
    RETIRED = "retired"          # No longer in use


class ModelType(str, Enum):
    """Type of model/system."""
    RULE_BASED = "rule_based"
    ML_CLASSIFIER = "ml_classifier"
    ML_REGRESSOR = "ml_regressor"
    HYBRID = "hybrid"
    ENSEMBLE = "ensemble"
    HEURISTIC = "heuristic"
    BAYESIAN = "bayesian"


class RiskLevel(str, Enum):
    """Model risk level for governance."""
    HIGH = "high"          # Direct customer impact, high stakes
    MEDIUM = "medium"      # Indirect impact, supports decisions
    LOW = "low"           # Minimal impact, internal only


# ============================================================================
# MODEL CARD SCHEMAS
# ============================================================================


class ModelOwnership(BaseModel):
    """Model ownership information."""
    
    owner: str = Field(description="Primary owner (person or team)")
    team: str = Field(description="Responsible team")
    contact_email: str = Field(description="Contact email for issues")
    stakeholders: List[str] = Field(
        default_factory=list,
        description="Other stakeholders",
    )


class ModelDescription(BaseModel):
    """Model description and intended use."""
    
    description: str = Field(description="What the model does")
    intended_use: str = Field(description="Primary intended use case")
    
    out_of_scope_uses: List[str] = Field(
        default_factory=list,
        description="Uses that are NOT supported",
    )
    
    user_groups: List[str] = Field(
        default_factory=list,
        description="Intended user groups",
    )


class ModelTechnicalDetails(BaseModel):
    """Technical implementation details."""
    
    model_type: ModelType = Field(description="Type of model")
    algorithm: str = Field(description="Algorithm or approach used")
    
    input_features: List[str] = Field(
        default_factory=list,
        description="Input features/data sources",
    )
    
    output_format: str = Field(description="Output format/schema")
    
    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="External dependencies",
    )
    
    # Resources
    compute_requirements: Optional[str] = Field(
        default=None,
        description="Compute requirements",
    )
    
    latency_p50_ms: Optional[float] = Field(
        default=None,
        description="Typical latency (p50)",
    )
    
    latency_p99_ms: Optional[float] = Field(
        default=None,
        description="Worst case latency (p99)",
    )


class TrainingDetails(BaseModel):
    """Training information for ML models."""
    
    training_data: Optional[str] = Field(
        default=None,
        description="Description of training data",
    )
    
    training_data_size: Optional[int] = Field(
        default=None,
        description="Number of training examples",
    )
    
    training_period: Optional[str] = Field(
        default=None,
        description="Time period of training data",
    )
    
    training_date: Optional[datetime] = Field(
        default=None,
        description="When model was trained",
    )
    
    training_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Metrics on training set",
    )
    
    validation_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Metrics on validation set",
    )


class PerformanceMetrics(BaseModel):
    """Model performance metrics."""
    
    # Overall metrics
    metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Overall performance metrics",
    )
    
    # Segmented performance
    metrics_by_segment: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Performance by segment (chokepoint, etc.)",
    )
    
    # Calibration (for probability outputs)
    calibration_ece: Optional[float] = Field(
        default=None,
        description="Expected Calibration Error",
    )
    
    calibration_brier: Optional[float] = Field(
        default=None,
        description="Brier Score",
    )
    
    # Evaluation details
    evaluation_dataset: Optional[str] = Field(
        default=None,
        description="Dataset used for evaluation",
    )
    
    last_evaluation: Optional[datetime] = Field(
        default=None,
        description="Date of last evaluation",
    )


class LimitationsAndRisks(BaseModel):
    """Known limitations and failure modes."""
    
    known_limitations: List[str] = Field(
        default_factory=list,
        description="Known limitations",
    )
    
    failure_modes: List[str] = Field(
        default_factory=list,
        description="Known failure modes and mitigations",
    )
    
    edge_cases: List[str] = Field(
        default_factory=list,
        description="Edge cases where model may fail",
    )
    
    data_quality_requirements: List[str] = Field(
        default_factory=list,
        description="Data quality requirements for good performance",
    )


class FairnessDocumentation(BaseModel):
    """Fairness evaluation documentation."""
    
    evaluated_groups: List[str] = Field(
        default_factory=list,
        description="Groups evaluated for fairness",
    )
    
    fairness_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Fairness metrics by group",
    )
    
    bias_mitigations: List[str] = Field(
        default_factory=list,
        description="Bias mitigation techniques applied",
    )
    
    fairness_constraints: List[str] = Field(
        default_factory=list,
        description="Fairness constraints enforced",
    )
    
    last_fairness_audit: Optional[datetime] = Field(
        default=None,
        description="Date of last fairness audit",
    )


class GovernanceInfo(BaseModel):
    """Governance and approval information."""
    
    risk_level: RiskLevel = Field(description="Model risk classification")
    
    approval_status: str = Field(
        default="PENDING",
        description="Approval status: PENDING, APPROVED, REJECTED",
    )
    
    approved_by: Optional[str] = Field(
        default=None,
        description="Approver name/role",
    )
    
    approval_date: Optional[datetime] = Field(
        default=None,
        description="Approval date",
    )
    
    next_review: Optional[datetime] = Field(
        default=None,
        description="Next scheduled review",
    )
    
    compliance_notes: List[str] = Field(
        default_factory=list,
        description="Compliance-related notes",
    )


class ModelCard(BaseModel):
    """
    Model Card - standardized documentation for each AI/ML model.
    
    Based on Google's Model Cards for Model Reporting, extended for EU AI Act.
    Every model in RISKCAST must have a complete Model Card.
    """
    
    # ========== Identity ==========
    model_id: str = Field(description="Unique model identifier")
    model_name: str = Field(description="Human-readable model name")
    version: str = Field(description="Model version (semver)")
    status: ModelStatus = Field(description="Lifecycle status")
    
    # ========== Ownership ==========
    ownership: ModelOwnership = Field(description="Ownership information")
    
    # ========== Description ==========
    description: ModelDescription = Field(description="Model description")
    
    # ========== Technical Details ==========
    technical: ModelTechnicalDetails = Field(description="Technical details")
    
    # ========== Training (Optional for rule-based) ==========
    training: Optional[TrainingDetails] = Field(
        default=None,
        description="Training details (for ML models)",
    )
    
    # ========== Performance ==========
    performance: PerformanceMetrics = Field(description="Performance metrics")
    
    # ========== Limitations ==========
    limitations: LimitationsAndRisks = Field(description="Limitations and risks")
    
    # ========== Fairness ==========
    fairness: FairnessDocumentation = Field(description="Fairness documentation")
    
    # ========== Governance ==========
    governance: GovernanceInfo = Field(description="Governance information")
    
    # ========== Dates ==========
    created_at: datetime = Field(description="When card was created")
    last_updated: datetime = Field(description="Last update date")
    
    # ========== Changelog ==========
    changelog: List[str] = Field(
        default_factory=list,
        description="Version changelog",
    )
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Is model in production?"""
        return self.status == ModelStatus.PRODUCTION
    
    @computed_field
    @property
    def is_approved(self) -> bool:
        """Is model approved for use?"""
        return self.governance.approval_status == "APPROVED"
    
    @computed_field
    @property
    def needs_review(self) -> bool:
        """Does model need review?"""
        if self.governance.next_review:
            return datetime.utcnow() > self.governance.next_review
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a brief summary of the model card."""
        return {
            "model_id": self.model_id,
            "name": self.model_name,
            "version": self.version,
            "status": self.status.value,
            "risk_level": self.governance.risk_level.value,
            "approval_status": self.governance.approval_status,
            "owner": self.ownership.owner,
            "accuracy": self.performance.metrics.get("accuracy"),
        }


# ============================================================================
# MODEL REGISTRY
# ============================================================================


class ModelRegistry:
    """
    Registry of all AI/ML models in the system.
    
    Provides model inventory, lookup, and lifecycle management.
    """
    
    def __init__(self):
        """Initialize registry with empty model store."""
        self._models: Dict[str, ModelCard] = {}
        self._initialized = False
    
    def register_model(self, card: ModelCard) -> None:
        """
        Register a model with its card.
        
        Args:
            card: Model card to register
        """
        self._models[card.model_id] = card
        logger.info(
            "model_registered",
            model_id=card.model_id,
            version=card.version,
            status=card.status.value,
        )
    
    def get_model(self, model_id: str) -> Optional[ModelCard]:
        """Get a model card by ID."""
        return self._models.get(model_id)
    
    def list_models(
        self,
        status: Optional[ModelStatus] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> List[ModelCard]:
        """
        List models with optional filters.
        
        Args:
            status: Filter by status
            risk_level: Filter by risk level
            
        Returns:
            List of matching model cards
        """
        models = list(self._models.values())
        
        if status:
            models = [m for m in models if m.status == status]
        
        if risk_level:
            models = [m for m in models if m.governance.risk_level == risk_level]
        
        return models
    
    def get_production_models(self) -> List[ModelCard]:
        """Get all production models."""
        return self.list_models(status=ModelStatus.PRODUCTION)
    
    def get_models_needing_review(self) -> List[ModelCard]:
        """Get models that need review."""
        return [m for m in self._models.values() if m.needs_review]
    
    def get_unapproved_models(self) -> List[ModelCard]:
        """Get models pending approval."""
        return [
            m for m in self._models.values()
            if m.governance.approval_status != "APPROVED"
        ]
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of registry contents."""
        models = list(self._models.values())
        
        return {
            "total_models": len(models),
            "by_status": {
                status.value: len([m for m in models if m.status == status])
                for status in ModelStatus
            },
            "by_risk_level": {
                level.value: len([m for m in models if m.governance.risk_level == level])
                for level in RiskLevel
            },
            "production_count": len(self.get_production_models()),
            "needing_review": len(self.get_models_needing_review()),
            "unapproved": len(self.get_unapproved_models()),
        }
    
    def initialize_riskcast_models(self) -> None:
        """Initialize registry with RISKCAST models."""
        if self._initialized:
            return
        
        for card in RISKCAST_MODELS:
            self.register_model(card)
        
        self._initialized = True
        logger.info(
            "model_registry_initialized",
            model_count=len(RISKCAST_MODELS),
        )


# ============================================================================
# PRE-DEFINED RISKCAST MODEL CARDS
# ============================================================================


RISKCAST_MODELS = [
    # ========== RISKCAST Decision Engine ==========
    ModelCard(
        model_id="riskcast-decision-v2",
        model_name="RISKCAST Decision Engine",
        version="2.1.0",
        status=ModelStatus.PRODUCTION,
        ownership=ModelOwnership(
            owner="Decision Team Lead",
            team="RISKCAST Core",
            contact_email="riskcast-core@company.com",
            stakeholders=["Product", "Operations", "Customer Success"],
        ),
        description=ModelDescription(
            description=(
                "6-layer reasoning engine that transforms supply chain signals into "
                "actionable risk mitigation recommendations. Uses Bayesian uncertainty "
                "quantification and multi-layer reasoning (factual, causal, temporal, "
                "counterfactual, strategic, meta) to generate decisions with confidence intervals."
            ),
            intended_use=(
                "Generate actionable risk mitigation recommendations for supply chain "
                "disruptions affecting customer shipments. Provides 7-question decision "
                "framework with confidence intervals and actionable guidance."
            ),
            out_of_scope_uses=[
                "Medical decision making",
                "Financial trading or investment decisions",
                "Personal safety or security decisions",
                "Autonomous execution without human oversight",
                "Decisions involving personal data classification",
            ],
            user_groups=[
                "Supply chain managers",
                "Logistics coordinators",
                "Risk managers",
                "Operations teams",
            ],
        ),
        technical=ModelTechnicalDetails(
            model_type=ModelType.HYBRID,
            algorithm="Multi-layer reasoning with Bayesian uncertainty propagation",
            input_features=[
                "signal_probability (from OMEN)",
                "vessel_positions (from AIS)",
                "customer_shipment_context",
                "market_rate_data",
                "historical_disruption_patterns",
                "chokepoint_status",
            ],
            output_format="DecisionObject with 7 Questions and confidence intervals",
            dependencies=[
                "OMEN Signal Processor",
                "ORACLE Reality Correlator",
                "Uncertainty Module",
                "Calibration System",
            ],
            latency_p50_ms=250,
            latency_p99_ms=1500,
        ),
        performance=PerformanceMetrics(
            metrics={
                "accuracy": 0.72,
                "precision": 0.68,
                "recall": 0.75,
                "f1_score": 0.71,
                "calibration_ece": 0.08,
            },
            metrics_by_segment={
                "red_sea": {"accuracy": 0.78, "precision": 0.75},
                "panama": {"accuracy": 0.70, "precision": 0.65},
                "suez": {"accuracy": 0.68, "precision": 0.62},
                "malacca": {"accuracy": 0.65, "precision": 0.60},
            },
            calibration_ece=0.08,
            calibration_brier=0.18,
            evaluation_dataset="2024-2025 historical decisions with outcomes",
            last_evaluation=datetime(2025, 1, 15),
        ),
        limitations=LimitationsAndRisks(
            known_limitations=[
                "Limited historical data for novel disruption types",
                "Dependent on external signal quality (Polymarket, AIS)",
                "May underestimate tail risks in unprecedented scenarios",
                "Performance degrades with stale data (>1 hour)",
                "Regional coverage limited to major trade routes",
            ],
            failure_modes=[
                "Signal provider outage → Falls back to conservative estimates",
                "Stale data (>1 hour) → Reduces confidence, may escalate to human",
                "Novel disruption type → Flags for human review",
                "Conflicting signals → Requests additional confirmation",
            ],
            edge_cases=[
                "Simultaneous multi-chokepoint disruptions",
                "Cascade failures across supply chain",
                "Rapid market condition changes",
            ],
            data_quality_requirements=[
                "AIS data freshness < 15 minutes",
                "Signal updates within 1 hour",
                "Customer shipment data completeness > 90%",
            ],
        ),
        fairness=FairnessDocumentation(
            evaluated_groups=[
                "customer_size (small, medium, large, enterprise)",
                "chokepoint (red_sea, panama, suez, malacca)",
                "region (APAC, EMEA, Americas)",
                "cargo_type (general, hazmat, perishable, high_value)",
            ],
            fairness_metrics={
                "demographic_parity_customer_size": 0.92,
                "equal_opportunity_chokepoint": 0.88,
                "calibration_by_region": 0.90,
            },
            bias_mitigations=[
                "Customer size normalization in cost/benefit calculations",
                "Chokepoint-specific calibration models",
                "Region-adjusted confidence thresholds",
                "Exposure-weighted recommendations",
            ],
            fairness_constraints=[
                "Accuracy ratio across customer sizes > 0.9",
                "False positive rate difference < 5% across regions",
            ],
            last_fairness_audit=datetime(2025, 1, 1),
        ),
        governance=GovernanceInfo(
            risk_level=RiskLevel.HIGH,
            approval_status="APPROVED",
            approved_by="AI Ethics Board",
            approval_date=datetime(2024, 12, 1),
            next_review=datetime(2025, 4, 1),
            compliance_notes=[
                "EU AI Act: LIMITED RISK - transparency obligations apply",
                "Human oversight required for decisions > $500K",
                "Quarterly fairness audit mandated",
            ],
        ),
        created_at=datetime(2024, 1, 1),
        last_updated=datetime(2025, 2, 1),
        changelog=[
            "2.1.0: Added confidence intervals to all numeric outputs",
            "2.0.0: Implemented 6-layer reasoning architecture",
            "1.5.0: Added uncertainty quantification",
            "1.0.0: Initial release with basic decision support",
        ],
    ),
    
    # ========== OMEN Signal Processor ==========
    ModelCard(
        model_id="omen-signal-processor",
        model_name="OMEN Signal Processor",
        version="1.2.0",
        status=ModelStatus.PRODUCTION,
        ownership=ModelOwnership(
            owner="Signal Team Lead",
            team="RISKCAST Intelligence",
            contact_email="signals@company.com",
            stakeholders=["RISKCAST Core", "Data Engineering"],
        ),
        description=ModelDescription(
            description=(
                "Processes signals from multiple sources (Polymarket, news, AIS anomalies) "
                "and validates them through 4-stage validation pipeline. Outputs calibrated "
                "probability estimates with evidence items."
            ),
            intended_use="Detect and validate supply chain disruption signals",
            out_of_scope_uses=[
                "Financial market predictions",
                "Political event forecasting",
                "Direct customer recommendations",
            ],
            user_groups=["RISKCAST Decision Engine", "Operations monitoring"],
        ),
        technical=ModelTechnicalDetails(
            model_type=ModelType.HYBRID,
            algorithm="Multi-source fusion with Bayesian calibration",
            input_features=[
                "polymarket_probabilities",
                "news_sentiment_scores",
                "ais_anomaly_signals",
                "historical_patterns",
            ],
            output_format="OmenSignal with probability and evidence",
            dependencies=["Polymarket API", "News API", "AIS Provider"],
            latency_p50_ms=150,
            latency_p99_ms=800,
        ),
        performance=PerformanceMetrics(
            metrics={
                "signal_accuracy": 0.78,
                "false_positive_rate": 0.12,
                "calibration_ece": 0.06,
            },
            calibration_ece=0.06,
            last_evaluation=datetime(2025, 1, 10),
        ),
        limitations=LimitationsAndRisks(
            known_limitations=[
                "Dependent on Polymarket market liquidity",
                "News sentiment may lag actual events",
                "Limited coverage for minor chokepoints",
            ],
            failure_modes=[
                "Polymarket outage → Falls back to news-only mode",
                "High latency → Caches recent signals",
            ],
        ),
        fairness=FairnessDocumentation(
            evaluated_groups=["chokepoint", "event_type"],
            fairness_metrics={"accuracy_by_chokepoint": 0.85},
            bias_mitigations=["Chokepoint-specific thresholds"],
        ),
        governance=GovernanceInfo(
            risk_level=RiskLevel.MEDIUM,
            approval_status="APPROVED",
            approved_by="Technical Review Board",
            approval_date=datetime(2024, 11, 1),
            next_review=datetime(2025, 5, 1),
        ),
        created_at=datetime(2024, 6, 1),
        last_updated=datetime(2025, 1, 15),
    ),
    
    # ========== ORACLE Reality Correlator ==========
    ModelCard(
        model_id="oracle-reality-correlator",
        model_name="ORACLE Reality Correlator",
        version="1.1.0",
        status=ModelStatus.PRODUCTION,
        ownership=ModelOwnership(
            owner="Reality Team Lead",
            team="RISKCAST Intelligence",
            contact_email="oracle@company.com",
            stakeholders=["RISKCAST Core", "Operations"],
        ),
        description=ModelDescription(
            description=(
                "Correlates OMEN signals with real-world observations (AIS vessel data, "
                "freight rates, port status) to confirm or refute predictions. Produces "
                "correlation status and combined confidence."
            ),
            intended_use="Validate signals against ground truth data",
            out_of_scope_uses=["Direct decision making", "Customer communication"],
        ),
        technical=ModelTechnicalDetails(
            model_type=ModelType.RULE_BASED,
            algorithm="Evidence-based correlation with threshold logic",
            input_features=[
                "omen_signals",
                "ais_vessel_positions",
                "freight_rate_indices",
                "port_congestion_data",
            ],
            output_format="CorrelatedIntelligence with status",
            dependencies=["AIS Provider", "Freight Rate API", "Port API"],
        ),
        performance=PerformanceMetrics(
            metrics={"correlation_accuracy": 0.85, "false_confirmation_rate": 0.08},
            last_evaluation=datetime(2025, 1, 5),
        ),
        limitations=LimitationsAndRisks(
            known_limitations=[
                "AIS coverage gaps in certain regions",
                "Freight rate updates may lag 24-48 hours",
            ],
        ),
        fairness=FairnessDocumentation(
            evaluated_groups=["region"],
            fairness_metrics={"accuracy_by_region": 0.82},
        ),
        governance=GovernanceInfo(
            risk_level=RiskLevel.MEDIUM,
            approval_status="APPROVED",
            approved_by="Technical Review Board",
            approval_date=datetime(2024, 10, 1),
            next_review=datetime(2025, 4, 1),
        ),
        created_at=datetime(2024, 5, 1),
        last_updated=datetime(2025, 1, 10),
    ),
    
    # ========== Uncertainty Quantification ==========
    ModelCard(
        model_id="uncertainty-bayesian",
        model_name="Bayesian Uncertainty Quantification",
        version="2.0.0",
        status=ModelStatus.PRODUCTION,
        ownership=ModelOwnership(
            owner="Analytics Team Lead",
            team="RISKCAST Analytics",
            contact_email="analytics@company.com",
        ),
        description=ModelDescription(
            description=(
                "Provides full uncertainty quantification for all numeric outputs. "
                "Calculates confidence intervals (80%, 90%, 95%, 99%), VaR, CVaR, "
                "and propagates uncertainty through arithmetic operations."
            ),
            intended_use="Quantify uncertainty in all RISKCAST predictions",
        ),
        technical=ModelTechnicalDetails(
            model_type=ModelType.BAYESIAN,
            algorithm="Monte Carlo propagation with multiple distribution types",
            input_features=["point_estimates", "distribution_parameters"],
            output_format="UncertainValue with CIs and risk metrics",
        ),
        performance=PerformanceMetrics(
            metrics={
                "ci_90_coverage": 0.89,
                "ci_95_coverage": 0.94,
            },
            last_evaluation=datetime(2025, 2, 1),
        ),
        limitations=LimitationsAndRisks(
            known_limitations=[
                "Assumes distributions are well-specified",
                "Monte Carlo may be slow for large ensembles",
            ],
        ),
        fairness=FairnessDocumentation(),
        governance=GovernanceInfo(
            risk_level=RiskLevel.LOW,
            approval_status="APPROVED",
            approved_by="Technical Review Board",
            approval_date=datetime(2025, 1, 15),
            next_review=datetime(2025, 7, 1),
        ),
        created_at=datetime(2024, 9, 1),
        last_updated=datetime(2025, 2, 1),
    ),
    
    # ========== Calibration System ==========
    ModelCard(
        model_id="calibration-system",
        model_name="Prediction Calibration System",
        version="1.0.0",
        status=ModelStatus.PRODUCTION,
        ownership=ModelOwnership(
            owner="Quality Team Lead",
            team="RISKCAST Quality",
            contact_email="quality@company.com",
        ),
        description=ModelDescription(
            description=(
                "Monitors and improves calibration of probability predictions. "
                "Tracks ECE, Brier score, and generates calibration curves. "
                "Alerts on calibration drift."
            ),
            intended_use="Ensure predictions match observed frequencies",
        ),
        technical=ModelTechnicalDetails(
            model_type=ModelType.HEURISTIC,
            algorithm="Isotonic regression calibration with drift detection",
            input_features=["predictions", "outcomes"],
            output_format="CalibrationMetrics and alerts",
        ),
        performance=PerformanceMetrics(
            metrics={"calibration_improvement": 0.15},
            last_evaluation=datetime(2025, 2, 1),
        ),
        limitations=LimitationsAndRisks(
            known_limitations=[
                "Requires sufficient outcome data for reliable estimates",
                "Calibration may lag rapid distribution shifts",
            ],
        ),
        fairness=FairnessDocumentation(),
        governance=GovernanceInfo(
            risk_level=RiskLevel.LOW,
            approval_status="APPROVED",
            approved_by="Technical Review Board",
            approval_date=datetime(2025, 1, 20),
            next_review=datetime(2025, 7, 1),
        ),
        created_at=datetime(2024, 12, 1),
        last_updated=datetime(2025, 2, 1),
    ),
]


# ============================================================================
# SINGLETON REGISTRY
# ============================================================================


_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry (singleton)."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
        _model_registry.initialize_riskcast_models()
    return _model_registry
