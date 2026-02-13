# RISKCAST Architecture - C4 Diagrams

## Overview

This document provides C4 model architecture diagrams for the RISKCAST Decision Intelligence Platform.

---

## Level 1: System Context

```mermaid
C4Context
    title System Context Diagram for RISKCAST

    Person(customer, "Supply Chain Manager", "Makes routing decisions for shipments")
    Person(ops, "Operations Team", "Monitors system health and alerts")
    
    System(riskcast, "RISKCAST", "Decision Intelligence Platform for supply chain risk management")
    
    System_Ext(polymarket, "Polymarket", "Prediction market data source")
    System_Ext(news, "News APIs", "News and event data sources")
    System_Ext(ais, "AIS Providers", "Vessel tracking data")
    System_Ext(rates, "Freight Rate APIs", "Real-time shipping rates")
    System_Ext(whatsapp, "WhatsApp Business", "Alert delivery channel")
    
    Rel(customer, riskcast, "Receives decisions, acknowledges alerts")
    Rel(ops, riskcast, "Monitors, configures")
    Rel(riskcast, polymarket, "Fetches prediction data")
    Rel(riskcast, news, "Fetches news signals")
    Rel(riskcast, ais, "Tracks vessels")
    Rel(riskcast, rates, "Gets freight rates")
    Rel(riskcast, whatsapp, "Sends alerts")
```

### Context Description

RISKCAST is a decision intelligence platform that:
- **Ingests** signals from multiple external data sources (prediction markets, news, AIS, rates)
- **Correlates** signals with customer shipment data
- **Generates** personalized, actionable decisions
- **Delivers** alerts via WhatsApp with specific costs, deadlines, and inaction consequences

---

## Level 2: Container Diagram

```mermaid
C4Container
    title Container Diagram for RISKCAST

    Person(customer, "Customer")
    
    Container_Boundary(riskcast, "RISKCAST Platform") {
        Container(api, "API Gateway", "FastAPI", "REST API endpoints, authentication, rate limiting")
        Container(omen, "OMEN Engine", "Python", "Signal detection and validation")
        Container(oracle, "ORACLE Engine", "Python", "Reality correlation and market data")
        Container(decision, "RISKCAST Engine", "Python", "Decision generation - THE MOAT")
        Container(alerter, "Alerter Service", "Python", "Alert formatting and delivery")
        Container(scheduler, "Task Scheduler", "Celery/APScheduler", "Periodic tasks and background jobs")
        
        ContainerDb(postgres, "PostgreSQL", "Database", "Customer data, decisions, shipments")
        ContainerDb(redis, "Redis", "Cache/Queue", "Caching, rate limiting, pub/sub")
    }
    
    System_Ext(external, "External Data Sources")
    System_Ext(whatsapp, "WhatsApp")
    
    Rel(customer, api, "HTTPS/REST")
    Rel(api, omen, "Internal")
    Rel(api, oracle, "Internal")
    Rel(api, decision, "Internal")
    Rel(api, alerter, "Internal")
    Rel(omen, external, "Fetches signals")
    Rel(oracle, external, "Fetches reality data")
    Rel(decision, postgres, "Reads/writes")
    Rel(alerter, whatsapp, "Sends messages")
    Rel_L(api, redis, "Cache/rate limit")
    Rel(scheduler, omen, "Triggers")
    Rel(scheduler, oracle, "Triggers")
```

### Container Descriptions

| Container | Purpose | Technology |
|-----------|---------|------------|
| **API Gateway** | Entry point for all requests, authentication, rate limiting | FastAPI, Pydantic |
| **OMEN Engine** | Detects and validates signals from external sources | Python, httpx |
| **ORACLE Engine** | Correlates signals with real-world data (AIS, rates) | Python, httpx |
| **RISKCAST Engine** | Generates personalized decisions (7 Questions) | Python, ML Pipeline |
| **Alerter Service** | Formats and delivers alerts | Python, WhatsApp API |
| **Task Scheduler** | Periodic data fetching, cleanup jobs | APScheduler |
| **PostgreSQL** | Persistent storage for all business data | PostgreSQL 15 |
| **Redis** | Caching, rate limiting, event pub/sub | Redis 7 |

---

## Level 3: Component Diagram - RISKCAST Engine

```mermaid
C4Component
    title Component Diagram for RISKCAST Decision Engine

    Container_Boundary(riskcast, "RISKCAST Engine") {
        Component(service, "RiskCastService", "Service", "Orchestrates decision generation pipeline")
        Component(matcher, "ExposureMatcher", "Component", "Matches signals to customer shipments")
        Component(calculator, "ImpactCalculator", "Component", "Calculates financial and time impact")
        Component(generator, "ActionGenerator", "Component", "Generates recommended actions")
        Component(tradeoff, "TradeOffAnalyzer", "Component", "Analyzes action trade-offs")
        Component(composer, "DecisionComposer", "Component", "Composes final decision with Q1-Q7")
        Component(ml, "MLPipeline", "Component", "ML predictions for delay/cost")
    }
    
    Container_Boundary(schemas, "Domain Schemas") {
        Component(customer_schema, "CustomerProfile", "Schema", "Customer and shipment data")
        Component(decision_schema, "DecisionObject", "Schema", "7 Questions output format")
        Component(impact_schema, "ImpactEstimate", "Schema", "Impact calculations")
        Component(action_schema, "Action", "Schema", "Recommended actions")
    }
    
    Rel(service, matcher, "Uses")
    Rel(service, calculator, "Uses")
    Rel(service, generator, "Uses")
    Rel(service, tradeoff, "Uses")
    Rel(service, composer, "Uses")
    Rel(calculator, ml, "Uses predictions")
    Rel(matcher, customer_schema, "Uses")
    Rel(composer, decision_schema, "Produces")
    Rel(calculator, impact_schema, "Produces")
    Rel(generator, action_schema, "Produces")
```

### Decision Generation Pipeline

```
1. ExposureMatcher
   - Input: Signal + CustomerProfile
   - Output: List of affected shipments with exposure amounts

2. ImpactCalculator
   - Input: Affected shipments + Signal severity
   - Output: ImpactEstimate (cost in USD, delay in days)

3. ActionGenerator
   - Input: ImpactEstimate + Customer preferences
   - Output: Ranked list of Actions

4. TradeOffAnalyzer
   - Input: Actions list
   - Output: Actions with trade-off analysis

5. DecisionComposer
   - Input: All above
   - Output: DecisionObject (7 Questions answered)
```

---

## Level 3: Component Diagram - OMEN Engine

```mermaid
C4Component
    title Component Diagram for OMEN Signal Engine

    Container_Boundary(omen, "OMEN Engine") {
        Component(service, "OmenService", "Service", "Orchestrates signal detection")
        
        Component_Boundary(sources, "Signal Sources") {
            Component(polymarket, "PolymarketSource", "Source", "Prediction market signals")
            Component(news, "NewsSource", "Source", "News-based signals")
            Component(social, "SocialSource", "Source", "Social media signals")
        }
        
        Component_Boundary(validators, "Validators") {
            Component(freshness, "FreshnessValidator", "Validator", "Checks signal recency")
            Component(confidence, "ConfidenceValidator", "Validator", "Validates data quality")
            Component(duplicate, "DuplicateValidator", "Validator", "Deduplicates signals")
            Component(relevance, "RelevanceValidator", "Validator", "Checks chokepoint relevance")
        }
        
        Component(aggregator, "SignalAggregator", "Component", "Combines multi-source signals")
    }
    
    Rel(service, polymarket, "Fetches")
    Rel(service, news, "Fetches")
    Rel(service, social, "Fetches")
    Rel(service, freshness, "Validates")
    Rel(service, confidence, "Validates")
    Rel(service, duplicate, "Validates")
    Rel(service, relevance, "Validates")
    Rel(service, aggregator, "Aggregates")
```

---

## Level 4: Code Diagram - Decision Object

```mermaid
classDiagram
    class DecisionObject {
        +str decision_id
        +str customer_id
        +str signal_id
        +Q1What q1_what
        +Q2When q2_when
        +Q3Severity q3_severity
        +Q4Why q4_why
        +Q5Action q5_action
        +Q6Confidence q6_confidence
        +Q7Inaction q7_inaction
        +datetime created_at
        +datetime expires_at
        +to_whatsapp_message() str
    }
    
    class Q1What {
        +str event_description
        +str personalized_summary
        +list~str~ affected_shipments
    }
    
    class Q2When {
        +datetime event_time
        +datetime decision_deadline
        +Urgency urgency
        +int hours_until_deadline
    }
    
    class Q3Severity {
        +Decimal exposure_usd
        +int delay_days
        +int affected_shipments
        +str severity_level
    }
    
    class Q5Action {
        +ActionType action_type
        +str specific_instruction
        +Decimal estimated_cost_usd
        +datetime deadline
        +str carrier
        +str route
    }
    
    class Q7Inaction {
        +Decimal cost_usd
        +int additional_delay_days
        +datetime point_of_no_return
        +str consequence
    }
    
    DecisionObject --> Q1What
    DecisionObject --> Q2When
    DecisionObject --> Q3Severity
    DecisionObject --> Q5Action
    DecisionObject --> Q7Inaction
```

---

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph External["External Sources"]
        PM[Polymarket]
        NEWS[News APIs]
        AIS[AIS Tracking]
        RATES[Freight Rates]
    end
    
    subgraph OMEN["OMEN - Signals"]
        FETCH[Fetch Data]
        VALIDATE[Validate]
        SIGNAL[OmenSignal]
    end
    
    subgraph ORACLE["ORACLE - Reality"]
        TRACK[Vessel Tracking]
        MARKET[Market Data]
        CORRELATE[Correlate]
        INTEL[CorrelatedIntelligence]
    end
    
    subgraph RISKCAST["RISKCAST - Decisions"]
        MATCH[Match Exposure]
        IMPACT[Calculate Impact]
        ACTION[Generate Actions]
        COMPOSE[Compose Decision]
        DECISION[DecisionObject]
    end
    
    subgraph ALERTER["ALERTER - Delivery"]
        FORMAT[Format Message]
        DELIVER[Send WhatsApp]
    end
    
    PM --> FETCH
    NEWS --> FETCH
    FETCH --> VALIDATE
    VALIDATE --> SIGNAL
    
    AIS --> TRACK
    RATES --> MARKET
    SIGNAL --> CORRELATE
    TRACK --> CORRELATE
    MARKET --> CORRELATE
    CORRELATE --> INTEL
    
    INTEL --> MATCH
    MATCH --> IMPACT
    IMPACT --> ACTION
    ACTION --> COMPOSE
    COMPOSE --> DECISION
    
    DECISION --> FORMAT
    FORMAT --> DELIVER
```

---

## Deployment Diagram

```mermaid
C4Deployment
    title Deployment Diagram for RISKCAST (Production)

    Deployment_Node(aws, "AWS", "Cloud Provider") {
        Deployment_Node(vpc, "VPC", "Private Network") {
            Deployment_Node(ecs, "ECS Cluster", "Container Orchestration") {
                Container(api_container, "API Service", "FastAPI", "3 instances, auto-scaling")
                Container(worker_container, "Worker Service", "Celery", "2 instances")
            }
            
            Deployment_Node(rds, "RDS", "Managed Database") {
                ContainerDb(postgres, "PostgreSQL", "Primary + Read Replica")
            }
            
            Deployment_Node(elasticache, "ElastiCache", "Managed Redis") {
                ContainerDb(redis, "Redis Cluster", "3 node cluster")
            }
        }
        
        Deployment_Node(cloudfront, "CloudFront", "CDN") {
            Container(cdn, "CDN", "Edge caching")
        }
    }
    
    Deployment_Node(monitoring, "Monitoring") {
        Container(prometheus, "Prometheus", "Metrics")
        Container(grafana, "Grafana", "Dashboards")
        Container(sentry, "Sentry", "Error tracking")
    }
```

---

## Security Architecture

```mermaid
flowchart TB
    subgraph Public["Public Zone"]
        CLIENT[Customer App/Browser]
        CDN[CloudFront CDN]
    end
    
    subgraph DMZ["DMZ"]
        WAF[WAF]
        LB[Load Balancer]
    end
    
    subgraph Private["Private Zone"]
        API[API Gateway]
        subgraph Services["Application Services"]
            OMEN
            ORACLE
            RISKCAST
            ALERTER
        end
        subgraph Data["Data Layer"]
            POSTGRES[(PostgreSQL)]
            REDIS[(Redis)]
        end
    end
    
    subgraph Secrets["Secrets Management"]
        VAULT[AWS Secrets Manager]
    end
    
    CLIENT --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> API
    API --> Services
    Services --> Data
    Services --> VAULT
    
    style Public fill:#f9f,stroke:#333
    style DMZ fill:#ff9,stroke:#333
    style Private fill:#9f9,stroke:#333
    style Secrets fill:#99f,stroke:#333
```

### Security Layers

1. **Edge Security**
   - CloudFront for DDoS protection
   - WAF rules for common attacks
   - TLS 1.3 encryption

2. **Authentication**
   - API key authentication
   - JWT tokens for sessions
   - Role-based access control

3. **Data Protection**
   - Encryption at rest (AES-256)
   - Encryption in transit (TLS)
   - Field-level encryption for PII

4. **Network Security**
   - VPC isolation
   - Security groups
   - Private subnets for data layer

---

## References

- [C4 Model](https://c4model.com/)
- [RISKCAST Architecture Decision Records](./decisions/)
- [API Documentation](../api/)
