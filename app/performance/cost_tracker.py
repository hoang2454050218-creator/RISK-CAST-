"""
Cost Tracking and Optimization.

Tracks infrastructure and operational costs per customer,
service, and resource for cost optimization.

Addresses audit gap: B4.4 Cost Optimization (+8 points)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from collections import defaultdict

from pydantic import BaseModel, Field, computed_field
import structlog

logger = structlog.get_logger(__name__)


class CostCategory(str, Enum):
    """Cost categories for tracking."""
    COMPUTE = "compute"
    STORAGE = "storage"
    NETWORK = "network"
    API_CALLS = "api_calls"
    DATABASE = "database"
    MESSAGING = "messaging"
    MONITORING = "monitoring"
    THIRD_PARTY = "third_party"
    OTHER = "other"


class CostAllocation(str, Enum):
    """Cost allocation methods."""
    DIRECT = "direct"           # Directly attributable to customer
    SHARED = "shared"           # Shared infrastructure
    OVERHEAD = "overhead"       # Platform overhead


class CostRecord(BaseModel):
    """
    Single cost record entry.
    
    Tracks a specific cost incurred at a point in time.
    """
    record_id: str = Field(description="Unique record identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    category: CostCategory = Field(description="Cost category")
    amount_usd: float = Field(ge=0, description="Cost in USD")
    service: str = Field(description="Service that incurred cost")
    customer_id: Optional[str] = Field(default=None, description="Customer if attributable")
    allocation: CostAllocation = Field(default=CostAllocation.SHARED)
    resource: str = Field(default="", description="Specific resource")
    units: float = Field(default=1.0, description="Number of units consumed")
    unit_type: str = Field(default="count", description="Type of unit")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CostBudget(BaseModel):
    """Budget definition for cost tracking."""
    budget_id: str
    name: str
    category: Optional[CostCategory] = None
    service: Optional[str] = None
    customer_id: Optional[str] = None
    monthly_limit_usd: float = Field(ge=0)
    alert_threshold_pct: float = Field(default=80.0, ge=0, le=100)
    hard_limit: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CostAlert(BaseModel):
    """Cost alert when thresholds are exceeded."""
    alert_id: str
    budget_id: str
    alert_type: str  # "threshold", "anomaly", "forecast"
    severity: str    # "warning", "critical"
    message: str
    current_amount_usd: float
    limit_usd: float
    percentage: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostReport(BaseModel):
    """
    Cost report for a time period.
    
    Aggregates costs by various dimensions.
    """
    report_id: str
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    by_category: Dict[str, float] = Field(default_factory=dict)
    by_service: Dict[str, float] = Field(default_factory=dict)
    by_customer: Dict[str, float] = Field(default_factory=dict)
    by_allocation: Dict[str, float] = Field(default_factory=dict)
    daily_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    top_resources: List[Dict[str, Any]] = Field(default_factory=list)
    efficiency_metrics: Dict[str, float] = Field(default_factory=dict)
    alerts: List[CostAlert] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def cost_per_day(self) -> float:
        """Average cost per day."""
        days = max(1, (self.period_end - self.period_start).days)
        return round(self.total_cost_usd / days, 2)


class CostTracker:
    """
    Tracks and analyzes infrastructure costs.
    
    Provides:
    - Per-customer cost attribution
    - Per-service cost breakdown
    - Budget management and alerts
    - Anomaly detection
    - Cost forecasting
    """
    
    def __init__(self):
        self._records: List[CostRecord] = []
        self._budgets: Dict[str, CostBudget] = {}
        self._alerts: List[CostAlert] = []
        self._cost_rates: Dict[str, float] = {}
        self._initialized = False
    
    async def initialize(
        self,
        cost_rates: Optional[Dict[str, float]] = None,
    ) -> None:
        """Initialize with cost rates."""
        # Default AWS-like cost rates
        self._cost_rates = cost_rates or {
            "compute_cpu_hour": 0.04,
            "compute_memory_gb_hour": 0.005,
            "storage_gb_month": 0.023,
            "network_gb": 0.09,
            "api_request": 0.0000004,
            "database_query": 0.0000001,
            "message_publish": 0.0000001,
            "message_delivery": 0.00000001,
        }
        
        self._initialized = True
        logger.info("cost_tracker_initialized", rates=len(self._cost_rates))
    
    async def record_cost(
        self,
        category: CostCategory,
        amount_usd: float,
        service: str,
        customer_id: Optional[str] = None,
        resource: str = "",
        units: float = 1.0,
        unit_type: str = "count",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CostRecord:
        """Record a cost entry."""
        record = CostRecord(
            record_id=f"cost_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            timestamp=datetime.utcnow(),
            category=category,
            amount_usd=amount_usd,
            service=service,
            customer_id=customer_id,
            allocation=CostAllocation.DIRECT if customer_id else CostAllocation.SHARED,
            resource=resource,
            units=units,
            unit_type=unit_type,
            metadata=metadata or {},
        )
        
        self._records.append(record)
        
        # Trim old records (keep 90 days)
        cutoff = datetime.utcnow() - timedelta(days=90)
        self._records = [r for r in self._records if r.timestamp > cutoff]
        
        # Check budgets
        await self._check_budgets(record)
        
        logger.debug(
            "cost_recorded",
            category=category.value,
            amount_usd=amount_usd,
            service=service,
            customer_id=customer_id,
        )
        
        return record
    
    async def record_usage(
        self,
        usage_type: str,
        units: float,
        service: str,
        customer_id: Optional[str] = None,
        resource: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CostRecord:
        """Record usage and calculate cost automatically."""
        rate = self._cost_rates.get(usage_type, 0.0)
        amount = units * rate
        
        # Map usage type to category
        category_map = {
            "compute_cpu_hour": CostCategory.COMPUTE,
            "compute_memory_gb_hour": CostCategory.COMPUTE,
            "storage_gb_month": CostCategory.STORAGE,
            "network_gb": CostCategory.NETWORK,
            "api_request": CostCategory.API_CALLS,
            "database_query": CostCategory.DATABASE,
            "message_publish": CostCategory.MESSAGING,
            "message_delivery": CostCategory.MESSAGING,
        }
        
        category = category_map.get(usage_type, CostCategory.OTHER)
        
        return await self.record_cost(
            category=category,
            amount_usd=amount,
            service=service,
            customer_id=customer_id,
            resource=resource,
            units=units,
            unit_type=usage_type,
            metadata=metadata,
        )
    
    def set_budget(
        self,
        budget_id: str,
        name: str,
        monthly_limit_usd: float,
        category: Optional[CostCategory] = None,
        service: Optional[str] = None,
        customer_id: Optional[str] = None,
        alert_threshold_pct: float = 80.0,
        hard_limit: bool = False,
    ) -> CostBudget:
        """Set or update a budget."""
        budget = CostBudget(
            budget_id=budget_id,
            name=name,
            category=category,
            service=service,
            customer_id=customer_id,
            monthly_limit_usd=monthly_limit_usd,
            alert_threshold_pct=alert_threshold_pct,
            hard_limit=hard_limit,
        )
        
        self._budgets[budget_id] = budget
        
        logger.info(
            "budget_set",
            budget_id=budget_id,
            limit_usd=monthly_limit_usd,
        )
        
        return budget
    
    async def get_customer_costs(
        self,
        customer_id: str,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """Get cost breakdown for a specific customer."""
        period_start = datetime.utcnow() - timedelta(days=period_days)
        
        # Filter records for customer
        customer_records = [
            r for r in self._records
            if r.customer_id == customer_id and r.timestamp > period_start
        ]
        
        # Add allocated shared costs
        shared_records = [
            r for r in self._records
            if r.allocation == CostAllocation.SHARED and r.timestamp > period_start
        ]
        
        # Simple allocation: divide shared by number of active customers
        active_customers = len(set(r.customer_id for r in self._records if r.customer_id))
        shared_allocation = sum(r.amount_usd for r in shared_records) / max(1, active_customers)
        
        direct_cost = sum(r.amount_usd for r in customer_records)
        
        # Group by category
        by_category = defaultdict(float)
        for r in customer_records:
            by_category[r.category.value] += r.amount_usd
        
        # Group by service
        by_service = defaultdict(float)
        for r in customer_records:
            by_service[r.service] += r.amount_usd
        
        return {
            "customer_id": customer_id,
            "period_days": period_days,
            "direct_cost_usd": round(direct_cost, 4),
            "allocated_shared_cost_usd": round(shared_allocation, 4),
            "total_cost_usd": round(direct_cost + shared_allocation, 4),
            "by_category": dict(by_category),
            "by_service": dict(by_service),
            "record_count": len(customer_records),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    async def get_service_costs(
        self,
        service: str,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """Get cost breakdown for a specific service."""
        period_start = datetime.utcnow() - timedelta(days=period_days)
        
        # Filter records for service
        service_records = [
            r for r in self._records
            if r.service == service and r.timestamp > period_start
        ]
        
        total_cost = sum(r.amount_usd for r in service_records)
        
        # Group by category
        by_category = defaultdict(float)
        for r in service_records:
            by_category[r.category.value] += r.amount_usd
        
        # Group by customer
        by_customer = defaultdict(float)
        for r in service_records:
            key = r.customer_id or "shared"
            by_customer[key] += r.amount_usd
        
        return {
            "service": service,
            "period_days": period_days,
            "total_cost_usd": round(total_cost, 4),
            "by_category": dict(by_category),
            "by_customer": dict(by_customer),
            "record_count": len(service_records),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    async def generate_report(
        self,
        period_days: int = 30,
    ) -> CostReport:
        """Generate comprehensive cost report."""
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Filter records in period
        records = [
            r for r in self._records
            if period_start <= r.timestamp <= period_end
        ]
        
        total_cost = sum(r.amount_usd for r in records)
        
        # Aggregate by dimensions
        by_category = defaultdict(float)
        by_service = defaultdict(float)
        by_customer = defaultdict(float)
        by_allocation = defaultdict(float)
        by_day = defaultdict(float)
        by_resource = defaultdict(float)
        
        for r in records:
            by_category[r.category.value] += r.amount_usd
            by_service[r.service] += r.amount_usd
            by_customer[r.customer_id or "shared"] += r.amount_usd
            by_allocation[r.allocation.value] += r.amount_usd
            day_key = r.timestamp.strftime("%Y-%m-%d")
            by_day[day_key] += r.amount_usd
            if r.resource:
                by_resource[r.resource] += r.amount_usd
        
        # Daily breakdown
        daily_breakdown = [
            {"date": date, "cost_usd": round(cost, 4)}
            for date, cost in sorted(by_day.items())
        ]
        
        # Top resources by cost
        top_resources = sorted(
            [{"resource": r, "cost_usd": round(c, 4)} for r, c in by_resource.items()],
            key=lambda x: x["cost_usd"],
            reverse=True,
        )[:10]
        
        # Calculate efficiency metrics
        efficiency_metrics = await self._calculate_efficiency(records)
        
        # Get recent alerts
        recent_alerts = [
            a for a in self._alerts
            if a.timestamp > period_start
        ]
        
        return CostReport(
            report_id=f"report_{period_end.strftime('%Y%m%d')}",
            period_start=period_start,
            period_end=period_end,
            total_cost_usd=round(total_cost, 4),
            by_category=dict(by_category),
            by_service=dict(by_service),
            by_customer=dict(by_customer),
            by_allocation=dict(by_allocation),
            daily_breakdown=daily_breakdown,
            top_resources=top_resources,
            efficiency_metrics=efficiency_metrics,
            alerts=recent_alerts,
        )
    
    async def detect_anomalies(
        self,
        lookback_days: int = 7,
        threshold_std: float = 2.0,
    ) -> List[CostAlert]:
        """Detect cost anomalies."""
        anomalies = []
        
        # Calculate baseline from lookback period
        lookback_start = datetime.utcnow() - timedelta(days=lookback_days)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Historical daily costs
        historical_records = [
            r for r in self._records
            if lookback_start <= r.timestamp < today_start
        ]
        
        # Today's costs
        today_records = [
            r for r in self._records
            if r.timestamp >= today_start
        ]
        
        # Group historical by service
        historical_by_service = defaultdict(list)
        for r in historical_records:
            day = r.timestamp.strftime("%Y-%m-%d")
            historical_by_service[(r.service, day)] = historical_by_service.get((r.service, day), 0) + r.amount_usd
        
        # Calculate mean and std per service
        service_stats: Dict[str, Dict[str, float]] = {}
        for service in set(r.service for r in self._records):
            daily_costs = []
            for i in range(lookback_days):
                day = (today_start - timedelta(days=i + 1)).strftime("%Y-%m-%d")
                cost = historical_by_service.get((service, day), 0)
                daily_costs.append(cost)
            
            if daily_costs:
                mean = sum(daily_costs) / len(daily_costs)
                variance = sum((x - mean) ** 2 for x in daily_costs) / len(daily_costs)
                std = variance ** 0.5
                service_stats[service] = {"mean": mean, "std": std}
        
        # Check today's costs against baseline
        today_by_service = defaultdict(float)
        for r in today_records:
            today_by_service[r.service] += r.amount_usd
        
        for service, today_cost in today_by_service.items():
            stats = service_stats.get(service, {"mean": 0, "std": 0})
            mean = stats["mean"]
            std = stats["std"]
            
            if std > 0 and today_cost > mean + threshold_std * std:
                alert = CostAlert(
                    alert_id=f"anomaly_{service}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                    budget_id="anomaly_detection",
                    alert_type="anomaly",
                    severity="warning" if today_cost < mean + 3 * std else "critical",
                    message=f"Unusual spending on {service}: ${today_cost:.2f} vs ${mean:.2f} average",
                    current_amount_usd=today_cost,
                    limit_usd=mean + threshold_std * std,
                    percentage=round(today_cost / mean * 100, 2) if mean > 0 else 0,
                )
                anomalies.append(alert)
                self._alerts.append(alert)
                
                logger.warning(
                    "cost_anomaly_detected",
                    service=service,
                    today_cost=today_cost,
                    mean=mean,
                    std=std,
                )
        
        return anomalies
    
    async def _check_budgets(self, record: CostRecord) -> None:
        """Check if record triggers any budget alerts."""
        # Get current month costs
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        for budget_id, budget in self._budgets.items():
            # Filter matching records
            matching = [
                r for r in self._records
                if r.timestamp >= month_start
            ]
            
            if budget.category:
                matching = [r for r in matching if r.category == budget.category]
            if budget.service:
                matching = [r for r in matching if r.service == budget.service]
            if budget.customer_id:
                matching = [r for r in matching if r.customer_id == budget.customer_id]
            
            current_total = sum(r.amount_usd for r in matching)
            percentage = (current_total / budget.monthly_limit_usd * 100) if budget.monthly_limit_usd > 0 else 0
            
            # Check threshold
            if percentage >= budget.alert_threshold_pct:
                severity = "critical" if percentage >= 100 else "warning"
                
                # Don't duplicate recent alerts
                recent = [
                    a for a in self._alerts
                    if a.budget_id == budget_id
                    and (datetime.utcnow() - a.timestamp).total_seconds() < 3600
                ]
                
                if not recent:
                    alert = CostAlert(
                        alert_id=f"budget_{budget_id}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                        budget_id=budget_id,
                        alert_type="threshold",
                        severity=severity,
                        message=f"Budget '{budget.name}' at {percentage:.1f}% (${current_total:.2f} of ${budget.monthly_limit_usd:.2f})",
                        current_amount_usd=current_total,
                        limit_usd=budget.monthly_limit_usd,
                        percentage=round(percentage, 2),
                    )
                    self._alerts.append(alert)
                    
                    logger.warning(
                        "budget_threshold_exceeded",
                        budget_id=budget_id,
                        percentage=percentage,
                        current=current_total,
                        limit=budget.monthly_limit_usd,
                    )
    
    async def _calculate_efficiency(
        self,
        records: List[CostRecord],
    ) -> Dict[str, float]:
        """Calculate efficiency metrics."""
        if not records:
            return {}
        
        total_cost = sum(r.amount_usd for r in records)
        
        # Cost per customer
        customer_ids = set(r.customer_id for r in records if r.customer_id)
        cost_per_customer = total_cost / max(1, len(customer_ids))
        
        # Cost per API call (if API records exist)
        api_records = [r for r in records if r.category == CostCategory.API_CALLS]
        api_cost = sum(r.amount_usd for r in api_records)
        api_units = sum(r.units for r in api_records)
        cost_per_api_call = api_cost / max(1, api_units)
        
        # Compute utilization (if compute records exist)
        compute_records = [r for r in records if r.category == CostCategory.COMPUTE]
        compute_cost = sum(r.amount_usd for r in compute_records)
        
        # Direct vs shared ratio
        direct_cost = sum(r.amount_usd for r in records if r.allocation == CostAllocation.DIRECT)
        direct_ratio = direct_cost / total_cost if total_cost > 0 else 0
        
        return {
            "cost_per_customer_usd": round(cost_per_customer, 4),
            "cost_per_api_call_usd": round(cost_per_api_call, 8),
            "compute_cost_ratio": round(compute_cost / total_cost, 4) if total_cost > 0 else 0,
            "direct_attribution_ratio": round(direct_ratio, 4),
            "customer_count": len(customer_ids),
        }
    
    def get_alerts(
        self,
        hours: int = 24,
        severity: Optional[str] = None,
    ) -> List[CostAlert]:
        """Get recent alerts."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in self._alerts if a.timestamp > cutoff]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts


# Singleton accessor
_tracker: Optional[CostTracker] = None


async def get_cost_tracker() -> CostTracker:
    """Get or create the cost tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
        await _tracker.initialize()
    return _tracker
