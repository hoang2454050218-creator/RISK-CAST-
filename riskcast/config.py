"""
RiskCast V2 Configuration.

Pydantic Settings v2 — loads from .env, environment variables.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "RiskCast V2"
    app_version: str = "2.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8001, alias="V2_API_PORT")
    api_prefix: str = "/api/v1"
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://riskcast:riskcast@localhost:5432/riskcast",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # ── JWT ────────────────────────────────────────────────────────────────
    jwt_secret: str = Field(
        default="dev-jwt-secret-change-in-production",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")

    # ── Security ────────────────────────────────────────────────────────────
    encryption_key: str = Field(default="", alias="RISKCAST_ENCRYPTION_KEY")
    rate_limit_default: int = Field(default=100, alias="RATE_LIMIT_DEFAULT")
    rate_limit_burst: int = Field(default=20, alias="RATE_LIMIT_BURST")

    # ── Alerting ──────────────────────────────────────────────────────────
    alert_cooldown_minutes: int = Field(default=30, alias="ALERT_COOLDOWN_MINUTES")
    max_alerts_per_day: int = Field(default=50, alias="MAX_ALERTS_PER_DAY")
    alert_webhook_url: str = Field(default="", alias="ALERT_WEBHOOK_URL")
    alert_smtp_host: str = Field(default="", alias="ALERT_SMTP_HOST")
    alert_smtp_port: int = Field(default=587, alias="ALERT_SMTP_PORT")
    alert_from_email: str = Field(default="alerts@riskcast.io", alias="ALERT_FROM_EMAIL")

    # ── External Services ─────────────────────────────────────────────────
    omen_url: str = Field(default="http://localhost:8000", alias="OMEN_URL")
    omen_api_key: str = Field(default="dev-test-key", alias="OMEN_API_KEY")
    omen_timeout_seconds: int = Field(default=30, alias="OMEN_TIMEOUT_SECONDS")
    omen_retry_attempts: int = Field(default=3, alias="OMEN_RETRY_ATTEMPTS")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # ── Risk Engine ────────────────────────────────────────────────────────
    # Analyzer weights (order risk composite)
    weight_customer: float = Field(default=0.4, alias="RISK_WEIGHT_CUSTOMER")
    weight_route: float = Field(default=0.3, alias="RISK_WEIGHT_ROUTE")
    weight_value: float = Field(default=0.15, alias="RISK_WEIGHT_VALUE")
    weight_new_customer: float = Field(default=0.15, alias="RISK_WEIGHT_NEW_CUSTOMER")
    composite_emit_threshold: float = Field(
        default=30.0, alias="COMPOSITE_EMIT_THRESHOLD",
        description="Minimum composite score to emit a risk signal",
    )

    # Payment risk
    payment_lookback_days: int = Field(default=90, alias="PAYMENT_LOOKBACK_DAYS")
    late_ratio_threshold: float = Field(default=0.3, alias="LATE_RATIO_THRESHOLD")
    payment_behavior_recent_count: int = Field(default=5, alias="PAYMENT_BEHAVIOR_RECENT_COUNT")
    payment_behavior_change_multiplier: float = Field(default=1.5, alias="PAYMENT_BEHAVIOR_CHANGE_MULTIPLIER")

    # Route disruption
    route_analysis_days: int = Field(default=14, alias="ROUTE_ANALYSIS_DAYS")
    route_min_orders: int = Field(default=3, alias="ROUTE_MIN_ORDERS")
    route_macro_boost: float = Field(default=0.15, alias="ROUTE_MACRO_BOOST")
    route_disruption_threshold: float = Field(default=0.5, alias="ROUTE_DISRUPTION_THRESHOLD")

    # Ensemble model weights
    ensemble_weight_fusion: float = Field(default=0.6, alias="ENSEMBLE_WEIGHT_FUSION")
    ensemble_weight_bayesian: float = Field(default=0.4, alias="ENSEMBLE_WEIGHT_BAYESIAN")

    # Severity bands
    severity_critical_threshold: float = Field(default=75.0, alias="SEVERITY_CRITICAL_THRESHOLD")
    severity_high_threshold: float = Field(default=50.0, alias="SEVERITY_HIGH_THRESHOLD")
    severity_moderate_threshold: float = Field(default=25.0, alias="SEVERITY_MODERATE_THRESHOLD")

    # Escalation
    escalation_exposure_threshold: float = Field(default=200_000.0, alias="ESCALATION_EXPOSURE_THRESHOLD")
    escalation_confidence_floor: float = Field(default=0.5, alias="ESCALATION_CONFIDENCE_FLOOR")
    escalation_risk_ceiling: float = Field(default=80.0, alias="ESCALATION_RISK_CEILING")
    escalation_disagreement_threshold: float = Field(default=15.0, alias="ESCALATION_DISAGREEMENT_THRESHOLD")

    # Temporal decay half-lives (hours)
    halflife_payment_risk: float = Field(default=720.0, alias="HALFLIFE_PAYMENT_RISK")
    halflife_route_disruption: float = Field(default=168.0, alias="HALFLIFE_ROUTE_DISRUPTION")
    halflife_order_risk: float = Field(default=336.0, alias="HALFLIFE_ORDER_RISK")
    halflife_market_volatility: float = Field(default=72.0, alias="HALFLIFE_MARKET_VOLATILITY")
    halflife_default: float = Field(default=168.0, alias="HALFLIFE_DEFAULT")
    temporal_min_weight: float = Field(default=0.01, alias="TEMPORAL_MIN_WEIGHT")

    # Pipeline health
    freshness_stale_minutes: int = Field(default=60, alias="FRESHNESS_STALE_MINUTES")
    freshness_outdated_minutes: int = Field(default=360, alias="FRESHNESS_OUTDATED_MINUTES")
    gap_threshold_minutes: int = Field(default=120, alias="GAP_THRESHOLD_MINUTES")

    # ── Operational ────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_tracing: bool = Field(default=False, alias="ENABLE_TRACING")
    health_check_timeout_seconds: int = Field(default=5, alias="HEALTH_CHECK_TIMEOUT_SECONDS")
    graceful_shutdown_seconds: int = Field(default=30, alias="GRACEFUL_SHUTDOWN_SECONDS")

    @property
    def async_database_url(self) -> str:
        """Ensure the database URL uses asyncpg driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url


settings = Settings()  # v2-alerts
