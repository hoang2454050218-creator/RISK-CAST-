"""
Application Configuration Module.

Production-grade configuration with:
- Pydantic Settings v2
- Environment variable support
- AWS Secrets Manager integration (production)
- Secure secret handling (never logged)
- Validation

SECURITY: Sensitive values are loaded from SecretsManager in production,
falling back to environment variables in development.
"""

from typing import Optional, List
from functools import lru_cache, cached_property
from pathlib import Path

from pydantic import Field, field_validator, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All sensitive values should be loaded from environment variables,
    never hardcoded.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    
    app_name: str = "RISKCAST"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    testing: bool = Field(default=False, alias="TESTING")
    
    # ========================================================================
    # API
    # ========================================================================
    
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000"],
        alias="ALLOWED_ORIGINS",
    )
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/riskcast",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses async driver."""
        if "postgresql://" in v and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v
    
    # ========================================================================
    # REDIS
    # ========================================================================
    
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    
    encryption_key: Optional[str] = Field(
        default=None,
        alias="ENCRYPTION_KEY",
        description="Master encryption key for PII (base64 encoded)",
    )
    encryption_key_version: int = Field(
        default=1,
        alias="ENCRYPTION_KEY_VERSION",
    )
    
    # API key settings
    api_key_header: str = "Authorization"
    api_key_prefix: str = "Bearer"
    
    # ========================================================================
    # EXTERNAL SERVICES
    # ========================================================================
    
    # Twilio (WhatsApp) — supports both Account SID+Token and API Key auth
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_api_key_sid: Optional[str] = Field(default=None, alias="TWILIO_API_KEY_SID")
    twilio_api_key_secret: Optional[str] = Field(default=None, alias="TWILIO_API_KEY_SECRET")
    twilio_whatsapp_number: Optional[str] = Field(
        default=None,
        alias="TWILIO_WHATSAPP_NUMBER",
    )
    
    # OMEN Signal Intelligence Service
    omen_api_url: str = Field(
        default="http://localhost:8000",
        alias="OMEN_URL",
        description="OMEN Signal Intelligence API base URL",
    )
    omen_api_key: str = Field(
        default="dev-test-key",
        alias="OMEN_API_KEY",
        description="API key for OMEN authentication",
    )
    
    # Polymarket
    polymarket_api_url: str = Field(
        default="https://gamma-api.polymarket.com",
        alias="POLYMARKET_API_URL",
    )
    polymarket_api_key: Optional[str] = Field(default=None, alias="POLYMARKET_API_KEY")
    
    # AIS / Marine Traffic
    ais_api_url: str = Field(
        default="https://services.marinetraffic.com/api",
        alias="AIS_API_URL",
    )
    ais_api_key: Optional[str] = Field(default=None, alias="AIS_API_KEY")
    
    # Anthropic (Claude) — LLM for reasoning engine enhancement
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model_reasoning: str = Field(
        default="claude-sonnet-4-20250514",
        alias="LLM_MODEL_REASONING",
        description="Model for reasoning enhancement (company analysis, causal chains)",
    )
    llm_model_fast: str = Field(
        default="claude-haiku-4-5-20251001",
        alias="LLM_MODEL_FAST",
        description="Fast model for signal analysis and explanations",
    )
    llm_enabled: bool = Field(
        default=True,
        alias="LLM_ENABLED",
        description="Enable LLM-enhanced reasoning (falls back to rule-based if False or no API key)",
    )
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    rate_limit_per_day: int = Field(default=10000, alias="RATE_LIMIT_PER_DAY")
    
    # ========================================================================
    # ALERTING
    # ========================================================================
    
    alert_cooldown_minutes: int = Field(default=30, alias="ALERT_COOLDOWN_MINUTES")
    max_alerts_per_day: int = Field(default=10, alias="MAX_ALERTS_PER_DAY")
    
    # ========================================================================
    # OBSERVABILITY
    # ========================================================================
    
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json or console
    
    # OpenTelemetry
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="riskcast-api", alias="OTEL_SERVICE_NAME")
    otel_exporter_endpoint: Optional[str] = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_sampling_rate: float = Field(default=0.1, alias="OTEL_SAMPLING_RATE")
    
    # Prometheus
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_path: str = Field(default="/metrics", alias="METRICS_PATH")
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    
    feature_outcome_tracking: bool = Field(
        default=True,
        alias="FEATURE_OUTCOME_TRACKING",
    )
    feature_confidence_calibration: bool = Field(
        default=True,
        alias="FEATURE_CONFIDENCE_CALIBRATION",
    )
    feature_multi_chokepoint: bool = Field(
        default=False,
        alias="FEATURE_MULTI_CHOKEPOINT",
    )
    
    # ========================================================================
    # CHOKEPOINTS
    # ========================================================================
    
    enabled_chokepoints: List[str] = Field(
        default=["red_sea"],
        alias="ENABLED_CHOKEPOINTS",
    )
    
    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
    
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"
    
    @computed_field
    @property
    def twilio_configured(self) -> bool:
        """Check if Twilio is configured (Account SID+Token or API Key)."""
        has_api_key = bool(self.twilio_api_key_sid and self.twilio_api_key_secret)
        has_account = bool(self.twilio_account_sid and self.twilio_auth_token)
        return (has_api_key or has_account) and bool(self.twilio_whatsapp_number)
    
    # ========================================================================
    # SECURE SECRET ACCESS
    # ========================================================================
    
    @cached_property
    def secure_database_url(self) -> str:
        """
        Get database URL from secrets manager.
        
        In production, loads from AWS Secrets Manager.
        In development, falls back to environment variable.
        """
        if self.is_development:
            return self.database_url
        
        from app.core.secrets import get_database_url
        return get_database_url()
    
    @cached_property
    def secure_twilio_credentials(self) -> dict:
        """
        Get Twilio credentials from secrets manager.
        
        Returns dict with 'account_sid' and 'auth_token'.
        """
        from app.core.secrets import get_twilio_credentials
        
        creds = get_twilio_credentials()
        if creds:
            return creds
        
        # Fallback to env vars
        return {
            "account_sid": self.twilio_account_sid or "",
            "auth_token": self.twilio_auth_token or "",
        }
    
    @cached_property
    def secure_polymarket_api_key(self) -> Optional[str]:
        """Get Polymarket API key from secrets manager."""
        from app.core.secrets import get_polymarket_api_key
        return get_polymarket_api_key() or self.polymarket_api_key
    
    @cached_property
    def secure_ais_api_key(self) -> Optional[str]:
        """Get AIS API key from secrets manager."""
        from app.core.secrets import get_ais_api_key
        return get_ais_api_key() or self.ais_api_key
    
    @cached_property
    def secure_encryption_key(self) -> Optional[str]:
        """Get encryption key from secrets manager."""
        from app.core.secrets import get_encryption_key
        return get_encryption_key() or self.encryption_key
    
    # ========================================================================
    # PROPERTY ALIASES (for compatibility)
    # ========================================================================
    
    @property
    def cors_origins(self) -> List[str]:
        """Alias for allowed_origins."""
        return self.allowed_origins
    
    @property
    def host(self) -> str:
        """Alias for api_host."""
        return self.api_host
    
    @property
    def port(self) -> int:
        """Alias for api_port."""
        return self.api_port


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    settings = Settings()
    
    logger.info(
        "settings_loaded",
        environment=settings.environment,
        debug=settings.debug,
        features={
            "outcome_tracking": settings.feature_outcome_tracking,
            "confidence_calibration": settings.feature_confidence_calibration,
            "multi_chokepoint": settings.feature_multi_chokepoint,
        },
    )
    
    return settings


# Global settings instance
settings = get_settings()
