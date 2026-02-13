# RISKCAST C4 Architecture Model

## Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           Supply Chain Ecosystem                            │
│                                                                             │
│  ┌─────────────┐        ┌─────────────────────┐        ┌─────────────┐     │
│  │   Freight   │        │                     │        │  Shipping   │     │
│  │  Forwarders │◄──────►│                     │◄──────►│   Lines     │     │
│  └─────────────┘        │                     │        └─────────────┘     │
│                         │      RISKCAST       │                             │
│  ┌─────────────┐        │   Decision Engine   │        ┌─────────────┐     │
│  │   Traders   │◄──────►│                     │◄──────►│   Insurers  │     │
│  └─────────────┘        │  (Nexus Platform)   │        └─────────────┘     │
│                         │                     │                             │
│  ┌─────────────┐        │                     │        ┌─────────────┐     │
│  │  Logistics  │◄──────►│                     │◄──────►│  Government │     │
│  │  Providers  │        └─────────────────────┘        │  Agencies   │     │
│  └─────────────┘                 │                     └─────────────┘     │
│                                  │                                          │
│                                  ▼                                          │
│                         ┌─────────────────┐                                 │
│                         │  External Data  │                                 │
│                         │    Sources      │                                 │
│                         └─────────────────┘                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### System Context Description

**RISKCAST** transforms supply chain disruption signals into actionable business decisions.

**Users:**
- Freight Forwarders: Need to make routing decisions
- Traders: Need to assess cargo risk exposure
- Logistics Providers: Need operational guidance
- Shipping Lines: Need capacity planning insights

**External Systems:**
- Polymarket: Prediction market data
- AIS Providers: Vessel tracking data
- News APIs: Event information
- Freight Rate Providers: Market rates

---

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RISKCAST Platform                              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           API Gateway                                 │  │
│  │                     (FastAPI + Authentication)                        │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         │                          │                          │            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐       │
│  │             │           │             │           │             │       │
│  │    OMEN     │──────────►│   ORACLE    │──────────►│  RISKCAST   │       │
│  │  (Signals)  │           │  (Reality)  │           │ (Decisions) │       │
│  │             │           │             │           │             │       │
│  └──────┬──────┘           └──────┬──────┘           └──────┬──────┘       │
│         │                          │                          │            │
│         │                          │                          │            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                            ALERTER                                   │   │
│  │                    (WhatsApp Delivery)                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         │                          │                          │            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐       │
│  │  PostgreSQL │           │    Redis    │           │   Message   │       │
│  │  (Persist)  │           │   (Cache)   │           │   Queue     │       │
│  └─────────────┘           └─────────────┘           └─────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Container Descriptions

| Container | Technology | Purpose |
|-----------|------------|---------|
| API Gateway | FastAPI | REST API, Authentication, Rate Limiting |
| OMEN | Python Service | Signal detection and validation |
| ORACLE | Python Service | Reality snapshot aggregation |
| RISKCAST | Python Service | Decision generation (THE MOAT) |
| ALERTER | Python Service | Message delivery via WhatsApp |
| PostgreSQL | PostgreSQL 15 | Customer data, decisions, audit logs |
| Redis | Redis 7 | Caching, rate limiting, sessions |
| Message Queue | (Future) | Async processing, event streaming |

---

## Level 3: Component Diagram - RISKCAST Service

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RISKCAST Decision Engine                          │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        RiskCastService (Orchestrator)                 │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│    ┌─────────────────────────────────┼─────────────────────────────────┐    │
│    │                                 │                                 │    │
│    ▼                                 ▼                                 ▼    │
│  ┌───────────────┐          ┌───────────────┐          ┌───────────────┐   │
│  │   Exposure    │          │    Impact     │          │    Action     │   │
│  │    Matcher    │─────────►│  Calculator   │─────────►│   Generator   │   │
│  └───────────────┘          └───────────────┘          └───────────────┘   │
│         │                          │                          │            │
│         │                          │                          │            │
│         │                          ▼                          │            │
│         │                  ┌───────────────┐                  │            │
│         │                  │   Trade-Off   │                  │            │
│         │                  │   Analyzer    │                  │            │
│         │                  └───────────────┘                  │            │
│         │                          │                          │            │
│         │                          ▼                          │            │
│         │                  ┌───────────────┐                  │            │
│         └─────────────────►│   Decision    │◄─────────────────┘            │
│                            │   Composer    │                               │
│                            │  (7 Questions)│                               │
│                            └───────────────┘                               │
│                                    │                                        │
│                                    ▼                                        │
│                            ┌───────────────┐                               │
│                            │  Decision     │                               │
│                            │   Object      │                               │
│                            └───────────────┘                               │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                              Schemas                                   │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │  │
│  │  │ Customer   │  │  Decision  │  │   Impact   │  │   Action   │       │  │
│  │  │  Profile   │  │   Object   │  │  Estimate  │  │    Type    │       │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component | Responsibility |
|-----------|---------------|
| RiskCastService | Orchestrates the decision pipeline |
| ExposureMatcher | Matches signals to customer shipments |
| ImpactCalculator | Calculates financial/operational impact |
| ActionGenerator | Generates possible actions with costs |
| TradeOffAnalyzer | Compares action alternatives |
| DecisionComposer | Composes the 7 Questions answer |

---

## Level 4: Code - Decision Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Decision Generation Flow                             │
│                                                                             │
│  Signal (from OMEN)                                                         │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     1. EXPOSURE MATCHING                             │   │
│  │                                                                      │   │
│  │   signal.chokepoints ∩ customer.shipments.routes                    │   │
│  │   → List[AffectedShipment]                                          │   │
│  │   → total_exposure_usd                                              │   │
│  │   → affected_teu_count                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     2. IMPACT CALCULATION                            │   │
│  │                                                                      │   │
│  │   For each shipment:                                                │   │
│  │   - delay_days = f(chokepoint, severity, congestion)               │   │
│  │   - cost_impact = f(delay, cargo_value, holding_cost)              │   │
│  │   - reroute_cost = f(teu, fuel_price, charter_rates)               │   │
│  │   → ImpactEstimate                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     3. ACTION GENERATION                             │   │
│  │                                                                      │   │
│  │   Generate actions:                                                 │   │
│  │   - REROUTE: alternative route + cost + timeline                   │   │
│  │   - DELAY: wait + projected cost if event resolves                 │   │
│  │   - INSURE: insurance cost + coverage                              │   │
│  │   - MONITOR: decision deadline + next check                        │   │
│  │   → List[Action]                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     4. TRADE-OFF ANALYSIS                            │   │
│  │                                                                      │   │
│  │   Compare actions on:                                               │   │
│  │   - Cost                                                            │   │
│  │   - Timeline                                                        │   │
│  │   - Risk                                                            │   │
│  │   - Reversibility                                                   │   │
│  │   → Ranked actions with trade-offs                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     5. DECISION COMPOSITION                          │   │
│  │                                                                      │   │
│  │   Q1: What is happening? → Personalized event summary               │   │
│  │   Q2: When? → Timeline + urgency                                    │   │
│  │   Q3: How bad? → $ exposure + delay days                           │   │
│  │   Q4: Why? → Causal chain + evidence                               │   │
│  │   Q5: What to do? → Specific action + cost + deadline              │   │
│  │   Q6: Confidence? → Score + factors + caveats                      │   │
│  │   Q7: If nothing? → Inaction cost + point of no return             │   │
│  │   → DecisionObject                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  DecisionObject                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow                                      │
│                                                                             │
│   External APIs                 RISKCAST                    Storage         │
│   ────────────                 ─────────                   ───────          │
│                                                                             │
│   ┌───────────┐                                                            │
│   │Polymarket │────┐                                                       │
│   └───────────┘    │                                                       │
│                    ▼                                                       │
│   ┌───────────┐  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐   │
│   │  News API │──►│  OMEN  │──►│ORACLE │──►│RISKCAST │──►│ PostgreSQL  │   │
│   └───────────┘  └────────┘  └────────┘  └──────────┘  └──────────────┘   │
│                    │                            │                          │
│   ┌───────────┐    │                            │                          │
│   │ AIS Data  │────┘                            │       ┌──────────────┐   │
│   └───────────┘                                 │       │    Redis     │   │
│                                                 └──────►│   (Cache)    │   │
│   ┌───────────┐                                         └──────────────┘   │
│   │  Freight  │────────────────────────────────►                          │
│   │   Rates   │                                                            │
│   └───────────┘                                                            │
│                                                                             │
│   Output:                                                                   │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                          WhatsApp                                     │ │
│   │   "Your shipment PO-4521 is affected by Red Sea disruption.          │ │
│   │    Impact: $235,000 across 5 containers.                             │ │
│   │    Recommended: REROUTE via Cape with MSC for $8,500.                │ │
│   │    Deadline: Feb 5, 6PM UTC. Delay cost: $15,000/day after."         │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AWS Production Architecture                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                              VPC                                     │   │
│  │                                                                      │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │                    Public Subnets                            │   │   │
│  │   │                                                              │   │   │
│  │   │   ┌───────────────┐    ┌───────────────┐                    │   │   │
│  │   │   │      ALB      │    │   NAT GW      │                    │   │   │
│  │   │   └───────────────┘    └───────────────┘                    │   │   │
│  │   │                                                              │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                              │                                       │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │                    Private Subnets                           │   │   │
│  │   │                                                              │   │   │
│  │   │   ┌─────────────────────────────────────────────────────┐   │   │   │
│  │   │   │                     EKS Cluster                      │   │   │   │
│  │   │   │                                                      │   │   │   │
│  │   │   │   ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │   │   │
│  │   │   │   │ API Pod │  │ API Pod │  │ API Pod │            │   │   │   │
│  │   │   │   └─────────┘  └─────────┘  └─────────┘            │   │   │   │
│  │   │   │                                                      │   │   │   │
│  │   │   └─────────────────────────────────────────────────────┘   │   │   │
│  │   │                                                              │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                              │                                       │   │
│  │   ┌─────────────────────────────────────────────────────────────┐   │   │
│  │   │                    Database Subnets                          │   │   │
│  │   │                                                              │   │   │
│  │   │   ┌───────────────┐    ┌───────────────┐                    │   │   │
│  │   │   │      RDS      │    │  ElastiCache  │                    │   │   │
│  │   │   │  (PostgreSQL) │    │   (Redis)     │                    │   │   │
│  │   │   └───────────────┘    └───────────────┘                    │   │   │
│  │   │                                                              │   │   │
│  │   └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   External Services:                                                        │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│   │  CloudWatch   │  │   Secrets     │  │     KMS       │                  │
│   │   (Logs)      │  │   Manager     │  │  (Encryption) │                  │
│   └───────────────┘  └───────────────┘  └───────────────┘                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Security Architecture                               │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                        Edge Layer                                  │    │
│   │                                                                    │    │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │    │
│   │   │  WAF    │  │  DDoS   │  │  TLS    │  │  Rate   │            │    │
│   │   │         │  │ Shield  │  │ 1.3     │  │ Limit   │            │    │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘            │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                │                                            │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                     Application Layer                              │    │
│   │                                                                    │    │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │    │
│   │   │ API Key │  │  RBAC   │  │ Input   │  │ Output  │            │    │
│   │   │  Auth   │  │         │  │ Valid.  │  │ Encod.  │            │    │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘            │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                │                                            │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                        Data Layer                                  │    │
│   │                                                                    │    │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │    │
│   │   │Encrypt  │  │  KMS    │  │ Secrets │  │  Audit  │            │    │
│   │   │ at Rest │  │ Keys    │  │ Manager │  │  Logs   │            │    │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘            │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API Framework | FastAPI | Async support, OpenAPI, type hints |
| Database | PostgreSQL | ACID compliance, JSON support |
| Cache | Redis | Performance, rate limiting |
| Deployment | Kubernetes | Scaling, self-healing |
| Cloud | AWS | Mature, comprehensive services |
| Auth | API Keys + JWT | B2B simplicity + future OAuth |
| Messaging | (Future) Kafka | Event sourcing, replay |
