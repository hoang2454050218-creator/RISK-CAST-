"""
Business Pricing & Value Module for RISKCAST.

Production-grade pricing and ROI calculations:
- Customer value scoring
- Pricing tiers
- ROI calculator
- Value metrics tracking
- Churn prediction signals
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import math

import structlog
from pydantic import BaseModel, Field, computed_field

logger = structlog.get_logger(__name__)


# ============================================================================
# PRICING TIERS
# ============================================================================


class PricingTier(str, Enum):
    """Pricing tiers for customers."""
    
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingPeriod(str, Enum):
    """Billing periods."""
    
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class TierLimits:
    """Limits for a pricing tier."""
    
    max_shipments_per_month: int
    max_alerts_per_day: int
    max_chokepoints: int
    max_team_members: int
    sla_response_hours: int
    api_rate_limit_per_minute: int
    historical_data_days: int
    custom_integrations: bool = False
    dedicated_support: bool = False
    priority_queue: bool = False


TIER_LIMITS: Dict[PricingTier, TierLimits] = {
    PricingTier.FREE: TierLimits(
        max_shipments_per_month=5,
        max_alerts_per_day=3,
        max_chokepoints=1,
        max_team_members=1,
        sla_response_hours=48,
        api_rate_limit_per_minute=10,
        historical_data_days=7,
    ),
    PricingTier.STARTER: TierLimits(
        max_shipments_per_month=100,
        max_alerts_per_day=25,
        max_chokepoints=3,
        max_team_members=3,
        sla_response_hours=24,
        api_rate_limit_per_minute=60,
        historical_data_days=30,
    ),
    PricingTier.PROFESSIONAL: TierLimits(
        max_shipments_per_month=500,
        max_alerts_per_day=100,
        max_chokepoints=10,
        max_team_members=10,
        sla_response_hours=4,
        api_rate_limit_per_minute=300,
        historical_data_days=90,
        custom_integrations=True,
    ),
    PricingTier.ENTERPRISE: TierLimits(
        max_shipments_per_month=99999,
        max_alerts_per_day=99999,
        max_chokepoints=99999,
        max_team_members=100,
        sla_response_hours=1,
        api_rate_limit_per_minute=1000,
        historical_data_days=365,
        custom_integrations=True,
        dedicated_support=True,
        priority_queue=True,
    ),
}


# Base prices in USD (aligned with frontend pricing 2026)
BASE_PRICES: Dict[PricingTier, Dict[BillingPeriod, Decimal]] = {
    PricingTier.FREE: {
        BillingPeriod.MONTHLY: Decimal("0"),
        BillingPeriod.QUARTERLY: Decimal("0"),
        BillingPeriod.ANNUAL: Decimal("0"),
    },
    PricingTier.STARTER: {
        BillingPeriod.MONTHLY: Decimal("199"),
        BillingPeriod.QUARTERLY: Decimal("179"),  # 10% discount
        BillingPeriod.ANNUAL: Decimal("159"),     # 20% discount
    },
    PricingTier.PROFESSIONAL: {
        BillingPeriod.MONTHLY: Decimal("599"),
        BillingPeriod.QUARTERLY: Decimal("539"),
        BillingPeriod.ANNUAL: Decimal("479"),
    },
    PricingTier.ENTERPRISE: {
        BillingPeriod.MONTHLY: Decimal("1499"),
        BillingPeriod.QUARTERLY: Decimal("1349"),
        BillingPeriod.ANNUAL: Decimal("1199"),
    },
}


# ============================================================================
# PRICING CALCULATOR
# ============================================================================


class PriceQuote(BaseModel):
    """Price quote for a customer."""
    
    quote_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tier: PricingTier
    billing_period: BillingPeriod
    base_price_usd: Decimal
    discount_pct: Decimal = Decimal("0")
    discount_reason: Optional[str] = None
    addon_price_usd: Decimal = Decimal("0")
    addons: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def total_price_usd(self) -> Decimal:
        """Calculate total price."""
        discount_amount = self.base_price_usd * (self.discount_pct / 100)
        return (self.base_price_usd - discount_amount + self.addon_price_usd).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    
    @computed_field
    @property
    def monthly_equivalent_usd(self) -> Decimal:
        """Monthly equivalent price."""
        multiplier = {
            BillingPeriod.MONTHLY: 1,
            BillingPeriod.QUARTERLY: 3,
            BillingPeriod.ANNUAL: 12,
        }
        return (self.total_price_usd / multiplier[self.billing_period]).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=30)
    )


class PricingCalculator:
    """
    Calculate pricing for customers.
    
    Handles:
    - Base tier pricing
    - Volume discounts
    - Promotional codes
    - Add-on features
    """
    
    # Add-on prices per month
    ADDONS: Dict[str, Decimal] = {
        "extra_chokepoint": Decimal("99"),
        "api_priority": Decimal("199"),
        "custom_webhook": Decimal("149"),
        "insurance_integration": Decimal("299"),
        "carrier_booking": Decimal("399"),
        "slack_integration": Decimal("49"),
        "email_alerts": Decimal("29"),
        "sms_alerts": Decimal("79"),
    }
    
    # Promotional codes
    PROMO_CODES: Dict[str, Decimal] = {
        "LAUNCH2024": Decimal("25"),      # 25% off
        "PARTNER10": Decimal("10"),       # 10% off
        "ANNUAL50": Decimal("50"),        # 50% off first year (annual only)
    }
    
    def calculate_quote(
        self,
        tier: PricingTier,
        billing_period: BillingPeriod,
        addons: List[str] = None,
        promo_code: Optional[str] = None,
    ) -> PriceQuote:
        """Calculate a price quote."""
        if tier == PricingTier.CUSTOM:
            raise ValueError("Custom tier requires manual quote")
        
        addons = addons or []
        
        # Get base price
        base_price = BASE_PRICES[tier][billing_period]
        
        # Calculate add-on cost
        addon_total = Decimal("0")
        valid_addons = []
        
        for addon in addons:
            if addon in self.ADDONS:
                addon_price = self.ADDONS[addon]
                # Adjust for billing period
                if billing_period == BillingPeriod.QUARTERLY:
                    addon_price *= 3
                elif billing_period == BillingPeriod.ANNUAL:
                    addon_price *= 12
                addon_total += addon_price
                valid_addons.append(addon)
        
        # Apply promo code
        discount_pct = Decimal("0")
        discount_reason = None
        
        if promo_code and promo_code.upper() in self.PROMO_CODES:
            code = promo_code.upper()
            # Check if ANNUAL50 is being used correctly
            if code == "ANNUAL50" and billing_period != BillingPeriod.ANNUAL:
                logger.warning("promo_code_invalid_period", code=code)
            else:
                discount_pct = self.PROMO_CODES[code]
                discount_reason = f"Promotional code: {code}"
        
        return PriceQuote(
            tier=tier,
            billing_period=billing_period,
            base_price_usd=base_price,
            discount_pct=discount_pct,
            discount_reason=discount_reason,
            addon_price_usd=addon_total,
            addons=valid_addons,
        )
    
    def get_tier_for_usage(
        self,
        monthly_shipments: int,
        daily_alerts: int,
        chokepoints_needed: int,
    ) -> PricingTier:
        """Recommend tier based on usage requirements."""
        for tier in [PricingTier.FREE, PricingTier.STARTER, 
                     PricingTier.PROFESSIONAL, PricingTier.ENTERPRISE]:
            limits = TIER_LIMITS[tier]
            if (monthly_shipments <= limits.max_shipments_per_month and
                daily_alerts <= limits.max_alerts_per_day and
                chokepoints_needed <= limits.max_chokepoints):
                return tier
        
        return PricingTier.CUSTOM


# ============================================================================
# ROI CALCULATOR
# ============================================================================


class ROIScenario(BaseModel):
    """ROI calculation scenario."""
    
    # Input parameters
    monthly_shipments: int = Field(ge=1)
    average_shipment_value_usd: Decimal
    current_disruption_rate_pct: Decimal = Field(ge=0, le=100)
    average_disruption_cost_pct: Decimal = Field(ge=0, le=100)
    average_delay_days: int = Field(ge=0)
    
    # RISKCAST effectiveness assumptions
    disruption_reduction_pct: Decimal = Field(default=Decimal("60"))  # 60% fewer disruptions
    delay_reduction_pct: Decimal = Field(default=Decimal("50"))       # 50% shorter delays
    proactive_reroute_savings_pct: Decimal = Field(default=Decimal("25"))  # 25% cheaper when proactive


class ROIResult(BaseModel):
    """ROI calculation result."""
    
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario: ROIScenario
    
    # Annual values
    annual_shipment_volume_usd: Decimal
    annual_disruption_cost_without_riskcast: Decimal
    annual_disruption_cost_with_riskcast: Decimal
    annual_savings_usd: Decimal
    
    # Monthly values
    monthly_savings_usd: Decimal
    
    # ROI metrics
    breakeven_tier: PricingTier
    breakeven_days: int
    
    @computed_field
    @property
    def roi_pct(self) -> Decimal:
        """Return on investment percentage."""
        if self.annual_disruption_cost_with_riskcast == 0:
            return Decimal("0")
        return ((self.annual_savings_usd / self.annual_disruption_cost_with_riskcast) * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    
    payback_period_months: Decimal
    net_value_year_1_usd: Decimal
    net_value_year_3_usd: Decimal
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ROICalculator:
    """
    Calculate ROI for RISKCAST implementation.
    
    Uses industry benchmarks and customer-specific data
    to project value and payback period.
    """
    
    def calculate(self, scenario: ROIScenario, tier: PricingTier) -> ROIResult:
        """Calculate ROI for a customer scenario."""
        
        # Annual volume
        annual_shipments = scenario.monthly_shipments * 12
        annual_volume = Decimal(str(annual_shipments)) * scenario.average_shipment_value_usd
        
        # Current disruption costs (without RISKCAST)
        disruptions_per_year = annual_shipments * (scenario.current_disruption_rate_pct / 100)
        cost_per_disruption = scenario.average_shipment_value_usd * (scenario.average_disruption_cost_pct / 100)
        annual_disruption_cost_current = disruptions_per_year * cost_per_disruption
        
        # With RISKCAST
        reduced_disruptions = disruptions_per_year * (1 - scenario.disruption_reduction_pct / 100)
        # Proactive rerouting reduces cost per disruption
        reduced_cost_per_disruption = cost_per_disruption * (1 - scenario.proactive_reroute_savings_pct / 100)
        annual_disruption_cost_with = reduced_disruptions * reduced_cost_per_disruption
        
        # Savings
        annual_savings = annual_disruption_cost_current - annual_disruption_cost_with
        monthly_savings = annual_savings / 12
        
        # Get subscription cost
        if tier == PricingTier.CUSTOM:
            annual_subscription = Decimal("0")
        else:
            monthly_price = BASE_PRICES[tier][BillingPeriod.MONTHLY]
            annual_subscription = monthly_price * 12
        
        # Breakeven calculation
        breakeven_tier = self._find_breakeven_tier(annual_savings)
        breakeven_days = self._calculate_breakeven_days(monthly_savings, tier)
        
        # Payback period
        if monthly_savings > 0:
            monthly_cost = annual_subscription / 12
            if monthly_savings > monthly_cost:
                payback_months = monthly_cost / (monthly_savings - monthly_cost)
            else:
                payback_months = Decimal("999")  # Won't pay back
        else:
            payback_months = Decimal("999")
        
        # Net value
        net_year_1 = annual_savings - annual_subscription
        net_year_3 = (annual_savings * 3) - (annual_subscription * 3)
        
        return ROIResult(
            scenario=scenario,
            annual_shipment_volume_usd=annual_volume.quantize(Decimal("0.01")),
            annual_disruption_cost_without_riskcast=annual_disruption_cost_current.quantize(Decimal("0.01")),
            annual_disruption_cost_with_riskcast=annual_disruption_cost_with.quantize(Decimal("0.01")),
            annual_savings_usd=annual_savings.quantize(Decimal("0.01")),
            monthly_savings_usd=monthly_savings.quantize(Decimal("0.01")),
            breakeven_tier=breakeven_tier,
            breakeven_days=breakeven_days,
            payback_period_months=payback_months.quantize(Decimal("0.1")),
            net_value_year_1_usd=net_year_1.quantize(Decimal("0.01")),
            net_value_year_3_usd=net_year_3.quantize(Decimal("0.01")),
        )
    
    def _find_breakeven_tier(self, annual_savings: Decimal) -> PricingTier:
        """Find the highest tier that still has positive ROI."""
        for tier in [PricingTier.ENTERPRISE, PricingTier.PROFESSIONAL, 
                     PricingTier.STARTER, PricingTier.FREE]:
            annual_cost = BASE_PRICES[tier][BillingPeriod.ANNUAL] * 12
            if annual_savings > annual_cost:
                return tier
        return PricingTier.FREE
    
    def _calculate_breakeven_days(self, monthly_savings: Decimal, tier: PricingTier) -> int:
        """Calculate days until breakeven."""
        if tier == PricingTier.CUSTOM:
            return 0
        
        monthly_cost = BASE_PRICES[tier][BillingPeriod.MONTHLY]
        
        if monthly_savings <= 0:
            return 365 * 10  # Never
        
        daily_savings = monthly_savings / 30
        days = int(monthly_cost / daily_savings)
        
        return min(days, 365 * 10)


# ============================================================================
# VALUE TRACKER
# ============================================================================


class CustomerValueMetrics(BaseModel):
    """Value metrics for a customer."""
    
    customer_id: str
    period_start: datetime
    period_end: datetime
    
    # Usage
    shipments_tracked: int = 0
    alerts_sent: int = 0
    decisions_generated: int = 0
    
    # Value delivered
    disruptions_predicted: int = 0
    disruptions_avoided: int = 0
    
    # Cost savings
    estimated_savings_usd: Decimal = Decimal("0")
    confirmed_savings_usd: Decimal = Decimal("0")
    
    # Delays
    average_delay_reduction_days: Decimal = Decimal("0")
    
    # Engagement
    alert_acknowledgment_rate_pct: Decimal = Decimal("0")
    action_taken_rate_pct: Decimal = Decimal("0")
    
    @computed_field
    @property
    def value_score(self) -> int:
        """Calculate overall value score (0-100)."""
        score = 0
        
        # Savings factor (up to 40 points)
        if self.estimated_savings_usd > 0:
            savings_factor = min(self.estimated_savings_usd / Decimal("100000"), 1)
            score += int(40 * float(savings_factor))
        
        # Engagement factor (up to 30 points)
        engagement = (self.alert_acknowledgment_rate_pct + self.action_taken_rate_pct) / 2
        score += int(30 * float(engagement / 100))
        
        # Avoidance factor (up to 30 points)
        if self.disruptions_predicted > 0:
            avoidance_rate = self.disruptions_avoided / self.disruptions_predicted
            score += int(30 * avoidance_rate)
        
        return min(score, 100)


class ValueTracker:
    """
    Track value delivered to customers.
    
    Used for:
    - Customer success metrics
    - Churn prediction
    - Upsell opportunities
    - ROI validation
    """
    
    def __init__(self, session=None):
        self._session = session
        self._metrics_cache: Dict[str, CustomerValueMetrics] = {}
    
    async def record_value_event(
        self,
        customer_id: str,
        event_type: str,
        value_usd: Decimal = Decimal("0"),
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Record a value event for a customer."""
        logger.info(
            "value_event_recorded",
            customer_id=customer_id,
            event_type=event_type,
            value_usd=str(value_usd),
        )
        
        # In production, persist to database
        # For now, update in-memory cache
        if customer_id not in self._metrics_cache:
            self._metrics_cache[customer_id] = CustomerValueMetrics(
                customer_id=customer_id,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30),
            )
        
        metrics = self._metrics_cache[customer_id]
        
        if event_type == "shipment_tracked":
            metrics.shipments_tracked += 1
        elif event_type == "alert_sent":
            metrics.alerts_sent += 1
        elif event_type == "decision_generated":
            metrics.decisions_generated += 1
        elif event_type == "disruption_predicted":
            metrics.disruptions_predicted += 1
        elif event_type == "disruption_avoided":
            metrics.disruptions_avoided += 1
            metrics.estimated_savings_usd += value_usd
        elif event_type == "savings_confirmed":
            metrics.confirmed_savings_usd += value_usd
    
    async def get_customer_metrics(
        self,
        customer_id: str,
        period_days: int = 30,
    ) -> Optional[CustomerValueMetrics]:
        """Get value metrics for a customer."""
        return self._metrics_cache.get(customer_id)
    
    async def calculate_ltv(
        self,
        customer_id: str,
        tier: PricingTier,
        months_active: int,
    ) -> Decimal:
        """Calculate customer lifetime value."""
        if tier == PricingTier.CUSTOM:
            return Decimal("0")
        
        monthly_revenue = BASE_PRICES[tier][BillingPeriod.MONTHLY]
        
        # Average retention rate by tier
        retention_rates = {
            PricingTier.FREE: Decimal("0.5"),
            PricingTier.STARTER: Decimal("0.85"),
            PricingTier.PROFESSIONAL: Decimal("0.92"),
            PricingTier.ENTERPRISE: Decimal("0.97"),
        }
        
        retention = retention_rates.get(tier, Decimal("0.9"))
        
        # LTV = ARPU * (1 / (1 - retention))
        if retention < 1:
            ltv = monthly_revenue * (1 / (1 - retention))
        else:
            ltv = monthly_revenue * 60  # 5 years
        
        return ltv.quantize(Decimal("0.01"))
    
    async def get_churn_risk_score(self, customer_id: str) -> Tuple[int, List[str]]:
        """
        Calculate churn risk score (0-100).
        
        Returns (score, risk_factors).
        Higher score = higher risk of churn.
        """
        metrics = self._metrics_cache.get(customer_id)
        if not metrics:
            return 50, ["insufficient_data"]
        
        risk_score = 0
        risk_factors = []
        
        # Low engagement
        if metrics.alert_acknowledgment_rate_pct < 20:
            risk_score += 30
            risk_factors.append("low_alert_engagement")
        
        # No actions taken
        if metrics.action_taken_rate_pct < 10:
            risk_score += 25
            risk_factors.append("no_actions_taken")
        
        # Low value delivered
        if metrics.value_score < 30:
            risk_score += 25
            risk_factors.append("low_value_score")
        
        # No recent activity
        if metrics.decisions_generated == 0:
            risk_score += 20
            risk_factors.append("no_recent_activity")
        
        return min(risk_score, 100), risk_factors


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================


_pricing_calculator: Optional[PricingCalculator] = None
_roi_calculator: Optional[ROICalculator] = None
_value_tracker: Optional[ValueTracker] = None


def get_pricing_calculator() -> PricingCalculator:
    """Get pricing calculator instance."""
    global _pricing_calculator
    if _pricing_calculator is None:
        _pricing_calculator = PricingCalculator()
    return _pricing_calculator


def get_roi_calculator() -> ROICalculator:
    """Get ROI calculator instance."""
    global _roi_calculator
    if _roi_calculator is None:
        _roi_calculator = ROICalculator()
    return _roi_calculator


def get_value_tracker() -> ValueTracker:
    """Get value tracker instance."""
    global _value_tracker
    if _value_tracker is None:
        _value_tracker = ValueTracker()
    return _value_tracker
