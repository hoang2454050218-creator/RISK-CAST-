# RISKCAST Architecture Documentation

## Overview

RISKCAST is a Decision Intelligence Platform that transforms supply chain disruption signals into actionable decisions. The platform follows a clear pipeline architecture:

```
OMEN (Signals) → ORACLE (Reality) → RISKCAST (Decisions) → ALERTER (Delivery)
```

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                EXTERNAL SOURCES                              │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────
│   Polymarket    │   Marine AIS    │   News APIs     │   Freight Rates       │
│   (Predictions) │   (Vessels)     │   (Events)      │   (Market Data)       │
└────────┬────────┴────────┬────────┴────────┬────────┴──────────┬────────────┘
         │                 │                 │                   │
         ▼                 ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OMEN (Signal Engine)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Collectors  │→ │ Validators  │→ │ Correlator  │→ │ Signal Repository   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORACLE (Reality Engine)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ AIS Service │  │ Rate Service│  │ Port Service│  │ Reality Snapshot    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RISKCAST (Decision Engine)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Exposure     │→ │ Impact       │→ │ Action       │→ │ Decision        │  │
│  │ Matcher      │  │ Calculator   │  │ Generator    │  │ Composer        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Confidence Calibration                            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ Multi-Factor│→ │ Calibrator  │→ │ Outcome Tracker             │   │   │
│  │  │ Calculator  │  │             │  │ (Self-Improvement Loop)     │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────┬────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ALERTER (Delivery Engine)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Templates   │→ │ Formatter   │→ │ Twilio API  │→ │ WhatsApp            │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Signal Collection
   ├── Polymarket: Prediction market probabilities
   ├── Marine AIS: Vessel positions, routes
   ├── News: Event detection, sentiment
   └── Rates: Freight market conditions

2. Signal Processing (OMEN)
   ├── Validation: 4-stage validation pipeline
   ├── Correlation: Cross-source verification
   └── Output: OmenSignal with probability + confidence

3. Reality Correlation (ORACLE)
   ├── Vessel tracking at chokepoints
   ├── Current freight rates
   └── Output: RealitySnapshot with ground truth

4. Decision Generation (RISKCAST)
   ├── Match customer shipments to signals
   ├── Calculate personalized impact
   ├── Generate ranked actions
   └── Output: DecisionObject answering 7 Questions

5. Alert Delivery (ALERTER)
   ├── Format decision for WhatsApp
   ├── Apply cooldown rules
   └── Track delivery status
```

## Component Details

### Core Components

#### OMEN (Signal Engine)
- **Purpose**: Collect and validate disruption signals
- **Key Output**: `OmenSignal` with `probability` (event likelihood) and `confidence_score` (data quality)
- **Sources**: Polymarket, news feeds, AIS data

#### ORACLE (Reality Engine)  
- **Purpose**: Ground-truth validation with real-world data
- **Key Output**: `RealitySnapshot` with chokepoint health, vessel traffic
- **Integration**: AIS tracking, freight rate APIs

#### RISKCAST (Decision Engine)
- **Purpose**: Transform signals into personalized decisions
- **Key Output**: `DecisionObject` answering the 7 Questions
- **Critical Features**:
  - Exposure matching (customer shipments × signals)
  - Impact calculation ($ amounts, not percentages)
  - Action generation (specific, actionable, with deadlines)
  - Confidence calibration (self-improving accuracy)

#### ALERTER (Delivery Engine)
- **Purpose**: Deliver decisions to customers
- **Channel**: WhatsApp via Twilio
- **Features**: Templates, cooldowns, delivery tracking

### Infrastructure Components

#### Database Layer
- **PostgreSQL**: Customer data, shipments, decisions, outcomes
- **Redis**: Caching, rate limiting, session management
- **Migrations**: Alembic with async support

#### Security Layer
- **Authentication**: API keys with scopes (RBAC)
- **Encryption**: AES-256-GCM for PII fields
- **Rate Limiting**: Sliding window with Redis

#### Observability Layer
- **Metrics**: Prometheus (business + system metrics)
- **Tracing**: OpenTelemetry → Jaeger
- **Logging**: Structlog (JSON format)

#### Resilience Layer
- **Circuit Breakers**: Per external service
- **Retries**: Exponential backoff with jitter
- **Timeouts**: Configurable per operation
- **Bulkheads**: Resource isolation

## The 7 Questions Framework

Every decision MUST answer these questions:

| # | Question | Output |
|---|----------|--------|
| Q1 | What is happening? | Personalized event summary |
| Q2 | When? | Timeline + urgency level |
| Q3 | How bad? | $ exposure + delay days |
| Q4 | Why? | Evidence chain |
| Q5 | What to do? | Action + cost + deadline |
| Q6 | Confidence? | Score + factors + caveats |
| Q7 | If nothing? | Inaction cost + deadline |

## Self-Improvement Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    Outcome Tracking System                       │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Decision   │ →  │  Outcome    │ →  │  Calibration        │  │
│  │  Generated  │    │  Recorded   │    │  Adjustment         │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│         ↑                                        │               │
│         │                                        │               │
│         └────────────────────────────────────────┘               │
│                    Confidence Recalibration                      │
└─────────────────────────────────────────────────────────────────┘
```

**Flow**:
1. Generate decision with confidence score
2. Track customer action (followed recommendation or not)
3. Record actual outcome (cost, delay)
4. Compare prediction vs actual
5. Adjust confidence calibration for future decisions

## Deployment Architecture

### Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster (EKS)                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     riskcast Namespace                       ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ││
│  │  │  API Pods    │  │  API Pods    │  │  API Pods        │  ││
│  │  │  (replica 1) │  │  (replica 2) │  │  (replica 3)     │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  ││
│  │         │                 │                  │              ││
│  │         └─────────────────┼──────────────────┘              ││
│  │                           │                                 ││
│  │  ┌──────────────────────────────────────────────────────┐  ││
│  │  │                 Service (ClusterIP)                   │  ││
│  │  └──────────────────────────────────────────────────────┘  ││
│  │                           │                                 ││
│  │  ┌──────────────────────────────────────────────────────┐  ││
│  │  │              Ingress (NGINX + TLS)                    │  ││
│  │  └──────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    External Services                         ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ││
│  │  │  RDS         │  │  ElastiCache │  │  Secrets Manager │  ││
│  │  │  (PostgreSQL)│  │  (Redis)     │  │                  │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### High Availability Configuration

- **Replicas**: Minimum 3 pods (PDB ensures 2 always available)
- **HPA**: Auto-scale 3-20 based on CPU/memory/custom metrics
- **Pod Anti-Affinity**: Spread across nodes
- **Topology Spread**: Spread across availability zones
- **Database**: Multi-AZ RDS with automatic failover
- **Cache**: Redis cluster with automatic failover

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│                    Network Security                              │
│  ├── VPC isolation                                              │
│  ├── Private subnets for databases                              │
│  ├── Security groups (least privilege)                          │
│  └── Network policies (pod-to-pod)                              │
├─────────────────────────────────────────────────────────────────┤
│                    Application Security                          │
│  ├── API key authentication                                     │
│  ├── Scope-based authorization (RBAC)                           │
│  ├── Rate limiting (per customer, per endpoint)                 │
│  ├── Input validation (Pydantic)                                │
│  └── Security headers (HSTS, CSP, etc.)                         │
├─────────────────────────────────────────────────────────────────┤
│                    Data Security                                 │
│  ├── Encryption at rest (RDS, S3, EBS)                          │
│  ├── Encryption in transit (TLS 1.3)                            │
│  ├── PII field-level encryption (AES-256-GCM)                   │
│  └── Key rotation (KMS)                                         │
├─────────────────────────────────────────────────────────────────┤
│                    Container Security                            │
│  ├── Non-root user                                              │
│  ├── Read-only filesystem                                       │
│  ├── Dropped capabilities                                       │
│  └── Trivy vulnerability scanning                               │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic v2 |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Messaging | Twilio (WhatsApp) |
| Observability | Prometheus, OpenTelemetry, Jaeger |
| Container | Docker |
| Orchestration | Kubernetes (EKS) |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Cloud | AWS |

## Key Design Decisions

### 1. Separation of Concerns
- OMEN handles signal collection (what MIGHT happen)
- ORACLE provides ground truth (what IS happening)
- RISKCAST generates decisions (what to DO)
- ALERTER delivers notifications (how to INFORM)

### 2. Customer Data as Moat
- Personalization requires knowing customer shipments
- More data → better predictions → more value
- This compounds over time, creating defensibility

### 3. Self-Improving System
- Track every decision outcome
- Use outcomes to calibrate confidence
- Adjust recommendations based on historical accuracy

### 4. Production-First Design
- Circuit breakers prevent cascade failures
- Rate limiting protects resources
- PII encryption by default
- Comprehensive observability

## Future Considerations

### Phase 2 Roadmap
- Multi-chokepoint support (Panama, Malacca, Hormuz)
- Dashboard UI for decision visualization
- Insurance API integration for automated coverage
- Carrier booking integration for one-click actions
- ML-based routing optimization
