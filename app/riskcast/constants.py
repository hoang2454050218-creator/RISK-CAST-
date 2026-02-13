"""RISKCAST Constants - Enums, thresholds, and parameters.

All configurable values for the RISKCAST decision engine.
"""

from enum import Enum
from typing import TypedDict


# ============================================================================
# ENUMS
# ============================================================================


class Chokepoint(str, Enum):
    """Major maritime chokepoints (duplicated from omen for convenience)."""

    RED_SEA = "red_sea"
    SUEZ = "suez"
    PANAMA = "panama"
    MALACCA = "malacca"
    HORMUZ = "hormuz"
    GIBRALTAR = "gibraltar"


class ActionType(str, Enum):
    """Types of actions RISKCAST can recommend.

    MVP focuses on 5 core action types.
    """

    # Proactive interventions
    REROUTE = "reroute"  # Change route to avoid disruption
    DELAY = "delay"  # Hold shipment at origin
    SPLIT = "split"  # Split across multiple routes (Phase 2)
    EXPEDITE = "expedite"  # Speed up if possible (Phase 2)

    # Risk transfer
    INSURE = "insure"  # Buy additional insurance

    # Monitoring
    MONITOR = "monitor"  # Watch but don't act yet

    # Baseline
    DO_NOTHING = "do_nothing"  # Accept the risk


class Urgency(str, Enum):
    """Urgency levels for decisions."""

    IMMEDIATE = "immediate"  # Act within hours
    URGENT = "urgent"  # Act within 1-2 days
    SOON = "soon"  # Act within a week
    WATCH = "watch"  # Monitor, no immediate action


class Severity(str, Enum):
    """Impact severity levels."""

    LOW = "low"  # < $5,000 exposure
    MEDIUM = "medium"  # $5,000 - $25,000
    HIGH = "high"  # $25,000 - $100,000
    CRITICAL = "critical"  # > $100,000


class RiskTolerance(str, Enum):
    """Customer risk tolerance preferences.

    Affects action recommendations.
    """

    CONSERVATIVE = "conservative"  # Minimize risk, accept higher cost
    BALANCED = "balanced"  # Balance cost and risk
    AGGRESSIVE = "aggressive"  # Minimize cost, accept more risk


class ShipmentStatus(str, Enum):
    """Shipment lifecycle status."""

    BOOKED = "booked"  # Confirmed but not departed
    IN_TRANSIT = "in_transit"  # Currently moving
    AT_PORT = "at_port"  # Waiting at port
    DELIVERED = "delivered"  # Arrived at destination
    CANCELLED = "cancelled"  # Cancelled


class ConfidenceLevel(str, Enum):
    """Confidence levels for decisions."""

    HIGH = "high"  # 80%+ - Act with confidence
    MEDIUM = "medium"  # 60-80% - Act but monitor
    LOW = "low"  # <60% - Consider monitoring first


# ============================================================================
# SEVERITY THRESHOLDS (USD)
# ============================================================================

SEVERITY_THRESHOLDS: dict[str, float] = {
    "LOW": 5_000,
    "MEDIUM": 25_000,
    "HIGH": 100_000,
    # Above HIGH = CRITICAL
}


def get_severity(cost_usd: float) -> Severity:
    """Determine severity level from cost in USD."""
    if cost_usd < SEVERITY_THRESHOLDS["LOW"]:
        return Severity.LOW
    elif cost_usd < SEVERITY_THRESHOLDS["MEDIUM"]:
        return Severity.MEDIUM
    elif cost_usd < SEVERITY_THRESHOLDS["HIGH"]:
        return Severity.HIGH
    else:
        return Severity.CRITICAL


# ============================================================================
# CHOKEPOINT PARAMETERS
# ============================================================================


class ChokepointParams(TypedDict):
    """Parameters for a chokepoint."""

    reroute_delay_days: tuple[int, int]  # (min, max) delay in days
    reroute_cost_per_teu: float  # USD per TEU for rerouting
    holding_cost_per_day_pct: float  # % of cargo value per day
    alternative_route: str  # Name of alternative route


CHOKEPOINT_PARAMS: dict[str, ChokepointParams] = {
    "red_sea": {
        "reroute_delay_days": (7, 14),
        "reroute_cost_per_teu": 2500.0,
        "holding_cost_per_day_pct": 0.001,  # 0.1% per day
        "alternative_route": "Cape of Good Hope",
    },
    "suez": {
        "reroute_delay_days": (7, 14),
        "reroute_cost_per_teu": 2500.0,
        "holding_cost_per_day_pct": 0.001,
        "alternative_route": "Cape of Good Hope",
    },
    "panama": {
        "reroute_delay_days": (5, 10),
        "reroute_cost_per_teu": 2000.0,
        "holding_cost_per_day_pct": 0.001,
        "alternative_route": "Suez Canal",
    },
    "malacca": {
        "reroute_delay_days": (2, 4),
        "reroute_cost_per_teu": 800.0,
        "holding_cost_per_day_pct": 0.001,
        "alternative_route": "Lombok Strait",
    },
    "hormuz": {
        "reroute_delay_days": (3, 7),
        "reroute_cost_per_teu": 1500.0,
        "holding_cost_per_day_pct": 0.001,
        "alternative_route": "Overland pipeline",
    },
}


def get_chokepoint_params(chokepoint: str) -> ChokepointParams:
    """Get parameters for a chokepoint with fallback to Red Sea defaults."""
    return CHOKEPOINT_PARAMS.get(chokepoint, CHOKEPOINT_PARAMS["red_sea"])


# ============================================================================
# ROUTE MAPPINGS
# ============================================================================

# Maps origin-destination pairs to chokepoints on the route
ROUTE_CHOKEPOINTS: dict[tuple[str, str], list[str]] = {
    # Asia → Europe routes (via Suez/Red Sea)
    ("CNSHA", "NLRTM"): ["malacca", "red_sea", "suez"],  # Shanghai → Rotterdam
    ("CNSHA", "DEHAM"): ["malacca", "red_sea", "suez"],  # Shanghai → Hamburg
    ("CNNGB", "NLRTM"): ["malacca", "red_sea", "suez"],  # Ningbo → Rotterdam
    ("CNYTN", "NLRTM"): ["malacca", "red_sea", "suez"],  # Yantian → Rotterdam
    ("VNHCM", "NLRTM"): ["malacca", "red_sea", "suez"],  # Ho Chi Minh → Rotterdam
    ("VNHCM", "DEHAM"): ["malacca", "red_sea", "suez"],  # Ho Chi Minh → Hamburg
    ("KRPUS", "NLRTM"): ["malacca", "red_sea", "suez"],  # Busan → Rotterdam
    ("JPYOK", "NLRTM"): ["malacca", "red_sea", "suez"],  # Yokohama → Rotterdam
    ("SGSIN", "NLRTM"): ["red_sea", "suez"],  # Singapore → Rotterdam
    ("INMUN", "NLRTM"): ["red_sea", "suez"],  # Mumbai → Rotterdam
    # Asia → US East Coast (via Suez)
    ("CNSHA", "USNYC"): ["malacca", "red_sea", "suez"],  # Shanghai → New York
    ("CNSHA", "USSAV"): ["malacca", "red_sea", "suez"],  # Shanghai → Savannah
    ("VNHCM", "USNYC"): ["malacca", "red_sea", "suez"],  # Ho Chi Minh → New York
    # Asia → US West Coast (Pacific, no Red Sea)
    ("CNSHA", "USLAX"): [],  # Shanghai → Los Angeles
    ("CNSHA", "USLGB"): [],  # Shanghai → Long Beach
    ("CNNGB", "USLAX"): [],  # Ningbo → Los Angeles
    ("VNHCM", "USLAX"): [],  # Ho Chi Minh → Los Angeles
    ("KRPUS", "USLAX"): [],  # Busan → Los Angeles
    # Europe → Asia (reverse)
    ("NLRTM", "CNSHA"): ["suez", "red_sea", "malacca"],
    ("DEHAM", "CNSHA"): ["suez", "red_sea", "malacca"],
    # Middle East routes
    ("AEAUH", "NLRTM"): ["red_sea", "suez"],  # Abu Dhabi → Rotterdam
    ("SAJED", "NLRTM"): ["red_sea", "suez"],  # Jeddah → Rotterdam
}


def derive_chokepoints(origin: str, destination: str) -> list[str]:
    """
    Derive chokepoints from origin/destination ports.

    Falls back to Red Sea assumption for Asia-Europe routes.
    """
    key = (origin.upper(), destination.upper())
    if key in ROUTE_CHOKEPOINTS:
        return ROUTE_CHOKEPOINTS[key]

    # Heuristic fallback based on port regions
    origin_upper = origin.upper()
    dest_upper = destination.upper()

    # Asia origins
    asia_prefixes = ("CN", "VN", "KR", "JP", "TW", "TH", "MY", "ID", "PH")
    # Europe destinations
    europe_prefixes = ("NL", "DE", "BE", "FR", "GB", "ES", "IT", "PL")
    # US East Coast
    us_east_ports = ("USNYC", "USSAV", "USBAL", "USBOS", "USMIA")

    is_asia_origin = any(origin_upper.startswith(p) for p in asia_prefixes)
    is_europe_dest = any(dest_upper.startswith(p) for p in europe_prefixes)
    is_us_east_dest = dest_upper in us_east_ports

    if is_asia_origin and (is_europe_dest or is_us_east_dest):
        return ["malacca", "red_sea", "suez"]

    # Default: assume no chokepoints (direct route)
    return []


# ============================================================================
# TEU CONVERSION
# ============================================================================

TEU_CONVERSION: dict[str, float] = {
    "20GP": 1.0,  # 20ft General Purpose
    "20HC": 1.0,  # 20ft High Cube
    "40GP": 2.0,  # 40ft General Purpose
    "40HC": 2.0,  # 40ft High Cube
    "45HC": 2.25,  # 45ft High Cube
    "20RF": 1.0,  # 20ft Reefer
    "40RF": 2.0,  # 40ft Reefer
}


def container_to_teu(container_type: str, count: int = 1) -> float:
    """Convert container type and count to TEU."""
    multiplier = TEU_CONVERSION.get(container_type.upper(), 2.0)  # Default to 40ft
    return count * multiplier


# ============================================================================
# CARRIER INFORMATION
# ============================================================================


class CarrierInfo(TypedDict):
    """Carrier information for recommendations."""

    code: str
    name: str
    premium_pct: float  # Premium percentage for rerouting
    capacity: str  # high, medium, low
    contact: str


CARRIERS: dict[str, CarrierInfo] = {
    "MSCU": {
        "code": "MSCU",
        "name": "MSC",
        "premium_pct": 0.35,
        "capacity": "high",
        "contact": "bookings@msc.com",
    },
    "MAEU": {
        "code": "MAEU",
        "name": "Maersk",
        "premium_pct": 0.40,
        "capacity": "high",
        "contact": "bookings@maersk.com",
    },
    "CMDU": {
        "code": "CMDU",
        "name": "CMA CGM",
        "premium_pct": 0.38,
        "capacity": "medium",
        "contact": "bookings@cma-cgm.com",
    },
    "COSU": {
        "code": "COSU",
        "name": "COSCO",
        "premium_pct": 0.32,
        "capacity": "high",
        "contact": "bookings@cosco.com",
    },
    "EGLV": {
        "code": "EGLV",
        "name": "Evergreen",
        "premium_pct": 0.34,
        "capacity": "medium",
        "contact": "bookings@evergreen.com",
    },
    "HLCU": {
        "code": "HLCU",
        "name": "Hapag-Lloyd",
        "premium_pct": 0.42,
        "capacity": "medium",
        "contact": "bookings@hapag-lloyd.com",
    },
    "ONEY": {
        "code": "ONEY",
        "name": "ONE",
        "premium_pct": 0.36,
        "capacity": "medium",
        "contact": "bookings@one-line.com",
    },
}


def get_carrier_info(code: str) -> CarrierInfo | None:
    """Get carrier information by SCAC code."""
    return CARRIERS.get(code.upper())


def get_best_reroute_carrier(chokepoint: str) -> CarrierInfo:
    """Get the best carrier for rerouting around a chokepoint."""
    # Sort by premium (lowest first), then by capacity (high first)
    capacity_order = {"high": 0, "medium": 1, "low": 2}
    sorted_carriers = sorted(
        CARRIERS.values(),
        key=lambda c: (c["premium_pct"], capacity_order.get(c["capacity"], 2)),
    )
    return sorted_carriers[0]


# ============================================================================
# TIMING CONSTANTS
# ============================================================================

# Booking window (hours before departure)
BOOKING_DEADLINE_HOURS = 48

# Decision validity period (hours)
DECISION_TTL_HOURS = 24

# Inaction cost escalation factors
INACTION_ESCALATION = {
    6: 1.10,  # 10% increase after 6 hours
    24: 1.30,  # 30% increase after 24 hours
    48: 1.50,  # 50% increase after 48 hours
}


# ============================================================================
# INSURANCE CONSTANTS
# ============================================================================

# Insurance premium rate (percentage of cargo value)
INSURANCE_PREMIUM_RATE = 0.0075  # 0.75%

# Insurance coverage percentage
INSURANCE_COVERAGE_PCT = 0.80  # 80% of losses covered


# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

CONFIDENCE_THRESHOLDS = {
    "HIGH": 0.80,
    "MEDIUM": 0.60,
    # Below MEDIUM = LOW
}


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Determine confidence level from score."""
    if score >= CONFIDENCE_THRESHOLDS["HIGH"]:
        return ConfidenceLevel.HIGH
    elif score >= CONFIDENCE_THRESHOLDS["MEDIUM"]:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
