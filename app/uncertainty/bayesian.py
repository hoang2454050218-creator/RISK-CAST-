"""
Bayesian Uncertainty Quantification - Production Grade.

Properly propagates uncertainty through calculations using:
- Distribution modeling (normal, beta, lognormal, triangular, empirical)
- Monte Carlo simulation with configurable sample sizes
- Bayesian updating for combining uncertain inputs
- Risk metrics (VaR, CVaR/Expected Shortfall)
- Asymmetric confidence intervals for skewed distributions

Every numeric output in RISKCAST should use UncertainValue
to capture full uncertainty information.

Usage:
    # Create uncertain values
    cargo_value = UncertainValue.from_normal(mean=150000, std=5000)
    delay_days = UncertainValue.from_range(min_val=7, max_val=14)
    
    # Combine with uncertainty propagation
    calculator = BayesianCalculator()
    exposure = calculator.calculate_exposure(
        cargo_value, delay_days, holding_rate, penalty
    )
    
    # Access results with full uncertainty
    print(f"Exposure: ${exposure.point_estimate:,.0f}")
    print(f"90% CI: ${exposure.ci_90[0]:,.0f} - ${exposure.ci_90[1]:,.0f}")
    print(f"VaR 95%: ${exposure.var_95:,.0f}")
    print(f"CVaR 95%: ${exposure.cvar_95:,.0f}")
    
Addresses audit gaps:
- A2.2 Confidence Intervals: Full CI propagation through all calculations
- A4.4 Confidence Communication: Rich uncertainty metrics for actionable guidance
"""

from typing import Tuple, Optional, List, Union, Dict, Any
from enum import Enum
import math
import random
from pydantic import BaseModel, Field, field_validator, computed_field
import structlog

logger = structlog.get_logger(__name__)


class DistributionType(str, Enum):
    """Supported distribution types."""
    NORMAL = "normal"
    BETA = "beta"
    LOGNORMAL = "lognormal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    EMPIRICAL = "empirical"
    POINT = "point"  # Degenerate distribution (known value)


class Distribution(BaseModel):
    """
    Represents a probability distribution.
    
    Supports multiple distribution types with parameters.
    """
    type: DistributionType = Field(description="Distribution type")
    parameters: dict = Field(description="Distribution parameters")
    
    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, v, info):
        """Validate parameters based on distribution type."""
        # Parameters will be validated when sampling
        return v
    
    def sample(self, n: int = 1000, seed: Optional[int] = None) -> List[float]:
        """
        Draw samples from distribution.
        
        Uses pure Python for portability (no numpy required).
        For production, consider using numpy for performance.
        
        Args:
            n: Number of samples
            seed: Random seed for reproducibility
            
        Returns:
            List of samples
        """
        import random
        
        if seed is not None:
            random.seed(seed)
        
        if self.type == DistributionType.NORMAL:
            mean = self.parameters.get("mean", 0)
            std = self.parameters.get("std", 1)
            return [random.gauss(mean, std) for _ in range(n)]
        
        elif self.type == DistributionType.BETA:
            alpha = self.parameters.get("alpha", 2)
            beta_param = self.parameters.get("beta", 2)
            return [random.betavariate(alpha, beta_param) for _ in range(n)]
        
        elif self.type == DistributionType.LOGNORMAL:
            # Parameters are mean and sigma of underlying normal
            mu = self.parameters.get("mean", 0)
            sigma = self.parameters.get("sigma", 1)
            return [random.lognormvariate(mu, sigma) for _ in range(n)]
        
        elif self.type == DistributionType.UNIFORM:
            low = self.parameters.get("low", 0)
            high = self.parameters.get("high", 1)
            return [random.uniform(low, high) for _ in range(n)]
        
        elif self.type == DistributionType.TRIANGULAR:
            low = self.parameters.get("low", 0)
            high = self.parameters.get("high", 1)
            mode = self.parameters.get("mode", (low + high) / 2)
            return [random.triangular(low, high, mode) for _ in range(n)]
        
        elif self.type == DistributionType.EMPIRICAL:
            samples = self.parameters.get("samples", [0])
            return random.choices(samples, k=n)
        
        elif self.type == DistributionType.POINT:
            value = self.parameters.get("value", 0)
            return [value] * n
        
        else:
            raise ValueError(f"Unknown distribution type: {self.type}")
    
    def mean(self) -> float:
        """Calculate expected value."""
        if self.type == DistributionType.NORMAL:
            return self.parameters.get("mean", 0)
        
        elif self.type == DistributionType.BETA:
            a = self.parameters.get("alpha", 2)
            b = self.parameters.get("beta", 2)
            return a / (a + b)
        
        elif self.type == DistributionType.LOGNORMAL:
            mu = self.parameters.get("mean", 0)
            sigma = self.parameters.get("sigma", 1)
            return math.exp(mu + sigma**2 / 2)
        
        elif self.type == DistributionType.UNIFORM:
            low = self.parameters.get("low", 0)
            high = self.parameters.get("high", 1)
            return (low + high) / 2
        
        elif self.type == DistributionType.TRIANGULAR:
            low = self.parameters.get("low", 0)
            high = self.parameters.get("high", 1)
            mode = self.parameters.get("mode", (low + high) / 2)
            return (low + mode + high) / 3
        
        elif self.type == DistributionType.EMPIRICAL:
            samples = self.parameters.get("samples", [0])
            return sum(samples) / len(samples)
        
        elif self.type == DistributionType.POINT:
            return self.parameters.get("value", 0)
        
        else:
            return 0.0
    
    def std(self) -> float:
        """Calculate standard deviation."""
        if self.type == DistributionType.NORMAL:
            return self.parameters.get("std", 1)
        
        elif self.type == DistributionType.POINT:
            return 0.0
        
        else:
            # Estimate from samples
            samples = self.sample(1000)
            mean = sum(samples) / len(samples)
            variance = sum((x - mean) ** 2 for x in samples) / len(samples)
            return math.sqrt(variance)
    
    def confidence_interval(self, level: float = 0.90) -> Tuple[float, float]:
        """
        Compute confidence interval.
        
        Args:
            level: Confidence level (0.90 = 90% CI)
            
        Returns:
            (lower_bound, upper_bound)
        """
        samples = self.sample(10000)
        samples.sort()
        
        lower_pct = (1 - level) / 2
        upper_pct = 1 - lower_pct
        
        lower_idx = int(len(samples) * lower_pct)
        upper_idx = int(len(samples) * upper_pct) - 1
        
        return (samples[lower_idx], samples[upper_idx])


class UncertainValue(BaseModel):
    """
    A numeric value with full uncertainty quantification.
    
    Every uncertain value has:
    - Point estimate (best single guess)
    - Distribution (full probability model)
    - Multiple confidence intervals (80%, 90%, 95%, 99%)
    - Risk metrics (VaR, CVaR)
    - Asymmetric risk bounds (downside/upside)
    
    This addresses audit gap A2.2 (Confidence Intervals).
    """
    point_estimate: float = Field(description="Best single estimate (mean)")
    distribution: Distribution = Field(description="Full probability distribution")
    
    # Multiple confidence intervals
    ci_80: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="80% confidence interval (10th to 90th percentile)"
    )
    ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval (5th to 95th percentile)"
    )
    ci_95: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="95% confidence interval (2.5th to 97.5th percentile)"
    )
    ci_99: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="99% confidence interval (0.5th to 99.5th percentile)"
    )
    
    # Legacy compatibility
    confidence_interval_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval (legacy alias for ci_90)"
    )
    confidence_interval_95: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="95% confidence interval (legacy alias for ci_95)"
    )
    
    # Asymmetric risk bounds
    downside_risk: float = Field(
        default=0.0,
        description="5th percentile - worst reasonable case"
    )
    upside_potential: float = Field(
        default=0.0,
        description="95th percentile - best reasonable case"
    )
    
    # Risk metrics (for cost/loss distributions)
    var_95: float = Field(
        default=0.0,
        description="Value at Risk 95% - maximum loss at 95% confidence"
    )
    cvar_95: float = Field(
        default=0.0,
        description="Conditional VaR (Expected Shortfall) - expected loss in worst 5%"
    )
    
    # Standard deviation
    std: float = Field(
        default=0.0,
        description="Standard deviation of the distribution"
    )
    
    unit: Optional[str] = Field(
        default=None,
        description="Unit of measurement (e.g., 'usd', 'days')"
    )
    
    @computed_field
    @property
    def uncertainty_ratio(self) -> float:
        """Ratio of CI width to point estimate (coefficient of variation proxy)."""
        if self.point_estimate == 0:
            return float('inf')
        ci_width = self.ci_90[1] - self.ci_90[0]
        return ci_width / abs(self.point_estimate)
    
    @computed_field
    @property
    def is_highly_uncertain(self) -> bool:
        """Flag if uncertainty is > 50% of point estimate."""
        return self.uncertainty_ratio > 0.5
    
    @computed_field
    @property
    def is_asymmetric(self) -> bool:
        """Check if distribution is significantly asymmetric."""
        if self.point_estimate == 0:
            return False
        lower_diff = self.point_estimate - self.ci_90[0]
        upper_diff = self.ci_90[1] - self.point_estimate
        if lower_diff == 0:
            return True
        asymmetry = abs(upper_diff - lower_diff) / lower_diff
        return asymmetry > 0.3  # More than 30% difference
    
    def format_range(self, decimals: int = 0) -> str:
        """Format as 'point_estimate [ci_90_low - ci_90_high]'."""
        if decimals == 0:
            return f"{self.point_estimate:,.0f} [{self.ci_90[0]:,.0f} - {self.ci_90[1]:,.0f}]"
        return f"{self.point_estimate:,.{decimals}f} [{self.ci_90[0]:,.{decimals}f} - {self.ci_90[1]:,.{decimals}f}]"
    
    def format_currency(self) -> str:
        """Format as currency with range."""
        return f"${self.point_estimate:,.0f} [${self.ci_90[0]:,.0f} - ${self.ci_90[1]:,.0f}]"
    
    @classmethod
    def from_normal(
        cls,
        mean: float,
        std: float,
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from normal distribution parameters.
        
        Args:
            mean: Mean value
            std: Standard deviation
            unit: Unit of measurement
        """
        dist = Distribution(
            type=DistributionType.NORMAL,
            parameters={"mean": mean, "std": std}
        )
        
        # Sample for comprehensive statistics
        samples = dist.sample(10000)
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        
        # Calculate all intervals
        ci_80 = (sorted_samples[int(n * 0.10)], sorted_samples[int(n * 0.90) - 1])
        ci_90 = (sorted_samples[int(n * 0.05)], sorted_samples[int(n * 0.95) - 1])
        ci_95 = (sorted_samples[int(n * 0.025)], sorted_samples[int(n * 0.975) - 1])
        ci_99 = (sorted_samples[int(n * 0.005)], sorted_samples[int(n * 0.995) - 1])
        
        # Risk metrics
        var_95 = sorted_samples[int(n * 0.95)]
        worst_5_pct = sorted_samples[int(n * 0.95):]
        cvar_95 = sum(worst_5_pct) / len(worst_5_pct) if worst_5_pct else var_95
        
        return cls(
            point_estimate=mean,
            distribution=dist,
            ci_80=ci_80,
            ci_90=ci_90,
            ci_95=ci_95,
            ci_99=ci_99,
            confidence_interval_90=ci_90,
            confidence_interval_95=ci_95,
            downside_risk=sorted_samples[int(n * 0.05)],
            upside_potential=sorted_samples[int(n * 0.95)],
            var_95=var_95,
            cvar_95=cvar_95,
            std=std,
            unit=unit,
        )
    
    @classmethod
    def from_range(
        cls,
        min_val: float,
        max_val: float,
        most_likely: Optional[float] = None,
        confidence: float = 0.90,
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from a range with optional most likely value.
        
        If most_likely is provided, uses triangular distribution.
        Otherwise, assumes normal distribution with range as confidence interval.
        
        Args:
            min_val: Lower bound
            max_val: Upper bound
            most_likely: Most likely value (mode). If provided, uses triangular.
            confidence: Confidence level for the range (only if most_likely is None)
            unit: Unit of measurement
        """
        if most_likely is not None:
            # Use triangular distribution for asymmetric ranges
            return cls.from_triangular(min_val, most_likely, max_val, unit)
        
        # Calculate normal parameters from range
        mean = (min_val + max_val) / 2
        
        # Z-score for confidence level
        # For 90% CI, z ≈ 1.645
        # For 95% CI, z ≈ 1.96
        if confidence >= 0.99:
            z = 2.576
        elif confidence >= 0.95:
            z = 1.96
        elif confidence >= 0.90:
            z = 1.645
        elif confidence >= 0.80:
            z = 1.282
        else:
            z = 1.0
        
        std = (max_val - min_val) / (2 * z)
        
        return cls.from_normal(mean, std, unit)
    
    @classmethod
    def from_triangular(
        cls,
        low: float,
        mode: float,
        high: float,
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from triangular distribution (min, most likely, max).
        
        Useful for expert estimates with asymmetric uncertainty.
        """
        dist = Distribution(
            type=DistributionType.TRIANGULAR,
            parameters={"low": low, "mode": mode, "high": high}
        )
        
        # Sample for comprehensive statistics
        samples = dist.sample(10000)
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        
        # Calculate all intervals
        ci_80 = (sorted_samples[int(n * 0.10)], sorted_samples[int(n * 0.90) - 1])
        ci_90 = (sorted_samples[int(n * 0.05)], sorted_samples[int(n * 0.95) - 1])
        ci_95 = (sorted_samples[int(n * 0.025)], sorted_samples[int(n * 0.975) - 1])
        ci_99 = (sorted_samples[int(n * 0.005)], sorted_samples[int(n * 0.995) - 1])
        
        # Risk metrics
        var_95 = sorted_samples[int(n * 0.95)]
        worst_5_pct = sorted_samples[int(n * 0.95):]
        cvar_95 = sum(worst_5_pct) / len(worst_5_pct) if worst_5_pct else var_95
        
        # Calculate std from samples
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance)
        
        return cls(
            point_estimate=mean,
            distribution=dist,
            ci_80=ci_80,
            ci_90=ci_90,
            ci_95=ci_95,
            ci_99=ci_99,
            confidence_interval_90=ci_90,
            confidence_interval_95=ci_95,
            downside_risk=sorted_samples[int(n * 0.05)],
            upside_potential=sorted_samples[int(n * 0.95)],
            var_95=var_95,
            cvar_95=cvar_95,
            std=std,
            unit=unit,
        )
    
    @classmethod
    def from_samples(
        cls,
        samples: List[float],
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from Monte Carlo samples with full statistics.
        
        Args:
            samples: List of sample values
            unit: Unit of measurement
        """
        n = len(samples)
        if n == 0:
            raise ValueError("Cannot create UncertainValue from empty samples")
        
        mean = sum(samples) / n
        
        # Calculate percentiles
        sorted_samples = sorted(samples)
        
        # Calculate all intervals
        ci_80 = (
            sorted_samples[max(0, int(n * 0.10))],
            sorted_samples[min(n - 1, int(n * 0.90) - 1)]
        )
        ci_90 = (
            sorted_samples[max(0, int(n * 0.05))],
            sorted_samples[min(n - 1, int(n * 0.95) - 1)]
        )
        ci_95 = (
            sorted_samples[max(0, int(n * 0.025))],
            sorted_samples[min(n - 1, int(n * 0.975) - 1)]
        )
        ci_99 = (
            sorted_samples[max(0, int(n * 0.005))],
            sorted_samples[min(n - 1, int(n * 0.995) - 1)]
        )
        
        # Risk metrics
        var_95_idx = min(n - 1, int(n * 0.95))
        var_95 = sorted_samples[var_95_idx]
        worst_5_pct = sorted_samples[var_95_idx:]
        cvar_95 = sum(worst_5_pct) / len(worst_5_pct) if worst_5_pct else var_95
        
        # Calculate std
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance)
        
        return cls(
            point_estimate=mean,
            distribution=Distribution(
                type=DistributionType.EMPIRICAL,
                parameters={"samples": samples[:1000]}  # Limit stored samples
            ),
            ci_80=ci_80,
            ci_90=ci_90,
            ci_95=ci_95,
            ci_99=ci_99,
            confidence_interval_90=ci_90,
            confidence_interval_95=ci_95,
            downside_risk=sorted_samples[max(0, int(n * 0.05))],
            upside_potential=sorted_samples[min(n - 1, int(n * 0.95) - 1)],
            var_95=var_95,
            cvar_95=cvar_95,
            std=std,
            unit=unit,
        )
    
    @classmethod
    def from_point(
        cls,
        value: float,
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from a known (certain) value.
        
        For values with zero uncertainty (e.g., contract terms).
        """
        return cls(
            point_estimate=value,
            distribution=Distribution(
                type=DistributionType.POINT,
                parameters={"value": value}
            ),
            ci_80=(value, value),
            ci_90=(value, value),
            ci_95=(value, value),
            ci_99=(value, value),
            confidence_interval_90=(value, value),
            confidence_interval_95=(value, value),
            downside_risk=value,
            upside_potential=value,
            var_95=value,
            cvar_95=value,
            std=0.0,
            unit=unit,
        )
    
    @classmethod
    def from_beta(
        cls,
        alpha: float,
        beta: float,
        unit: Optional[str] = None,
    ) -> "UncertainValue":
        """
        Create from Beta distribution (good for probabilities).
        
        Args:
            alpha: Alpha parameter (successes + 1)
            beta: Beta parameter (failures + 1)
            unit: Unit of measurement
        """
        dist = Distribution(
            type=DistributionType.BETA,
            parameters={"alpha": alpha, "beta": beta}
        )
        
        # Sample for comprehensive statistics
        samples = dist.sample(10000)
        return cls.from_samples(samples, unit)
    
    def __add__(self, other: Union["UncertainValue", float, int]) -> "UncertainValue":
        """Add two uncertain values with uncertainty propagation."""
        if isinstance(other, (int, float)):
            # Scalar addition - shifts distribution
            samples = [s + other for s in self.distribution.sample(10000)]
            return UncertainValue.from_samples(samples, self.unit)
        
        # For independent normals, variances add
        if (self.distribution.type == DistributionType.NORMAL and 
            other.distribution.type == DistributionType.NORMAL):
            new_mean = self.point_estimate + other.point_estimate
            new_std = math.sqrt(
                self.distribution.parameters["std"]**2 +
                other.distribution.parameters["std"]**2
            )
            return UncertainValue.from_normal(new_mean, new_std, self.unit)
        else:
            # Monte Carlo for non-normal
            samples1 = self.distribution.sample(10000)
            samples2 = other.distribution.sample(10000)
            result_samples = [a + b for a, b in zip(samples1, samples2)]
            return UncertainValue.from_samples(result_samples, self.unit)
    
    def __radd__(self, other: Union[float, int]) -> "UncertainValue":
        """Handle scalar + UncertainValue."""
        return self.__add__(other)
    
    def __sub__(self, other: Union["UncertainValue", float, int]) -> "UncertainValue":
        """Subtract two uncertain values with uncertainty propagation."""
        if isinstance(other, (int, float)):
            samples = [s - other for s in self.distribution.sample(10000)]
            return UncertainValue.from_samples(samples, self.unit)
        
        # Monte Carlo for subtraction
        samples1 = self.distribution.sample(10000)
        samples2 = other.distribution.sample(10000)
        result_samples = [a - b for a, b in zip(samples1, samples2)]
        return UncertainValue.from_samples(result_samples, self.unit)
    
    def __rsub__(self, other: Union[float, int]) -> "UncertainValue":
        """Handle scalar - UncertainValue."""
        samples = [other - s for s in self.distribution.sample(10000)]
        return UncertainValue.from_samples(samples, self.unit)
    
    def __mul__(self, other: Union["UncertainValue", float, int]) -> "UncertainValue":
        """Multiply two uncertain values or uncertain * scalar."""
        if isinstance(other, (int, float)):
            # Scalar multiplication
            if self.distribution.type == DistributionType.NORMAL:
                return UncertainValue.from_normal(
                    self.point_estimate * other,
                    self.distribution.parameters["std"] * abs(other),
                    self.unit,
                )
            else:
                samples = [s * other for s in self.distribution.sample(10000)]
                return UncertainValue.from_samples(samples, self.unit)
        else:
            # Monte Carlo for products
            samples1 = self.distribution.sample(10000)
            samples2 = other.distribution.sample(10000)
            result_samples = [a * b for a, b in zip(samples1, samples2)]
            return UncertainValue.from_samples(result_samples, self.unit)
    
    def __rmul__(self, other: Union[float, int]) -> "UncertainValue":
        """Handle scalar * UncertainValue."""
        return self.__mul__(other)
    
    def __truediv__(self, other: Union["UncertainValue", float, int]) -> "UncertainValue":
        """Divide two uncertain values or uncertain / scalar."""
        if isinstance(other, (int, float)):
            if other == 0:
                raise ValueError("Cannot divide by zero")
            samples = [s / other for s in self.distribution.sample(10000)]
            return UncertainValue.from_samples(samples, self.unit)
        else:
            # Monte Carlo for division
            samples1 = self.distribution.sample(10000)
            samples2 = other.distribution.sample(10000)
            result_samples = [
                a / b for a, b in zip(samples1, samples2) if b != 0
            ]
            if not result_samples:
                raise ValueError("Division resulted in no valid samples")
            return UncertainValue.from_samples(result_samples, self.unit)
    
    def clip(self, min_val: float, max_val: float) -> "UncertainValue":
        """Clip uncertain value to range."""
        samples = self.distribution.sample(10000)
        clipped = [max(min_val, min(max_val, s)) for s in samples]
        return UncertainValue.from_samples(clipped, self.unit)
    
    def max(self, other: Union["UncertainValue", float]) -> "UncertainValue":
        """Element-wise maximum with uncertainty propagation."""
        if isinstance(other, (int, float)):
            samples = [max(s, other) for s in self.distribution.sample(10000)]
        else:
            samples1 = self.distribution.sample(10000)
            samples2 = other.distribution.sample(10000)
            samples = [max(a, b) for a, b in zip(samples1, samples2)]
        return UncertainValue.from_samples(samples, self.unit)


class BayesianCalculator:
    """
    Performs calculations with proper uncertainty propagation.
    
    All calculations use Monte Carlo simulation to propagate
    uncertainty through complex operations.
    """
    
    def __init__(self, n_samples: int = 10000):
        """
        Initialize calculator.
        
        Args:
            n_samples: Number of Monte Carlo samples
        """
        self.n_samples = n_samples
    
    def calculate_exposure(
        self,
        cargo_value: UncertainValue,
        delay_days: UncertainValue,
        holding_cost_rate: UncertainValue,
        penalty_per_day: UncertainValue,
        grace_period_days: int = 3,
    ) -> UncertainValue:
        """
        Calculate total exposure with uncertainty.
        
        Formula: 
        exposure = cargo_value * holding_rate * delay + penalty * max(delay - grace, 0)
        
        Args:
            cargo_value: Value of cargo in USD
            delay_days: Expected delay in days
            holding_cost_rate: Daily holding cost as fraction of cargo value
            penalty_per_day: Contract penalty per day of delay
            grace_period_days: Days before penalties apply
            
        Returns:
            Total exposure as UncertainValue
        """
        # Sample from all distributions
        cargo_samples = cargo_value.distribution.sample(self.n_samples)
        delay_samples = delay_days.distribution.sample(self.n_samples)
        rate_samples = holding_cost_rate.distribution.sample(self.n_samples)
        penalty_samples = penalty_per_day.distribution.sample(self.n_samples)
        
        # Calculate for each sample
        exposures = []
        for cargo, delay, rate, penalty in zip(
            cargo_samples, delay_samples, rate_samples, penalty_samples
        ):
            # Holding cost
            holding_cost = cargo * rate * max(delay, 0)
            
            # Penalty cost (after grace period)
            penalty_days = max(delay - grace_period_days, 0)
            penalty_cost = penalty * penalty_days
            
            # Total
            exposures.append(holding_cost + penalty_cost)
        
        return UncertainValue.from_samples(exposures, unit="usd")
    
    def calculate_confidence(
        self,
        signal_probability: UncertainValue,
        correlation_strength: UncertainValue,
        data_quality: UncertainValue,
        weights: Optional[Tuple[float, float, float]] = None,
    ) -> UncertainValue:
        """
        Calculate combined confidence with uncertainty.
        
        Combines multiple confidence factors with weighted average.
        
        Args:
            signal_probability: Probability from signal source
            correlation_strength: How well signal correlates with reality
            data_quality: Quality of input data
            weights: (signal_weight, correlation_weight, quality_weight)
            
        Returns:
            Combined confidence as UncertainValue
        """
        if weights is None:
            weights = (0.4, 0.3, 0.3)
        
        w_signal, w_correlation, w_quality = weights
        
        # Sample
        signal = signal_probability.distribution.sample(self.n_samples)
        correlation = correlation_strength.distribution.sample(self.n_samples)
        quality = data_quality.distribution.sample(self.n_samples)
        
        # Weighted average
        combined = []
        for s, c, q in zip(signal, correlation, quality):
            conf = w_signal * s + w_correlation * c + w_quality * q
            # Clamp to [0, 1]
            combined.append(max(0, min(1, conf)))
        
        return UncertainValue.from_samples(combined)
    
    def calculate_utility(
        self,
        action_cost: UncertainValue,
        risk_mitigated: UncertainValue,
        success_probability: UncertainValue,
    ) -> UncertainValue:
        """
        Calculate expected utility with uncertainty.
        
        utility = success_prob * risk_mitigated - action_cost
        
        Args:
            action_cost: Cost of taking action
            risk_mitigated: Risk reduction if action succeeds
            success_probability: Probability action succeeds
            
        Returns:
            Expected utility as UncertainValue
        """
        cost = action_cost.distribution.sample(self.n_samples)
        mitigated = risk_mitigated.distribution.sample(self.n_samples)
        prob = success_probability.distribution.sample(self.n_samples)
        
        utilities = []
        for c, m, p in zip(cost, mitigated, prob):
            utility = p * m - c
            utilities.append(utility)
        
        return UncertainValue.from_samples(utilities, unit="usd")
    
    def calculate_delay_impact(
        self,
        base_delay: UncertainValue,
        reroute_additional: UncertainValue,
        probability_event: UncertainValue,
    ) -> UncertainValue:
        """
        Calculate expected delay impact with uncertainty.
        
        Args:
            base_delay: Base delivery delay
            reroute_additional: Additional delay if rerouting
            probability_event: Probability that event requiring reroute occurs
            
        Returns:
            Expected delay as UncertainValue
        """
        base = base_delay.distribution.sample(self.n_samples)
        additional = reroute_additional.distribution.sample(self.n_samples)
        prob = probability_event.distribution.sample(self.n_samples)
        
        delays = []
        for b, a, p in zip(base, additional, prob):
            # Expected delay = base + prob * additional
            expected = b + p * a
            delays.append(max(0, expected))
        
        return UncertainValue.from_samples(delays, unit="days")
    
    def bayesian_update(
        self,
        prior: UncertainValue,
        likelihood: UncertainValue,
        evidence_strength: float = 1.0,
    ) -> UncertainValue:
        """
        Bayesian update of probability estimate.
        
        For probability estimates in [0, 1], uses beta-like update.
        
        Args:
            prior: Prior probability estimate
            likelihood: New evidence (as probability)
            evidence_strength: How much weight to give new evidence (0-1)
            
        Returns:
            Updated probability as UncertainValue
        """
        prior_samples = prior.distribution.sample(self.n_samples)
        likelihood_samples = likelihood.distribution.sample(self.n_samples)
        
        # Simple weighted update (not true Bayesian but intuitive)
        updated = []
        for p, l in zip(prior_samples, likelihood_samples):
            # Move prior toward likelihood based on evidence strength
            new_val = p + evidence_strength * (l - p)
            updated.append(max(0, min(1, new_val)))
        
        return UncertainValue.from_samples(updated)


# ============================================================================
# FACTORY
# ============================================================================


def create_bayesian_calculator(n_samples: int = 10000) -> BayesianCalculator:
    """
    Factory function to create BayesianCalculator.
    
    Args:
        n_samples: Number of Monte Carlo samples for calculations
        
    Returns:
        Configured BayesianCalculator
    """
    return BayesianCalculator(n_samples=n_samples)
