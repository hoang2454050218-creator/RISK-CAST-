# NEXUS RISKCAST - Complete AI Documentation

> **Decision Intelligence Platform for Supply Chain Risk Management**
>
> Document Version: 1.0 | Last Updated: 2026-02-05
> 
> This document provides comprehensive information for AI assistants to understand the entire RISKCAST project.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Architecture](#2-core-architecture)
3. [The 7 Questions Framework](#3-the-7-questions-framework)
4. [Module Deep Dive](#4-module-deep-dive)
5. [Data Models & Schemas](#5-data-models--schemas)
6. [Business Logic & Calculations](#6-business-logic--calculations)
7. [API Endpoints](#7-api-endpoints)
8. [Infrastructure & DevOps](#8-infrastructure--devops)
9. [Testing Strategy](#9-testing-strategy)
10. [Key Design Decisions](#10-key-design-decisions)
11. [Development Guidelines](#11-development-guidelines)
12. [Constants & Configuration Reference](#12-constants--configuration-reference)

---

## 1. Executive Summary

### 1.1 What is RISKCAST?

**RISKCAST** is a Decision Intelligence Platform that transforms supply chain disruption signals into personalized, actionable decisions for maritime shipping customers.

**The Core Difference:**
```
NOTIFICATION SYSTEM: "Red Sea disruption detected"
RISKCAST:            "REROUTE shipment PO-4521 via Cape with MSC. Cost: $8,500. Book by 6PM today."
```

### 1.2 The MOAT (Competitive Advantage)

RISKCAST's competitive advantage is **customer context personalization**:

| Timeline | Capability | Defensibility |
|----------|-----------|---------------|
| Day 1 | Generic alerts | Competitors can copy |
| Day 30 | Personalized decisions | Know customer routes, shipments, preferences |
| Day 90 | Self-improving system | Historical accuracy data for calibration |

Every feature should collect more customer context to compound this advantage.

### 1.3 Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Runtime | Python | 3.11+ |
| Framework | FastAPI | Latest |
| Validation | Pydantic | v2 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| Messaging | Twilio (WhatsApp) | - |
| Observability | Prometheus, OpenTelemetry, Jaeger | - |
| Container | Docker, Kubernetes (EKS) | - |
| IaC | Terraform | - |
| CI/CD | GitHub Actions | - |

---

## 2. Core Architecture

### 2.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NEXUS PLATFORM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │    OMEN     │───▶│   ORACLE    │───▶│  RISKCAST   │───▶│   ALERTER   │ │
│   │  (Signals)  │    │  (Reality)  │    │ (Decisions) │    │ (WhatsApp)  │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  ▼          │
│   What MIGHT        What IS            What to DO        How to INFORM     │
│   happen            happening           about it         the customer      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility | Key Output |
|-----------|----------------|------------|
| **OMEN** | Signal collection & validation | `OmenSignal` with probability + confidence |
| **ORACLE** | Reality correlation (AIS, rates) | `CorrelatedIntelligence` with status |
| **RISKCAST** | Decision generation (THE MOAT) | `DecisionObject` answering 7 Questions |
| **ALERTER** | Delivery via WhatsApp | Message delivery + tracking |

### 2.3 Directory Structure

```
RISK CAST V2/
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── core/                      # Config, database, middleware, security
│   │   ├── config.py              # Settings from environment
│   │   ├── database.py            # PostgreSQL async connections
│   │   ├── middleware.py          # Request ID, rate limiting, security headers
│   │   ├── cache.py               # Redis caching
│   │   ├── tracing.py             # OpenTelemetry distributed tracing
│   │   └── events.py              # Event bus for async processing
│   │
│   ├── omen/                      # Signal Engine
│   │   ├── schemas.py             # OmenSignal, EvidenceItem, Chokepoint
│   │   ├── service.py             # OmenService for signal processing
│   │   ├── client.py              # External API clients (Polymarket, etc.)
│   │   └── validators/            # 4-stage validation pipeline
│   │       ├── schema.py          # Schema validation
│   │       ├── source.py          # Source credibility
│   │       ├── content.py         # Content plausibility
│   │       └── cross_reference.py # Cross-source verification
│   │
│   ├── oracle/                    # Reality Engine
│   │   ├── schemas.py             # RealitySnapshot, ChokepointHealth
│   │   ├── service.py             # OracleService
│   │   ├── ais.py                 # AIS vessel tracking
│   │   ├── freight.py             # Freight rate APIs
│   │   ├── port.py                # Port congestion data
│   │   └── correlator.py          # Signal-Reality correlation
│   │
│   ├── riskcast/                  # Decision Engine (THE MOAT)
│   │   ├── constants.py           # Enums, thresholds, parameters
│   │   ├── service.py             # AsyncRiskCastService (main API)
│   │   ├── schemas/
│   │   │   ├── customer.py        # CustomerProfile, Shipment, CustomerContext
│   │   │   ├── impact.py          # CostBreakdown, DelayEstimate, TotalImpact
│   │   │   ├── action.py          # Action, ActionSet, TradeOffAnalysis
│   │   │   └── decision.py        # Q1-Q7 models, DecisionObject
│   │   ├── matchers/
│   │   │   └── exposure.py        # ExposureMatcher - which shipments affected?
│   │   ├── calculators/
│   │   │   └── impact.py          # ImpactCalculator - how much $ and days?
│   │   ├── generators/
│   │   │   ├── action.py          # ActionGenerator - what are the options?
│   │   │   └── tradeoff.py        # TradeOffAnalyzer - what if I don't act?
│   │   ├── composers/
│   │   │   └── decision.py        # DecisionComposer - combine into Q1-Q7
│   │   ├── repos/
│   │   │   ├── customer.py        # Customer data access
│   │   │   └── decision.py        # Decision persistence
│   │   ├── confidence_calibration.py  # Self-improving confidence
│   │   └── outcome_tracking.py    # Track decision outcomes
│   │
│   ├── alerter/                   # Delivery Engine
│   │   ├── schemas.py             # AlertConfig, DeliveryStatus
│   │   ├── service.py             # AlerterService
│   │   ├── whatsapp.py            # Twilio WhatsApp integration
│   │   └── templates.py           # Message templates
│   │
│   ├── api/routes/                # FastAPI endpoints
│   │   ├── health.py              # /health, /ready, /live
│   │   ├── customers.py           # Customer CRUD
│   │   ├── shipments.py           # Shipment management
│   │   ├── decisions.py           # Decision generation & retrieval
│   │   ├── signals.py             # OMEN signal queries
│   │   ├── audit.py               # Audit trail endpoints
│   │   ├── calibration.py         # Confidence calibration
│   │   └── governance.py          # AI governance
│   │
│   ├── audit/                     # Audit trail for accountability
│   │   ├── service.py             # AuditService
│   │   ├── repository.py          # Audit log persistence
│   │   ├── trail.py               # AuditedDecisionComposer
│   │   └── snapshots.py           # Input/output snapshots
│   │
│   ├── ml/                        # Machine Learning
│   │   ├── pipeline.py            # ML pipeline orchestration
│   │   ├── features.py            # Feature engineering
│   │   └── calibration.py         # Probability calibration
│   │
│   ├── common/                    # Shared utilities
│   │   ├── exceptions.py          # Custom exceptions
│   │   └── metrics.py             # Prometheus metrics
│   │
│   └── db/                        # Database models
│       ├── models.py              # SQLAlchemy models
│       └── session.py             # Session management
│
├── alembic/                       # Database migrations
│   └── versions/                  # Migration scripts
│
├── tests/                         # Test suite (150+ tests)
│   ├── conftest.py                # Pytest fixtures
│   └── test_riskcast/             # RISKCAST unit tests
│
├── k8s/                           # Kubernetes manifests
│   ├── deployment.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── argo-rollouts/             # Blue-green, canary deployments
│
├── monitoring/                    # Observability config
│   └── prometheus.yml
│
├── config/                        # Application config
│   ├── alerting.yaml
│   └── prometheus/alerts/
│
└── deploy/
    ├── kubernetes/
    └── terraform/
```

---

## 3. The 7 Questions Framework

**EVERY DecisionObject MUST answer these 7 questions. No exceptions.**

This is what makes RISKCAST a DECISION system, not a NOTIFICATION system.

### 3.1 Question Overview

| # | Question | What it answers | Bad Example ❌ | Good Example ✅ |
|---|----------|-----------------|----------------|-----------------|
| Q1 | What's happening? | Personalized event summary | "Red Sea disruption" | "Red Sea disruption affecting YOUR route SH→RTM" |
| Q2 | When? | Timeline + urgency | "Ongoing situation" | "Impact in 3-5 days for shipment #4521" |
| Q3 | How bad? | $ exposure + delay | "Significant impact" | "Exposure: $235K, 10-14 days delay" |
| Q4 | Why? | Causal chain | "Geopolitical tensions" | "Houthi attacks → carriers avoid Suez → +10 days" |
| Q5 | What to do? | Specific action | "Consider alternatives" | "REROUTE via Cape, MSC, $8,500, by 6PM" |
| Q6 | Confidence? | Score + factors | "High confidence" | "87% based on Polymarket + 23 vessels rerouting" |
| Q7 | If nothing? | Inaction cost | "Risk increases" | "Wait 6h: +$15K. Wait 24h: booking closes." |

### 3.2 Q1: What Is Happening?

```python
class Q1WhatIsHappening(BaseModel):
    event_type: str           # DISRUPTION, CONGESTION, RATE_SPIKE, WEATHER
    event_summary: str        # One-line personalized summary (max 150 chars)
    affected_chokepoint: str  # Primary chokepoint affected
    affected_routes: list[str]      # Customer's routes affected
    affected_shipments: list[str]   # Customer's shipment IDs affected
```

**Key Rule:** Must be personalized to the customer's specific shipments and routes.

### 3.3 Q2: When Will It Happen?

```python
class Q2WhenWillItHappen(BaseModel):
    status: str               # PREDICTED / MATERIALIZING / CONFIRMED / ONGOING
    impact_timeline: str      # When customer feels impact
    earliest_impact: datetime # Earliest expected impact time
    latest_resolution: datetime
    urgency: Urgency          # IMMEDIATE / URGENT / SOON / WATCH
    urgency_reason: str       # Why this urgency level
```

**Urgency Levels:**
- `IMMEDIATE`: Act within hours
- `URGENT`: Act within 1-2 days
- `SOON`: Act within a week
- `WATCH`: Monitor, no immediate action needed

### 3.4 Q3: How Bad Is It?

```python
class Q3HowBadIsIt(BaseModel):
    # Exposure (with confidence intervals)
    total_exposure_usd: float       # Total $ at risk (point estimate)
    exposure_breakdown: dict        # By category (cargo, penalties, etc.)
    exposure_ci_90: tuple[float, float]   # 90% confidence interval
    exposure_ci_95: tuple[float, float]   # 95% confidence interval
    
    # Delay (with confidence intervals)
    expected_delay_days: int        # Point estimate
    delay_range: str                # "10-14 days"
    delay_ci_90: tuple[float, float]
    
    # Impact
    shipments_affected: int
    shipments_with_penalties: int
    severity: Severity              # LOW / MEDIUM / HIGH / CRITICAL
```

**Key Rule:** All numbers must be in DOLLARS and DAYS, not percentages or vague descriptions.

### 3.5 Q4: Why Is This Happening?

```python
class Q4WhyIsThisHappening(BaseModel):
    root_cause: str           # Root cause in plain language
    causal_chain: list[str]   # Step-by-step cause → effect
    evidence_summary: str     # Summary of supporting evidence
    sources: list[str]        # Data sources used
```

**Example Causal Chain:**
```
["Houthi attacks", "Carriers avoiding Red Sea", "Rerouting via Cape", "10-14 day additional transit"]
```

### 3.6 Q5: What To Do Now?

```python
class Q5WhatToDoNow(BaseModel):
    action_type: str              # REROUTE / DELAY / INSURE / MONITOR / DO_NOTHING
    action_summary: str           # Specific action in one line
    
    # Specifics
    affected_shipments: list[str]
    recommended_carrier: str      # Carrier code (e.g., MSCU)
    
    # Cost (with confidence intervals)
    estimated_cost_usd: float     # Point estimate
    cost_ci_90: tuple[float, float]
    
    # Execution
    execution_steps: list[str]    # Step-by-step guide
    deadline: datetime            # When action must be done
    deadline_reason: str          # Why this deadline
    
    # Contact
    who_to_contact: str
    contact_info: str
    
    # Utility
    expected_utility: float       # Benefit - cost
    success_probability: float    # Probability of achieving outcome
```

**Key Rule:** Must include specific action, cost, deadline, and carrier.

### 3.7 Q6: How Confident?

```python
class Q6HowConfident(BaseModel):
    score: float              # 0-1 confidence score
    level: ConfidenceLevel    # HIGH / MEDIUM / LOW
    factors: dict[str, float] # Confidence factor breakdown
    explanation: str          # Human-readable explanation
    caveats: list[str]        # Things that could change assessment
```

**Confidence Factors Include:**
- `signal_probability`: From prediction markets
- `intelligence_correlation`: Signal-reality match
- `impact_assessment`: Calculation reliability

### 3.8 Q7: What If Nothing?

```python
class Q7WhatIfNothing(BaseModel):
    # Immediate loss (with confidence intervals)
    expected_loss_if_nothing: float
    loss_ci_90: tuple[float, float]
    loss_ci_95: tuple[float, float]
    
    # Time-based escalation (with CIs)
    cost_if_wait_6h: float
    cost_if_wait_24h: float
    cost_if_wait_48h: float
    cost_if_wait_6h_ci: tuple[float, float]
    
    # Point of no return
    point_of_no_return: datetime
    point_of_no_return_reason: str
    
    # Worst case
    worst_case_cost: float
    worst_case_scenario: str
    
    # Summary
    inaction_summary: str     # One-line summary
```

**Key Rule:** Must show time-based cost escalation to create urgency.

---

## 4. Module Deep Dive

### 4.1 OMEN - Signal Engine

**Location:** `app/omen/`

**Purpose:** Collect and validate predictive signals from external sources.

#### Key Schemas

```python
class OmenSignal(BaseModel):
    """
    CRITICAL DISTINCTION:
    - probability = EVENT LIKELIHOOD (from Polymarket, 0-1)
    - confidence_score = DATA QUALITY (reliability of information, 0-1)
    
    High confidence + Low probability = "We're SURE it probably WON'T happen"
    Low confidence + High probability = "Unreliable data says it WILL happen"
    """
    signal_id: str
    title: str
    description: str
    category: SignalCategory  # GEOPOLITICAL, WEATHER, INFRASTRUCTURE, etc.
    probability: float        # Event likelihood (0-1)
    confidence_score: float   # Data quality (0-1)
    geographic: GeographicScope
    temporal: TemporalScope
    evidence: list[EvidenceItem]
```

#### Signal Categories

| Category | Examples |
|----------|----------|
| GEOPOLITICAL | Conflicts, sanctions, political instability |
| WEATHER | Storms, floods, extreme weather |
| INFRASTRUCTURE | Port closures, canal issues |
| LABOR | Strikes, workforce issues |
| ECONOMIC | Currency, trade policy changes |
| SECURITY | Piracy, terrorism threats |

#### Validation Pipeline (4 stages)

1. **Schema Validation** - Required fields, data types
2. **Source Credibility** - Is the source trustworthy?
3. **Content Plausibility** - Does the signal make sense?
4. **Cross-Reference** - Do multiple sources agree?

### 4.2 ORACLE - Reality Engine

**Location:** `app/oracle/`

**Purpose:** Provide ground truth about what IS happening through real-world data.

#### Key Schemas

```python
class CorrelatedIntelligence(BaseModel):
    """
    PRIMARY INPUT TO RISKCAST.
    Combines OMEN signal with ORACLE reality.
    """
    correlation_id: str
    signal: OmenSignal
    reality: RealitySnapshot
    correlation_status: CorrelationStatus
    combined_confidence: float
```

#### Correlation Status

| Status | Meaning | Action |
|--------|---------|--------|
| CONFIRMED | Signal happening in reality | Act immediately |
| MATERIALIZING | Early signs appearing | Prepare to act |
| PREDICTED_NOT_OBSERVED | Signal exists, reality normal | Monitor closely |
| SURPRISE | Reality disruption without signal | Investigate |
| NORMAL | No significant activity | Standard operations |

#### Data Sources

- **AIS (Automatic Identification System):** Vessel positions, routes, speeds
- **Freight Rates:** Current vs baseline rates per TEU
- **Port Congestion:** Vessels waiting, processing times
- **Chokepoint Health:** Transit times, disruption levels

### 4.3 RISKCAST - Decision Engine (THE MOAT)

**Location:** `app/riskcast/`

**Purpose:** Transform information into personalized, actionable decisions.

#### Internal Pipeline

```
Input: CorrelatedIntelligence + CustomerContext
                    ↓
┌──────────────────────────────────────────────────────────────┐
│  1. ExposureMatcher   → Which shipments are affected?        │
│  2. ImpactCalculator  → How much in $ and days?              │
│  3. ActionGenerator   → What are the options?                │
│  4. TradeOffAnalyzer  → What if I don't act?                 │
│  5. DecisionComposer  → Combine into Q1-Q7 format            │
└──────────────────────────────────────────────────────────────┘
                    ↓
Output: DecisionObject (7 Questions answered)
```

#### 4.3.1 ExposureMatcher

**File:** `app/riskcast/matchers/exposure.py`

**Logic:**
1. Get chokepoint from signal
2. Find shipments that pass through that chokepoint
3. Filter by timing (overlap with event window)
4. Filter by status (not delivered/cancelled)
5. Calculate total exposure and confidence

**Output:** `ExposureMatch` with:
- `affected_shipments`: List of exposed shipments
- `total_exposure_usd`: Sum of cargo values
- `exposure_confidence`: How certain we are

#### 4.3.2 ImpactCalculator

**File:** `app/riskcast/calculators/impact.py`

**Calculations per shipment:**

```python
# Delay estimation
delay_days = chokepoint_params['reroute_delay_days']  # (min, max)
expected_delay = (min_delay + max_delay) / 2

# Holding cost
holding_cost = cargo_value_usd * holding_cost_per_day_pct * delay_days

# Reroute cost
reroute_cost = teu_count * reroute_cost_per_teu

# Penalty cost (if applicable)
if delay_days > penalty_free_days:
    penalty = (delay_days - penalty_free_days) * daily_penalty_usd
```

**Output:** `TotalImpact` with per-shipment breakdowns

#### 4.3.3 ActionGenerator

**File:** `app/riskcast/generators/action.py`

**Action Types:**

| Type | Description | When to Use |
|------|-------------|-------------|
| REROUTE | Change route to avoid disruption | High probability, clear alternative |
| DELAY | Hold shipment at origin | Short-term disruption expected |
| INSURE | Buy additional insurance | High exposure, moderate probability |
| MONITOR | Watch but don't act yet | Low confidence, developing situation |
| DO_NOTHING | Accept the risk | Low impact or low probability |

**Ranking by Utility Score:**
```python
utility = (risk_mitigated / (cost + 1)) * feasibility_factor * urgency_factor
```

#### 4.3.4 TradeOffAnalyzer

**File:** `app/riskcast/generators/tradeoff.py`

**Output includes:**
- Cost escalation at 6h, 24h, 48h
- Point of no return
- Worst case scenario
- Recommended action with reasoning

#### 4.3.5 DecisionComposer

**File:** `app/riskcast/composers/decision.py`

**Orchestrates all components into a DecisionObject:**

```python
def compose(intelligence, context):
    exposure = self.exposure_matcher.match(intelligence, context)
    impact = self.impact_calculator.calculate(exposure, intelligence, context)
    action_set = self.action_generator.generate(exposure, impact, intelligence, context)
    tradeoff = self.tradeoff_analyzer.analyze(action_set, impact, exposure, intelligence)
    
    # Compose each of the 7 questions
    q1 = self._compose_q1(exposure, intelligence, context)
    q2 = self._compose_q2(exposure, impact, intelligence, tradeoff)
    # ... etc
    
    return DecisionObject(q1=q1, q2=q2, q3=q3, q4=q4, q5=q5, q6=q6, q7=q7, ...)
```

### 4.4 ALERTER - Delivery Engine

**Location:** `app/alerter/`

**Purpose:** Deliver decisions to customers via WhatsApp.

**Features:**
- WhatsApp Business API via Twilio
- Message templates for different languages
- Delivery tracking and status
- Cooldown rules to prevent alert fatigue

---

## 5. Data Models & Schemas

### 5.1 Enums Reference

| Enum | Values | Location |
|------|--------|----------|
| `SignalCategory` | GEOPOLITICAL, WEATHER, INFRASTRUCTURE, LABOR, ECONOMIC, SECURITY, OTHER | omen/schemas.py |
| `Chokepoint` | RED_SEA, SUEZ, PANAMA, MALACCA, HORMUZ, GIBRALTAR, DOVER, BOSPHORUS | omen/schemas.py |
| `CorrelationStatus` | CONFIRMED, MATERIALIZING, PREDICTED_NOT_OBSERVED, SURPRISE, NORMAL | oracle/schemas.py |
| `ActionType` | REROUTE, DELAY, SPLIT, EXPEDITE, INSURE, MONITOR, DO_NOTHING | riskcast/constants.py |
| `Urgency` | IMMEDIATE, URGENT, SOON, WATCH | riskcast/constants.py |
| `Severity` | LOW, MEDIUM, HIGH, CRITICAL | riskcast/constants.py |
| `RiskTolerance` | CONSERVATIVE, BALANCED, AGGRESSIVE | riskcast/constants.py |
| `ShipmentStatus` | BOOKED, IN_TRANSIT, AT_PORT, DELIVERED, CANCELLED | riskcast/constants.py |
| `ConfidenceLevel` | HIGH, MEDIUM, LOW | riskcast/constants.py |

### 5.2 Customer Schemas

```python
class CustomerProfile(BaseModel):
    customer_id: str
    company_name: str
    primary_routes: list[str]       # ["VNHCM-NLRTM", "CNSHA-DEHAM"]
    relevant_chokepoints: list[str] # Derived from routes
    risk_tolerance: RiskTolerance   # CONSERVATIVE, BALANCED, AGGRESSIVE
    primary_phone: str              # E.164 format (+84901234567)
    language: str                   # ISO code (en, vi, zh)
    timezone: str                   # IANA timezone

class Shipment(BaseModel):
    shipment_id: str
    origin_port: str               # UN/LOCODE (VNHCM)
    destination_port: str          # UN/LOCODE (NLRTM)
    cargo_value_usd: float
    etd: datetime                  # Estimated time of departure
    eta: datetime                  # Estimated time of arrival
    container_count: int
    container_type: str            # 20GP, 40HC, etc.
    status: ShipmentStatus
    has_delay_penalty: bool
    delay_penalty_per_day_usd: float

class CustomerContext(BaseModel):
    profile: CustomerProfile
    active_shipments: list[Shipment]
    total_cargo_value_usd: float   # Computed
    total_teu: float               # Computed
```

### 5.3 Validation Rules

- **Phone:** E.164 format (`+84901234567`)
- **Ports:** 5-char UN/LOCODE (`VNHCM`, `NLRTM`)
- **Routes:** Format `ORIGIN-DEST` (`VNHCM-NLRTM`)
- **ETD < ETA:** Departure must be before arrival

---

## 6. Business Logic & Calculations

### 6.1 Severity Thresholds (USD)

```python
SEVERITY_THRESHOLDS = {
    "LOW": 5_000,       # < $5,000
    "MEDIUM": 25_000,   # $5,000 - $25,000
    "HIGH": 100_000,    # $25,000 - $100,000
    # Above = CRITICAL
}
```

### 6.2 Chokepoint Parameters

| Chokepoint | Reroute Delay | Cost/TEU | Alternative |
|------------|---------------|----------|-------------|
| Red Sea | 7-14 days | $2,500 | Cape of Good Hope |
| Suez | 7-14 days | $2,500 | Cape of Good Hope |
| Panama | 5-10 days | $2,000 | Suez Canal |
| Malacca | 2-4 days | $800 | Lombok Strait |
| Hormuz | 3-7 days | $1,500 | Overland pipeline |

### 6.3 Inaction Cost Escalation

```python
INACTION_ESCALATION = {
    6: 1.10,    # +10% after 6 hours
    24: 1.30,   # +30% after 24 hours
    48: 1.50,   # +50% after 48 hours
}
```

### 6.4 TEU Conversion

| Container Type | TEU |
|----------------|-----|
| 20GP, 20HC | 1.0 |
| 40GP, 40HC | 2.0 |
| 45HC | 2.25 |
| 20RF, 40RF | 1.0, 2.0 |

### 6.5 Confidence Thresholds

```python
CONFIDENCE_THRESHOLDS = {
    "HIGH": 0.80,   # 80%+ → Act with confidence
    "MEDIUM": 0.60, # 60-80% → Act but monitor
    # Below = LOW  → Consider monitoring first
}
```

### 6.6 Route → Chokepoint Mappings

```python
ROUTE_CHOKEPOINTS = {
    # Asia → Europe
    ("CNSHA", "NLRTM"): ["malacca", "red_sea", "suez"],
    ("VNHCM", "NLRTM"): ["malacca", "red_sea", "suez"],
    ("SGSIN", "NLRTM"): ["red_sea", "suez"],
    
    # Asia → US East Coast
    ("CNSHA", "USNYC"): ["malacca", "red_sea", "suez"],
    
    # Asia → US West Coast (no chokepoints)
    ("CNSHA", "USLAX"): [],
    ("VNHCM", "USLAX"): [],
}
```

### 6.7 Carrier Information

| Code | Name | Premium | Capacity |
|------|------|---------|----------|
| MSCU | MSC | 35% | High |
| MAEU | Maersk | 40% | High |
| CMDU | CMA CGM | 38% | Medium |
| COSU | COSCO | 32% | High |
| EGLV | Evergreen | 34% | Medium |
| HLCU | Hapag-Lloyd | 42% | Medium |
| ONEY | ONE | 36% | Medium |

---

## 7. API Endpoints

### 7.1 Health & Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Overall health check |
| GET | `/health/live` | Kubernetes liveness probe |
| GET | `/health/ready` | Kubernetes readiness probe |
| GET | `/api/v1/metrics` | Prometheus metrics |

### 7.2 Customers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/customers` | List all customers |
| POST | `/api/v1/customers` | Create customer |
| GET | `/api/v1/customers/{id}` | Get customer |
| PUT | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Delete customer |

### 7.3 Shipments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/shipments` | List shipments |
| POST | `/api/v1/shipments` | Create shipment |
| GET | `/api/v1/shipments/{id}` | Get shipment |
| PUT | `/api/v1/shipments/{id}` | Update shipment |

### 7.4 Decisions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/decisions/generate` | Generate decision for signal |
| GET | `/api/v1/decisions` | List decisions |
| GET | `/api/v1/decisions/{id}` | Get decision |
| POST | `/api/v1/decisions/{id}/acknowledge` | Acknowledge decision |
| POST | `/api/v1/decisions/{id}/feedback` | Submit feedback |

### 7.5 Signals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/signals` | List active signals |
| GET | `/api/v1/signals/{id}` | Get signal details |
| POST | `/api/v1/signals/ingest` | Ingest new signal |

### 7.6 Audit

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/audit/decisions/{id}` | Get audit trail for decision |
| GET | `/api/v1/audit/verify` | Verify audit chain integrity |

---

## 8. Infrastructure & DevOps

### 8.1 Database

- **PostgreSQL 15** for persistent storage
- **Redis 7** for caching and rate limiting
- **Alembic** for database migrations

### 8.2 Observability

- **Prometheus:** Metrics collection
- **OpenTelemetry → Jaeger:** Distributed tracing
- **Structlog:** JSON-formatted logging

### 8.3 Kubernetes Deployment

```yaml
# Key configurations
replicas: 3 (minimum)
HPA: 3-20 pods based on CPU/memory
PDB: min 2 available
Pod Anti-Affinity: spread across nodes
```

### 8.4 Security

- API key authentication with scopes (RBAC)
- AES-256-GCM encryption for PII fields
- Rate limiting with sliding window
- Security headers (HSTS, CSP)

---

## 9. Testing Strategy

### 9.1 Test Summary

| Module | File | Tests |
|--------|------|-------|
| Customer Schemas | test_customer.py | 23 |
| Exposure Matcher | test_exposure.py | 19 |
| Impact Calculator | test_impact.py | 21 |
| Action Generator | test_action.py | 14 |
| TradeOff Analyzer | test_tradeoff.py | 15 |
| Decision Schemas | test_decision.py | 22 |
| Decision Composer | test_composer.py | 18 |
| RiskCast Service | test_service.py | 18 |
| **Total** | | **150+** |

### 9.2 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific module
pytest tests/test_riskcast/test_composer.py -v
```

---

## 10. Key Design Decisions

### 10.1 Separation of Concerns

| Component | Handles | Never Handles |
|-----------|---------|---------------|
| OMEN | Signal collection | Decisions, risk levels |
| ORACLE | Reality correlation | Recommendations |
| RISKCAST | Decision generation | Data collection |
| ALERTER | Message delivery | Decision logic |

### 10.2 Why 7 Questions?

The 7 Questions framework ensures:
1. **Completeness:** Every decision is thoroughly analyzed
2. **Actionability:** Users know exactly what to do
3. **Urgency:** Time-based escalation creates urgency
4. **Trust:** Confidence scores and evidence build trust

### 10.3 Self-Improving System

```
Decision Generated → Outcome Tracked → Calibration Adjusted
       ↑                                        │
       └────────────────────────────────────────┘
```

---

## 11. Development Guidelines

### 11.1 NEVER Output From OMEN

```python
# ❌ WRONG - OMEN should never output these
risk_level: "HIGH"
overall_risk: 0.8
risk_status: "CRITICAL"

# ✅ CORRECT - OMEN only outputs signals
probability: 0.78      # Event likelihood
confidence_score: 0.85 # Data quality
```

### 11.2 ALWAYS Include In RISKCAST Output

```python
# ❌ WRONG - Vague, useless
"Consider alternative routes"
"Significant impact expected"
"Risk level: HIGH"

# ✅ CORRECT - Specific, actionable
"REROUTE shipment PO-4521 via Cape with MSC"
"Cost: $8,500. Deadline: Feb 5, 6PM UTC"
"If wait 24h: cost becomes $15,000"
```

### 11.3 Code Patterns

```python
# Use Pydantic v2 patterns
from pydantic import BaseModel, Field, computed_field

class MyModel(BaseModel):
    value: float = Field(ge=0, description="Must be non-negative")
    
    @computed_field
    @property
    def derived(self) -> str:
        return f"Value: {self.value}"

# Use structlog for logging
import structlog
logger = structlog.get_logger(__name__)

logger.info(
    "event_name",
    field1=value1,
    field2=value2,
)

# Use httpx for async HTTP (NOT requests)
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### 11.4 Error Handling

```python
class RiskCastError(Exception):
    """Base exception for RISKCAST."""
    pass

class NoExposureError(RiskCastError):
    """Customer has no affected shipments."""
    pass

class InsufficientDataError(RiskCastError):
    """Not enough data to generate decision."""
    pass
```

---

## 12. Constants & Configuration Reference

### 12.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Optional |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | Required for alerts |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | Required for alerts |
| `ENCRYPTION_KEY` | AES-256 key for PII encryption | Required |
| `LOG_LEVEL` | Logging level | INFO |
| `ENVIRONMENT` | Environment name | development |

### 12.2 Timing Constants

```python
BOOKING_DEADLINE_HOURS = 48    # Hours before departure
DECISION_TTL_HOURS = 24        # Decision validity
```

### 12.3 Insurance Constants

```python
INSURANCE_PREMIUM_RATE = 0.0075  # 0.75% of cargo value
INSURANCE_COVERAGE_PCT = 0.80    # 80% of losses covered
```

---

## Appendix: Example DecisionObject

```json
{
  "decision_id": "dec_20240205143022_cust_abc",
  "customer_id": "cust_abc123",
  "signal_id": "OMEN-RS-2024-001",
  "schema_version": "2.1.0",
  
  "q1_what": {
    "event_type": "DISRUPTION",
    "event_summary": "Red Sea disruption affecting your Shanghai→Rotterdam route",
    "affected_chokepoint": "red_sea",
    "affected_routes": ["CNSHA-NLRTM"],
    "affected_shipments": ["PO-4521", "PO-4522"]
  },
  
  "q2_when": {
    "status": "CONFIRMED",
    "impact_timeline": "Impact starts in 3 days for your earliest shipment",
    "urgency": "immediate",
    "urgency_reason": "Disruption confirmed, carriers already rerouting"
  },
  
  "q3_severity": {
    "total_exposure_usd": 235000,
    "exposure_ci_90": [188000, 294000],
    "expected_delay_days": 12,
    "delay_range": "10-14 days",
    "severity": "critical",
    "shipments_affected": 2
  },
  
  "q4_why": {
    "root_cause": "Houthi attacks on commercial vessels",
    "causal_chain": [
      "Houthi attacks detected",
      "Carriers avoiding Red Sea",
      "Rerouting via Cape of Good Hope",
      "10-14 day additional transit"
    ],
    "evidence_summary": "78% signal probability | 47 vessels rerouting",
    "sources": ["Polymarket", "MarineTraffic", "Reuters"]
  },
  
  "q5_action": {
    "action_type": "REROUTE",
    "action_summary": "Reroute 2 shipments via Cape with MSC",
    "estimated_cost_usd": 8500,
    "cost_ci_90": [7200, 10100],
    "deadline": "2024-02-05T18:00:00Z",
    "deadline_reason": "Booking window closes for next Cape departure",
    "recommended_carrier": "MSCU",
    "execution_steps": [
      "Contact MSC booking at bookings@msc.com",
      "Request reroute via Cape of Good Hope",
      "Confirm new ETA with your customer"
    ]
  },
  
  "q6_confidence": {
    "score": 0.87,
    "level": "high",
    "factors": {
      "signal_probability": 0.78,
      "intelligence_correlation": 0.90,
      "impact_assessment": 0.85
    },
    "explanation": "87% confidence based on market probability and 47 vessels already rerouting"
  },
  
  "q7_inaction": {
    "expected_loss_if_nothing": 47000,
    "loss_ci_90": [38000, 59000],
    "cost_if_wait_6h": 51700,
    "cost_if_wait_24h": 61100,
    "cost_if_wait_48h": 70500,
    "point_of_no_return": "2024-02-06T18:00:00Z",
    "point_of_no_return_reason": "Next Cape departure booking closes",
    "inaction_summary": "Point of no return in 24h. Expected loss: $47,000"
  },
  
  "generated_at": "2024-02-05T14:30:22Z",
  "expires_at": "2024-02-06T14:30:22Z"
}
```

---

**Document End**

*"OMEN sees the future. RISKCAST tells you what to DO."*
