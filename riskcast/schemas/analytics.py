"""
Analytics API Schemas.

Every endpoint returns data_sufficiency to indicate reliability.
"""

from typing import Optional

from pydantic import BaseModel, Field


class TimeSeriesPoint(BaseModel):
    date: str
    value: float
    count: int = 0


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    avg_severity: float
    max_severity: float
    pct_of_total: float


class RouteRisk(BaseModel):
    route_id: str
    route_name: str
    origin: str
    destination: str
    signal_count: int
    avg_severity: float
    incident_count: int


class RiskFactor(BaseModel):
    factor: str
    impact_score: float
    occurrence_count: int
    pct_contribution: float


class AnalyticsResponse(BaseModel):
    """Unified analytics response."""
    period: str
    generated_at: str
    data_sufficiency: str  # "insufficient" (<50) | "developing" (50-200) | "reliable" (200+)
    data_points: int
    message: Optional[str] = None


class RiskOverTimeResponse(AnalyticsResponse):
    series: list[TimeSeriesPoint] = Field(default_factory=list)


class RiskByCategoryResponse(AnalyticsResponse):
    categories: list[CategoryBreakdown] = Field(default_factory=list)


class RiskByRouteResponse(AnalyticsResponse):
    routes: list[RouteRisk] = Field(default_factory=list)


class TopRiskFactorsResponse(AnalyticsResponse):
    factors: list[RiskFactor] = Field(default_factory=list)


class SystemHealthResponse(BaseModel):
    """Pipeline and system health metrics."""
    generated_at: str
    signal_pipeline: dict
    database: dict
    omen_connection: dict
    last_scan_at: Optional[str] = None
