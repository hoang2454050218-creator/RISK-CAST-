"""
SLA Definitions and Tracking.

Provides Service Level Agreement definitions, monitoring,
and compliance tracking for RISKCAST services.

Addresses audit gap: B4.1 Performance Benchmarks (+7 points)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, computed_field
import structlog

logger = structlog.get_logger(__name__)


class SLAObjectiveType(str, Enum):
    """Types of SLA objectives."""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ACCURACY = "accuracy"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"


class SLAStatus(str, Enum):
    """SLA compliance status."""
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class SLAObjective(BaseModel):
    """
    Single SLA objective definition.
    
    Example:
        Availability >= 99.9%
        p99 Latency <= 500ms
        Error rate <= 0.1%
    """
    name: str = Field(description="Objective name")
    objective_type: SLAObjectiveType = Field(description="Type of objective")
    target: float = Field(description="Target value")
    unit: str = Field(description="Unit of measurement (%, ms, req/s)")
    comparison: str = Field(default="gte", description="Comparison: gte, lte, eq")
    window_hours: int = Field(default=720, description="Measurement window (30 days default)")
    
    def evaluate(self, current_value: float) -> bool:
        """Check if current value meets objective."""
        if self.comparison == "gte":
            return current_value >= self.target
        elif self.comparison == "lte":
            return current_value <= self.target
        elif self.comparison == "eq":
            return abs(current_value - self.target) < 0.001
        return False
    
    def to_prometheus_rule(self, service: str) -> str:
        """Generate Prometheus alerting rule."""
        if self.objective_type == SLAObjectiveType.AVAILABILITY:
            return f'''
- alert: {service}_SLA_Availability_Breach
  expr: avg_over_time(up{{service="{service}"}}[{self.window_hours}h]) * 100 < {self.target}
  for: 5m
  labels:
    severity: critical
    sla: "true"
  annotations:
    summary: "{service} availability below SLA target of {self.target}%"
'''
        elif self.objective_type == SLAObjectiveType.LATENCY:
            return f'''
- alert: {service}_SLA_Latency_Breach
  expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m])) * 1000 > {self.target}
  for: 5m
  labels:
    severity: warning
    sla: "true"
  annotations:
    summary: "{service} p99 latency above SLA target of {self.target}ms"
'''
        elif self.objective_type == SLAObjectiveType.ERROR_RATE:
            return f'''
- alert: {service}_SLA_ErrorRate_Breach
  expr: rate(http_requests_total{{service="{service}",status=~"5.."}}[5m]) / rate(http_requests_total{{service="{service}"}}[5m]) * 100 > {self.target}
  for: 5m
  labels:
    severity: warning
    sla: "true"
  annotations:
    summary: "{service} error rate above SLA target of {self.target}%"
'''
        return ""


class SLADefinition(BaseModel):
    """
    Complete SLA definition for a service.
    
    Includes multiple objectives and metadata.
    """
    sla_id: str = Field(description="Unique SLA identifier")
    service: str = Field(description="Service name")
    version: str = Field(default="1.0", description="SLA version")
    description: str = Field(default="", description="SLA description")
    objectives: List[SLAObjective] = Field(default_factory=list, description="SLA objectives")
    effective_date: datetime = Field(default_factory=datetime.utcnow)
    review_date: Optional[datetime] = Field(default=None)
    owner: str = Field(default="platform", description="SLA owner team")
    tier: str = Field(default="standard", description="Service tier: standard, premium, enterprise")
    
    @computed_field
    @property
    def objective_count(self) -> int:
        return len(self.objectives)
    
    def generate_prometheus_rules(self) -> str:
        """Generate all Prometheus alerting rules for this SLA."""
        rules = [
            "groups:",
            f"- name: {self.service}_sla_rules",
            "  rules:",
        ]
        
        for objective in self.objectives:
            rule = objective.to_prometheus_rule(self.service)
            if rule:
                rules.append(rule)
        
        return "\n".join(rules)


class SLAMeasurement(BaseModel):
    """Single SLA measurement point."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    objective_name: str
    value: float
    status: SLAStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SLAReport(BaseModel):
    """SLA compliance report for a period."""
    sla_id: str
    service: str
    period_start: datetime
    period_end: datetime
    overall_status: SLAStatus
    objective_results: List[Dict[str, Any]] = Field(default_factory=list)
    uptime_percentage: float = Field(default=100.0)
    incidents: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SLATracker:
    """
    Tracks SLA compliance across services.
    
    Provides:
    - Real-time SLA monitoring
    - Historical compliance data
    - Automated alerting
    - Compliance reporting
    """
    
    def __init__(self):
        self._slas: Dict[str, SLADefinition] = {}
        self._measurements: Dict[str, List[SLAMeasurement]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the tracker with default SLAs."""
        # Register default RISKCAST SLAs
        self.register_sla(DEFAULT_SLA)
        self.register_sla(OMEN_SLA)
        self.register_sla(ORACLE_SLA)
        self.register_sla(RISKCAST_SLA)
        self.register_sla(ALERTER_SLA)
        
        self._initialized = True
        logger.info("sla_tracker_initialized", sla_count=len(self._slas))
    
    def register_sla(self, sla: SLADefinition) -> None:
        """Register an SLA definition."""
        self._slas[sla.sla_id] = sla
        self._measurements[sla.sla_id] = []
        
        logger.info(
            "sla_registered",
            sla_id=sla.sla_id,
            service=sla.service,
            objectives=len(sla.objectives),
        )
    
    def get_sla(self, sla_id: str) -> Optional[SLADefinition]:
        """Get SLA by ID."""
        return self._slas.get(sla_id)
    
    def get_all_slas(self) -> List[SLADefinition]:
        """Get all registered SLAs."""
        return list(self._slas.values())
    
    async def record_measurement(
        self,
        sla_id: str,
        objective_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SLAMeasurement:
        """Record an SLA measurement."""
        sla = self._slas.get(sla_id)
        if not sla:
            raise ValueError(f"Unknown SLA: {sla_id}")
        
        # Find objective
        objective = next(
            (o for o in sla.objectives if o.name == objective_name),
            None,
        )
        if not objective:
            raise ValueError(f"Unknown objective: {objective_name}")
        
        # Evaluate status
        is_compliant = objective.evaluate(value)
        status = SLAStatus.COMPLIANT if is_compliant else SLAStatus.VIOLATED
        
        measurement = SLAMeasurement(
            timestamp=datetime.utcnow(),
            objective_name=objective_name,
            value=value,
            status=status,
            metadata=metadata or {},
        )
        
        self._measurements[sla_id].append(measurement)
        
        # Trim old measurements (keep last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        self._measurements[sla_id] = [
            m for m in self._measurements[sla_id]
            if m.timestamp > cutoff
        ]
        
        # Check for violation
        if status == SLAStatus.VIOLATED:
            await self._handle_violation(sla, objective, measurement)
        
        logger.debug(
            "sla_measurement_recorded",
            sla_id=sla_id,
            objective=objective_name,
            value=value,
            status=status.value,
        )
        
        return measurement
    
    async def get_current_status(
        self,
        sla_id: str,
    ) -> Dict[str, Any]:
        """Get current SLA status."""
        sla = self._slas.get(sla_id)
        if not sla:
            return {"error": f"Unknown SLA: {sla_id}"}
        
        measurements = self._measurements.get(sla_id, [])
        
        # Get latest measurement for each objective
        latest_by_objective: Dict[str, SLAMeasurement] = {}
        for m in measurements:
            if m.objective_name not in latest_by_objective or m.timestamp > latest_by_objective[m.objective_name].timestamp:
                latest_by_objective[m.objective_name] = m
        
        # Determine overall status
        statuses = [m.status for m in latest_by_objective.values()]
        if SLAStatus.VIOLATED in statuses:
            overall = SLAStatus.VIOLATED
        elif SLAStatus.AT_RISK in statuses:
            overall = SLAStatus.AT_RISK
        elif all(s == SLAStatus.COMPLIANT for s in statuses):
            overall = SLAStatus.COMPLIANT
        else:
            overall = SLAStatus.UNKNOWN
        
        return {
            "sla_id": sla_id,
            "service": sla.service,
            "overall_status": overall.value,
            "objectives": {
                name: {
                    "value": m.value,
                    "status": m.status.value,
                    "timestamp": m.timestamp.isoformat(),
                }
                for name, m in latest_by_objective.items()
            },
            "checked_at": datetime.utcnow().isoformat(),
        }
    
    async def generate_report(
        self,
        sla_id: str,
        period_days: int = 30,
    ) -> SLAReport:
        """Generate SLA compliance report."""
        sla = self._slas.get(sla_id)
        if not sla:
            raise ValueError(f"Unknown SLA: {sla_id}")
        
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Filter measurements in period
        measurements = [
            m for m in self._measurements.get(sla_id, [])
            if period_start <= m.timestamp <= period_end
        ]
        
        # Calculate compliance per objective
        objective_results = []
        total_compliant = 0
        total_measurements = 0
        
        for objective in sla.objectives:
            obj_measurements = [
                m for m in measurements
                if m.objective_name == objective.name
            ]
            
            compliant_count = sum(
                1 for m in obj_measurements
                if m.status == SLAStatus.COMPLIANT
            )
            
            total = len(obj_measurements)
            compliance_pct = (compliant_count / total * 100) if total > 0 else 100.0
            
            objective_results.append({
                "objective": objective.name,
                "target": f"{objective.target}{objective.unit}",
                "measurements": total,
                "compliant": compliant_count,
                "compliance_percentage": round(compliance_pct, 2),
                "status": SLAStatus.COMPLIANT.value if compliance_pct >= 99.0 else SLAStatus.VIOLATED.value,
            })
            
            total_compliant += compliant_count
            total_measurements += total
        
        # Calculate uptime
        uptime = (total_compliant / total_measurements * 100) if total_measurements > 0 else 100.0
        
        # Determine overall status
        if uptime >= 99.5:
            overall = SLAStatus.COMPLIANT
        elif uptime >= 95.0:
            overall = SLAStatus.AT_RISK
        else:
            overall = SLAStatus.VIOLATED
        
        return SLAReport(
            sla_id=sla_id,
            service=sla.service,
            period_start=period_start,
            period_end=period_end,
            overall_status=overall,
            objective_results=objective_results,
            uptime_percentage=round(uptime, 2),
            incidents=[],  # Would be populated from incident tracking
            generated_at=datetime.utcnow(),
        )
    
    async def _handle_violation(
        self,
        sla: SLADefinition,
        objective: SLAObjective,
        measurement: SLAMeasurement,
    ) -> None:
        """Handle SLA violation."""
        alert = {
            "sla_id": sla.sla_id,
            "service": sla.service,
            "objective": objective.name,
            "target": objective.target,
            "actual": measurement.value,
            "timestamp": measurement.timestamp.isoformat(),
            "severity": "critical" if objective.objective_type == SLAObjectiveType.AVAILABILITY else "warning",
        }
        
        self._alerts.append(alert)
        
        logger.warning(
            "sla_violation_detected",
            **alert,
        )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for SLA dashboard."""
        dashboard = {
            "slas": [],
            "summary": {
                "total": len(self._slas),
                "compliant": 0,
                "at_risk": 0,
                "violated": 0,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        for sla_id, sla in self._slas.items():
            measurements = self._measurements.get(sla_id, [])
            
            # Count recent violations
            recent = datetime.utcnow() - timedelta(hours=24)
            recent_violations = sum(
                1 for m in measurements
                if m.timestamp > recent and m.status == SLAStatus.VIOLATED
            )
            
            status = (
                SLAStatus.VIOLATED if recent_violations > 5
                else SLAStatus.AT_RISK if recent_violations > 0
                else SLAStatus.COMPLIANT
            )
            
            dashboard["slas"].append({
                "sla_id": sla_id,
                "service": sla.service,
                "status": status.value,
                "recent_violations": recent_violations,
                "objectives": len(sla.objectives),
            })
            
            dashboard["summary"][status.value] += 1
        
        return dashboard


# Default SLA definitions for RISKCAST services

DEFAULT_SLA = SLADefinition(
    sla_id="riskcast-platform",
    service="riskcast-platform",
    version="1.0",
    description="Overall RISKCAST platform SLA",
    objectives=[
        SLAObjective(
            name="availability",
            objective_type=SLAObjectiveType.AVAILABILITY,
            target=99.9,
            unit="%",
            comparison="gte",
        ),
        SLAObjective(
            name="api_latency_p99",
            objective_type=SLAObjectiveType.LATENCY,
            target=500,
            unit="ms",
            comparison="lte",
        ),
        SLAObjective(
            name="error_rate",
            objective_type=SLAObjectiveType.ERROR_RATE,
            target=0.1,
            unit="%",
            comparison="lte",
        ),
    ],
    tier="standard",
    owner="platform",
)

OMEN_SLA = SLADefinition(
    sla_id="omen-signals",
    service="omen",
    version="1.0",
    description="OMEN signal engine SLA",
    objectives=[
        SLAObjective(
            name="signal_freshness",
            objective_type=SLAObjectiveType.LATENCY,
            target=300,  # 5 minutes
            unit="s",
            comparison="lte",
        ),
        SLAObjective(
            name="validation_accuracy",
            objective_type=SLAObjectiveType.ACCURACY,
            target=95.0,
            unit="%",
            comparison="gte",
        ),
    ],
    tier="premium",
    owner="signal-team",
)

ORACLE_SLA = SLADefinition(
    sla_id="oracle-reality",
    service="oracle",
    version="1.0",
    description="ORACLE reality engine SLA",
    objectives=[
        SLAObjective(
            name="data_freshness",
            objective_type=SLAObjectiveType.LATENCY,
            target=60,  # 1 minute
            unit="s",
            comparison="lte",
        ),
        SLAObjective(
            name="correlation_accuracy",
            objective_type=SLAObjectiveType.ACCURACY,
            target=90.0,
            unit="%",
            comparison="gte",
        ),
    ],
    tier="premium",
    owner="data-team",
)

RISKCAST_SLA = SLADefinition(
    sla_id="riskcast-decisions",
    service="riskcast",
    version="1.0",
    description="RISKCAST decision engine SLA",
    objectives=[
        SLAObjective(
            name="decision_latency",
            objective_type=SLAObjectiveType.LATENCY,
            target=2000,  # 2 seconds
            unit="ms",
            comparison="lte",
        ),
        SLAObjective(
            name="decision_quality",
            objective_type=SLAObjectiveType.ACCURACY,
            target=85.0,  # Based on historical outcome tracking
            unit="%",
            comparison="gte",
        ),
    ],
    tier="enterprise",
    owner="decision-team",
)

ALERTER_SLA = SLADefinition(
    sla_id="alerter-delivery",
    service="alerter",
    version="1.0",
    description="Alerter delivery SLA",
    objectives=[
        SLAObjective(
            name="delivery_latency",
            objective_type=SLAObjectiveType.LATENCY,
            target=30,  # 30 seconds
            unit="s",
            comparison="lte",
        ),
        SLAObjective(
            name="delivery_success_rate",
            objective_type=SLAObjectiveType.ACCURACY,
            target=99.5,
            unit="%",
            comparison="gte",
        ),
    ],
    tier="premium",
    owner="alerter-team",
)


# Singleton accessor
_tracker: Optional[SLATracker] = None


async def get_sla_tracker() -> SLATracker:
    """Get or create the SLA tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = SLATracker()
        await _tracker.initialize()
    return _tracker
