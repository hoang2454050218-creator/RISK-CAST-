# RISKCAST Decision Engine - Comprehensive Project Documentation

> **Tài liệu chi tiết dự án RISKCAST - Decision Intelligence Platform**
>
> Phiên bản: 2.0 | Cập nhật: 05/02/2026

---

## 📋 Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Các thành phần chi tiết](#3-các-thành-phần-chi-tiết)
4. [Data Models (Schemas)](#4-data-models-schemas)
5. [Pipeline xử lý](#5-pipeline-xử-lý)
6. [Công thức tính toán](#6-công-thức-tính-toán)
7. [Constants và Configurations](#7-constants-và-configurations)
8. [Tests](#8-tests)
9. [Trạng thái triển khai](#9-trạng-thái-triển-khai)
10. [Hướng dẫn mở rộng](#10-hướng-dẫn-mở-rộng)

---

## 1. Tổng quan dự án

### 1.1 Mục tiêu

**RISKCAST** là một **Decision Intelligence Platform** cho chuỗi cung ứng hàng hải. Khác với các hệ thống thông báo thông thường (chỉ báo "có sự kiện"), RISKCAST đưa ra **quyết định cụ thể** cho khách hàng.

```
NOTIFICATION SYSTEM:  "Red Sea disruption detected"
RISKCAST:             "REROUTE NOW via Cape. Cost: $8,500. Book by 6PM today."
```

### 1.2 Triết lý thiết kế

- **Personalization**: Mọi quyết định phải được cá nhân hóa theo ngữ cảnh của khách hàng
- **Actionable**: Không mô tả mơ hồ, phải có số liệu cụ thể ($, ngày, deadline)
- **7 Questions Format**: Mọi quyết định PHẢI trả lời 7 câu hỏi bắt buộc

### 1.3 The 7 Questions Format

| # | Câu hỏi | Mô tả | Ví dụ Output |
|---|---------|-------|--------------|
| Q1 | What's happening? | Sự kiện gì đang xảy ra (personalized) | "Red Sea disruption affecting YOUR route SH→RTM" |
| Q2 | When? | Timeline + Urgency | "Impact starts in 3 days for shipment #4521" |
| Q3 | How bad? | Tổn thất $ và ngày trễ | "Exposure: $235K across 5 containers" |
| Q4 | Why? | Chuỗi nguyên nhân | "Houthi attacks → carriers avoiding Suez → +10 days" |
| Q5 | What to do? | Hành động cụ thể | "REROUTE via Cape. Cost: $8,500. Deadline: 6PM today" |
| Q6 | Confidence? | Độ tin cậy + nguồn | "87% based on Polymarket + 23 vessels rerouting" |
| Q7 | If nothing? | Hậu quả không hành động | "Wait 6h → cost +$15K. Wait 24h → booking closes" |

### 1.4 Tech Stack

- **Runtime**: Python 3.11+
- **Web Framework**: FastAPI
- **Data Validation**: Pydantic v2
- **Database**: PostgreSQL (planned), In-Memory (MVP)
- **Cache**: Redis (planned)
- **Logging**: structlog
- **Testing**: pytest
- **Delivery**: WhatsApp Business API (Twilio)

---

## 2. Kiến trúc hệ thống

### 2.1 High-Level Architecture

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
│   • Prediction      • AIS Data         • 7 Questions      • Templates      │
│   • Markets         • Freight Rates    • Personalized     • Multi-lang     │
│   • News/Social     • Port Metrics     • Actionable       • WhatsApp API   │
│   • Probability     • Correlation      • Deadlines        • Delivery       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 RISKCAST Internal Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       RISKCAST DECISION ENGINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: CorrelatedIntelligence + CustomerContext                            │
│         ↓                                                                   │
│  ┌──────────────────┐                                                       │
│  │ 1. ExposureMatcher│ → Which shipments are affected?                      │
│  └────────┬─────────┘                                                       │
│           ↓                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 2. ImpactCalculator│ → How much in $ and days?                           │
│  └────────┬─────────┘                                                       │
│           ↓                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 3. ActionGenerator│ → What are the options?                              │
│  └────────┬─────────┘                                                       │
│           ↓                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 4. TradeOffAnalyzer│ → What if I don't act?                              │
│  └────────┬─────────┘                                                       │
│           ↓                                                                 │
│  ┌──────────────────┐                                                       │
│  │ 5. DecisionComposer│ → Combine into Q1-Q7 format                         │
│  └────────┬─────────┘                                                       │
│           ↓                                                                 │
│  OUTPUT: DecisionObject (7 Questions answered)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Folder Structure

```
c:\Users\RIM\OneDrive\Desktop\RISK CAST V2\
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Application settings
│   │   └── database.py            # Database connections
│   ├── omen/
│   │   ├── __init__.py
│   │   └── schemas.py             # Signal data models
│   ├── oracle/
│   │   ├── __init__.py
│   │   └── schemas.py             # Reality data models
│   ├── riskcast/
│   │   ├── __init__.py            # Exports: RiskCastService
│   │   ├── constants.py           # Enums, thresholds, parameters
│   │   ├── service.py             # High-level API
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py        # CustomerProfile, Shipment, CustomerContext
│   │   │   ├── impact.py          # CostBreakdown, DelayEstimate, TotalImpact
│   │   │   ├── action.py          # Action, ActionSet, TradeOffAnalysis
│   │   │   └── decision.py        # Q1-Q7 models, DecisionObject
│   │   ├── matchers/
│   │   │   ├── __init__.py
│   │   │   └── exposure.py        # ExposureMatcher, ExposureMatch
│   │   ├── calculators/
│   │   │   ├── __init__.py
│   │   │   └── impact.py          # ImpactCalculator
│   │   ├── generators/
│   │   │   ├── __init__.py
│   │   │   ├── action.py          # ActionGenerator
│   │   │   └── tradeoff.py        # TradeOffAnalyzer
│   │   ├── composers/
│   │   │   ├── __init__.py
│   │   │   └── decision.py        # DecisionComposer
│   │   └── repos/
│   │       ├── __init__.py
│   │       └── customer.py        # InMemoryCustomerRepository
│   └── alerter/
│       └── __init__.py            # WhatsApp alerter (Week 4)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   └── test_riskcast/
│       ├── __init__.py
│       ├── test_customer.py       # 23 tests
│       ├── test_exposure.py       # 19 tests
│       ├── test_impact.py         # 21 tests
│       ├── test_action.py         # 14 tests
│       ├── test_tradeoff.py       # 15 tests
│       ├── test_decision.py       # 22 tests
│       ├── test_composer.py       # 18 tests
│       └── test_service.py        # 18 tests
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 3. Các thành phần chi tiết

### 3.1 OMEN - Signal Engine

**File**: `app/omen/schemas.py`

OMEN là engine thu thập và xử lý tín hiệu dự đoán. OMEN CHỈ xử lý signals, KHÔNG đưa ra quyết định.

**Key Models**:

| Model | Mô tả |
|-------|-------|
| `SignalCategory` | Enum: GEOPOLITICAL, WEATHER, INFRASTRUCTURE, LABOR, ECONOMIC, SECURITY |
| `Chokepoint` | Enum: RED_SEA, SUEZ, PANAMA, MALACCA, HORMUZ, GIBRALTAR, etc. |
| `EvidenceItem` | Một bằng chứng hỗ trợ signal (source, URL, probability, sentiment) |
| `GeographicScope` | Phạm vi địa lý (primary_chokepoint, regions, ports) |
| `TemporalScope` | Phạm vi thời gian (earliest_impact, latest_resolution, is_ongoing) |
| `OmenSignal` | Output chính của OMEN |

**QUAN TRỌNG về OmenSignal**:
- `probability` = EVENT LIKELIHOOD (từ prediction markets như Polymarket)
- `confidence_score` = DATA QUALITY (độ tin cậy của dữ liệu)

```python
# Ví dụ: High confidence + Low probability
# "We're sure it probably won't happen"

# Ví dụ: Low confidence + High probability
# "Unreliable data says it will happen"
```

### 3.2 ORACLE - Reality Engine

**File**: `app/oracle/schemas.py`

ORACLE cung cấp ground truth về thực tế đang xảy ra: AIS vessel tracking, freight rates, port congestion.

**Key Models**:

| Model | Mô tả |
|-------|-------|
| `CorrelationStatus` | Enum: CONFIRMED, MATERIALIZING, PREDICTED_NOT_OBSERVED, SURPRISE, NORMAL |
| `ChokepointHealth` | Metrics cho một chokepoint (vessels, rates, delays) |
| `VesselMovement` | AIS data cho một vessel |
| `RealitySnapshot` | Snapshot thực tế tại một thời điểm |
| `CorrelatedIntelligence` | **INPUT chính cho RISKCAST** - kết hợp Signal + Reality |

**CorrelationStatus giải thích**:
- `CONFIRMED`: Signal đang xảy ra thực sự (high probability + reality confirms)
- `MATERIALIZING`: Dấu hiệu ban đầu xuất hiện
- `PREDICTED_NOT_OBSERVED`: Signal tồn tại nhưng reality vẫn bình thường
- `SURPRISE`: Reality disruption mà không có signal trước
- `NORMAL`: Không có signal hoặc disruption đáng kể

### 3.3 RISKCAST - Decision Engine

#### 3.3.1 Customer Schemas (`app/riskcast/schemas/customer.py`)

**The MOAT** - Đây là lợi thế cạnh tranh của RISKCAST. Customer data là thứ biến generic alerts thành personalized decisions.

| Model | Mô tả | Key Fields |
|-------|-------|------------|
| `CustomerProfile` | Hồ sơ khách hàng | customer_id, company_name, primary_routes, relevant_chokepoints, risk_tolerance, primary_phone, language, timezone |
| `Shipment` | Một lô hàng | shipment_id, origin_port, destination_port, cargo_value_usd, etd, eta, container_count, has_delay_penalty, delay_penalty_per_day_usd |
| `CustomerContext` | Full context cho decision-making | profile, active_shipments, total_cargo_value_usd, total_teu |

**Validation Rules**:
- Phone: E.164 format (`+84901234567`)
- Ports: 5-char UN/LOCODE (`VNHCM`, `NLRTM`)
- Routes: Format `ORIGIN-DEST` (`VNHCM-NLRTM`)
- ETD phải trước ETA

**Computed Properties**:
- `teu_count`: Tự động tính từ container_type và container_count
- `route_chokepoints`: Tự động derive từ origin/destination
- `is_actionable`: True nếu status là BOOKED hoặc AT_PORT

#### 3.3.2 Impact Schemas (`app/riskcast/schemas/impact.py`)

Trả lời câu hỏi: "Bao nhiêu tiền và bao nhiêu ngày?"

| Model | Mô tả |
|-------|-------|
| `CostBreakdown` | Chi tiết chi phí: delay_holding, reroute_premium, rate_increase, penalty |
| `DelayEstimate` | Ước tính delay: min_days, max_days, expected_days, confidence |
| `ShipmentImpact` | Impact cho một shipment |
| `TotalImpact` | Aggregate impact cho tất cả shipments |

**KHÔNG CHẤP NHẬN**:
- "Significant impact expected" ❌
- "$47,500 expected loss, 10-14 days delay" ✅

#### 3.3.3 Action Schemas (`app/riskcast/schemas/action.py`)

Trả lời câu hỏi: "Các lựa chọn là gì?"

| Model | Mô tả |
|-------|-------|
| `ActionType` | Enum: REROUTE, DELAY, SPLIT, EXPEDITE, INSURE, MONITOR, DO_NOTHING |
| `ActionFeasibility` | Enum: HIGH, MEDIUM, LOW, IMPOSSIBLE |
| `Action` | Một hành động cụ thể với steps, cost, deadline, carrier |
| `ActionSet` | Tập hợp actions, bao gồm primary_action và alternatives |
| `TimePoint` | Một điểm thời gian với cost tương ứng |
| `InactionConsequence` | Hậu quả của việc không hành động |
| `TradeOffAnalysis` | Phân tích trade-off hoàn chỉnh |

**KHÔNG CHẤP NHẬN**:
- "Consider rerouting" ❌
- "REROUTE via Cape with MSC. Cost: $8,500. Book by Feb 5, 6PM UTC." ✅

#### 3.3.4 Decision Schemas (`app/riskcast/schemas/decision.py`)

**THE FINAL OUTPUT OF RISKCAST**

| Model | Mô tả |
|-------|-------|
| `Q1WhatIsHappening` | Sự kiện gì đang xảy ra (personalized) |
| `Q2WhenWillItHappen` | Timeline và urgency |
| `Q3HowBadIsIt` | $ exposure và delay |
| `Q4WhyIsThisHappening` | Causal chain |
| `Q5WhatToDoNow` | Action cụ thể |
| `Q6HowConfident` | Confidence với factors |
| `Q7WhatIfNothing` | Inaction consequences |
| `DecisionObject` | Kết hợp tất cả Q1-Q7 |

**DecisionObject computed properties**:
- `is_expired`: True nếu quá expires_at
- `is_actionable`: True nếu action_type không phải DO_NOTHING hoặc MONITOR
- `get_summary()`: One-line summary
- `get_inaction_warning()`: Warning về hậu quả không hành động

### 3.4 Matchers

#### ExposureMatcher (`app/riskcast/matchers/exposure.py`)

**Nhiệm vụ**: Tìm shipments nào bị ảnh hưởng bởi signal.

**Logic**:
1. Lấy chokepoint từ signal
2. Tìm shipments đi qua chokepoint đó
3. Filter theo timing (có overlap với event window không?)
4. Filter theo status (chưa delivered/cancelled)
5. Tính total exposure và confidence

**Output**: `ExposureMatch` với affected_shipments, total_exposure_usd, confidence

### 3.5 Calculators

#### ImpactCalculator (`app/riskcast/calculators/impact.py`)

**Nhiệm vụ**: Tính toán impact tài chính và thời gian.

**Tính toán cho mỗi shipment**:
- Delay: min/max/expected days dựa trên chokepoint params
- Holding cost: cargo_value * holding_rate * delay_days
- Reroute cost: teu_count * reroute_cost_per_teu
- Penalty: (delay_days - penalty_free_days) * daily_penalty

**Output**: `TotalImpact` với per-shipment breakdowns

### 3.6 Generators

#### ActionGenerator (`app/riskcast/generators/action.py`)

**Nhiệm vụ**: Tạo các options hành động cụ thể.

**Actions được generate**:
1. **REROUTE**: Đổi route, có carrier recommendation, cost, deadline
2. **DELAY**: Giữ hàng tại origin
3. **INSURE**: Mua bảo hiểm
4. **MONITOR**: Theo dõi (khi confidence thấp)
5. **DO_NOTHING**: Baseline để so sánh

**Ranking by utility score**:
```
utility = (risk_mitigated / (cost + 1)) * feasibility_factor * urgency_factor
```

#### TradeOffAnalyzer (`app/riskcast/generators/tradeoff.py`)

**Nhiệm vụ**: Phân tích hậu quả của inaction và time-based cost escalation.

**Output bao gồm**:
- Cost escalation: cost_at_6h, cost_at_24h, cost_at_48h
- Point of no return: Thời điểm mà options bị severely limited
- Worst case scenario
- Recommended action với lý do

### 3.7 Composers

#### DecisionComposer (`app/riskcast/composers/decision.py`)

**Nhiệm vụ**: Orchestrate tất cả components thành một DecisionObject hoàn chỉnh.

**Pipeline**:
```python
def compose(intelligence, context):
    # Step 1: Match exposure
    exposure = self.exposure_matcher.match(intelligence, context)
    if not exposure.has_exposure:
        return None
    
    # Step 2: Calculate impact
    impact = self.impact_calculator.calculate(exposure, intelligence, context)
    
    # Step 3: Generate actions
    action_set = self.action_generator.generate(exposure, impact, intelligence, context)
    
    # Step 4: Analyze trade-offs
    tradeoff = self.tradeoff_analyzer.analyze(action_set, impact, exposure, intelligence)
    
    # Step 5: Compose 7 questions
    q1 = self._compose_q1(exposure, intelligence, context)
    q2 = self._compose_q2(exposure, impact, intelligence, tradeoff)
    q3 = self._compose_q3(impact, exposure)
    q4 = self._compose_q4(intelligence)
    q5 = self._compose_q5(action_set, tradeoff)
    q6 = self._compose_q6(impact, intelligence, action_set)
    q7 = self._compose_q7(tradeoff, impact)
    
    # Step 6: Build DecisionObject
    return DecisionObject(...)
```

### 3.8 Service Layer

#### RiskCastService (`app/riskcast/service.py`)

**Nhiệm vụ**: High-level API cho external consumers.

**Main Operations**:

| Method | Mô tả |
|--------|-------|
| `process_signal(intelligence)` | Broadcast mode: Generate decisions cho TẤT CẢ affected customers |
| `process_signal_for_customer(intelligence, customer_id)` | Targeted mode: Generate decision cho MỘT customer |
| `get_decision(decision_id)` | Lấy decision theo ID |
| `get_decisions_for_customer(customer_id)` | Lấy tất cả decisions của customer |
| `record_action_taken(decision_id)` | Ghi nhận user đã hành động |
| `record_feedback(decision_id, feedback)` | Ghi nhận feedback |
| `get_summary()` | Statistics |

**InMemoryDecisionStore** (MVP):
- Lưu trữ decisions trong memory
- Index theo customer_id và signal_id
- Support filter expired decisions

### 3.9 Repositories

#### CustomerRepository (`app/riskcast/repos/customer.py`)

**Nhiệm vụ**: Data access layer cho customer data.

**Interface**:
```python
class CustomerRepository(Protocol):
    async def get_profile(customer_id: str) -> Optional[CustomerProfile]
    async def get_shipments(customer_id: str) -> list[Shipment]
    async def get_context(customer_id: str) -> Optional[CustomerContext]
    async def get_all_contexts() -> list[CustomerContext]
```

**InMemoryCustomerRepository** (MVP):
- Lưu profiles và shipments trong memory
- Có synchronous wrappers cho MVP use case

---

## 4. Data Models (Schemas)

### 4.1 Enums Summary

| Enum | Values | File |
|------|--------|------|
| `SignalCategory` | GEOPOLITICAL, WEATHER, INFRASTRUCTURE, LABOR, ECONOMIC, SECURITY, OTHER | omen/schemas.py |
| `Chokepoint` | RED_SEA, SUEZ, PANAMA, MALACCA, HORMUZ, GIBRALTAR, DOVER, BOSPHORUS | omen/schemas.py |
| `CorrelationStatus` | CONFIRMED, MATERIALIZING, PREDICTED_NOT_OBSERVED, SURPRISE, NORMAL | oracle/schemas.py |
| `ActionType` | REROUTE, DELAY, SPLIT, EXPEDITE, INSURE, MONITOR, DO_NOTHING | riskcast/constants.py |
| `ActionFeasibility` | HIGH, MEDIUM, LOW, IMPOSSIBLE | riskcast/schemas/action.py |
| `Urgency` | IMMEDIATE, URGENT, SOON, WATCH | riskcast/constants.py |
| `Severity` | LOW, MEDIUM, HIGH, CRITICAL | riskcast/constants.py |
| `RiskTolerance` | CONSERVATIVE, BALANCED, AGGRESSIVE | riskcast/constants.py |
| `ShipmentStatus` | BOOKED, IN_TRANSIT, AT_PORT, DELIVERED, CANCELLED | riskcast/constants.py |
| `ConfidenceLevel` | HIGH, MEDIUM, LOW | riskcast/constants.py |

### 4.2 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  External Data Sources                                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  Polymarket   │  │    Reuters    │  │   AIS Data    │                   │
│  │  (probability)│  │    (news)     │  │   (vessels)   │                   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘                   │
│          │                  │                  │                            │
│          ▼                  ▼                  ▼                            │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                        OmenSignal                                │       │
│  │  - signal_id            - category                               │       │
│  │  - probability (0-1)    - confidence_score (0-1)                │       │
│  │  - geographic (chokepoints, regions, ports)                      │       │
│  │  - temporal (earliest_impact, latest_resolution)                 │       │
│  │  - evidence[] (sources, URLs, snippets)                          │       │
│  └───────────────────────────────┬─────────────────────────────────┘       │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                   CorrelatedIntelligence                         │       │
│  │  - signal (OmenSignal)                                           │       │
│  │  - reality (RealitySnapshot: vessels, rates, delays)             │       │
│  │  - correlation_status (CONFIRMED/MATERIALIZING/etc)              │       │
│  │  - combined_confidence (0-1)                                     │       │
│  └───────────────────────────────┬─────────────────────────────────┘       │
│                                  │                                          │
│  Customer Data                   │                                          │
│  ┌───────────────────────────────┼─────────────────────────────────┐       │
│  │                               │                                  │       │
│  │  CustomerProfile              │      Shipment[]                  │       │
│  │  - customer_id                │      - shipment_id               │       │
│  │  - primary_routes             │      - origin_port               │       │
│  │  - risk_tolerance             │      - destination_port          │       │
│  │  - language                   │      - cargo_value_usd           │       │
│  │                               │      - etd, eta                  │       │
│  │                               ▼      - has_delay_penalty         │       │
│  │              ┌────────────────────────────────────┐              │       │
│  │              │         CustomerContext            │              │       │
│  │              │  - profile                         │              │       │
│  │              │  - active_shipments                │              │       │
│  │              │  - total_cargo_value_usd           │              │       │
│  │              └──────────────────┬─────────────────┘              │       │
│  └─────────────────────────────────┼───────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    RISKCAST PIPELINE                             │       │
│  │                                                                  │       │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │       │
│  │  │ Exposure    │───▶│   Impact    │───▶│   Action    │          │       │
│  │  │  Matcher    │    │ Calculator  │    │  Generator  │          │       │
│  │  └─────────────┘    └─────────────┘    └──────┬──────┘          │       │
│  │        │                  │                   │                  │       │
│  │        ▼                  ▼                   ▼                  │       │
│  │  ExposureMatch      TotalImpact          ActionSet              │       │
│  │                                               │                  │       │
│  │                    ┌──────────────────────────┘                  │       │
│  │                    ▼                                             │       │
│  │            ┌─────────────┐                                       │       │
│  │            │  TradeOff   │                                       │       │
│  │            │  Analyzer   │                                       │       │
│  │            └──────┬──────┘                                       │       │
│  │                   │                                              │       │
│  │                   ▼                                              │       │
│  │            TradeOffAnalysis                                      │       │
│  │                   │                                              │       │
│  │                   ▼                                              │       │
│  │            ┌─────────────┐                                       │       │
│  │            │  Decision   │                                       │       │
│  │            │  Composer   │                                       │       │
│  │            └──────┬──────┘                                       │       │
│  │                   │                                              │       │
│  └───────────────────┼──────────────────────────────────────────────┘       │
│                      │                                                      │
│                      ▼                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      DecisionObject                              │       │
│  │                                                                  │       │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐                 │       │
│  │  │   Q1   │  │   Q2   │  │   Q3   │  │   Q4   │                 │       │
│  │  │ What?  │  │ When?  │  │ Bad?   │  │  Why?  │                 │       │
│  │  └────────┘  └────────┘  └────────┘  └────────┘                 │       │
│  │                                                                  │       │
│  │  ┌────────┐  ┌────────┐  ┌────────┐                             │       │
│  │  │   Q5   │  │   Q6   │  │   Q7   │                             │       │
│  │  │ What   │  │ Conf?  │  │  If    │                             │       │
│  │  │  Do?   │  │        │  │Nothing?│                             │       │
│  │  └────────┘  └────────┘  └────────┘                             │       │
│  │                                                                  │       │
│  │  + alternative_actions[]                                         │       │
│  │  + expires_at                                                    │       │
│  │  + was_acted_upon, user_feedback                                 │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Pipeline xử lý

### 5.1 Signal Processing Flow

```python
# 1. Signal arrives from OMEN
signal = OmenSignal(
    signal_id="OMEN-RS-2024-001",
    title="Red Sea shipping disruption - Houthi attacks",
    category=SignalCategory.GEOPOLITICAL,
    probability=0.78,  # From Polymarket
    confidence_score=0.85,  # Data quality
    geographic=GeographicScope(
        primary_chokepoint=Chokepoint.RED_SEA,
        affected_regions=["Middle East", "Red Sea"]
    ),
    temporal=TemporalScope(
        earliest_impact=datetime.now(),
        latest_resolution=datetime.now() + timedelta(days=30)
    ),
    evidence=[...]
)

# 2. ORACLE correlates with reality
intelligence = CorrelatedIntelligence(
    signal=signal,
    reality=RealitySnapshot(
        chokepoint_health={
            "red_sea": ChokepointHealth(
                vessels_waiting=50,
                rerouting_count=23,
                rate_premium_pct=0.35
            )
        }
    ),
    correlation_status=CorrelationStatus.CONFIRMED,
    combined_confidence=0.87
)

# 3. RISKCAST processes for all customers
service = RiskCastService()
decisions = service.process_signal(intelligence)

# 4. Each decision answers 7 questions
for decision in decisions:
    print(f"Customer: {decision.customer_id}")
    print(f"Q1: {decision.q1_what.event_summary}")
    print(f"Q2: {decision.q2_when.urgency}")
    print(f"Q3: ${decision.q3_severity.total_exposure_usd:,.0f}")
    print(f"Q4: {' → '.join(decision.q4_why.causal_chain)}")
    print(f"Q5: {decision.q5_action.action_summary}")
    print(f"Q6: {decision.q6_confidence.score_pct}")
    print(f"Q7: ${decision.q7_inaction.expected_loss_if_nothing:,.0f}")
```

---

## 6. Công thức tính toán

### 6.1 Delay Estimation

```python
delay_days = chokepoint_params['reroute_delay_days']  # (min, max)
expected_delay = (min_delay + max_delay) / 2
confidence_adjusted = expected_delay * (1 - (1 - signal_confidence) * 0.3)
```

### 6.2 Cost Breakdown

```python
# Holding cost (cargo sitting in delay)
holding_cost = cargo_value_usd * holding_cost_per_day_pct * delay_days

# Reroute premium
reroute_cost = teu_count * reroute_cost_per_teu

# Rate increase
rate_increase = teu_count * (current_rate - baseline_rate)

# Penalty cost
if delay_days > penalty_free_days:
    penalty = (delay_days - penalty_free_days) * daily_penalty_usd
else:
    penalty = 0

# Total
total_cost = holding_cost + reroute_cost + rate_increase + penalty
```

### 6.3 Severity Classification

| Level | Threshold (USD) |
|-------|-----------------|
| LOW | < $5,000 |
| MEDIUM | $5,000 - $25,000 |
| HIGH | $25,000 - $100,000 |
| CRITICAL | > $100,000 |

### 6.4 Confidence Calculation

```python
# Combined confidence = weighted average
combined = (
    0.40 * signal_probability +
    0.30 * intelligence_correlation +
    0.30 * impact_assessment_confidence
)

# Confidence level
if combined >= 0.80:
    level = HIGH
elif combined >= 0.60:
    level = MEDIUM
else:
    level = LOW
```

### 6.5 Inaction Cost Escalation

```python
ESCALATION_FACTORS = {
    6: 1.10,   # +10% after 6 hours
    24: 1.30,  # +30% after 24 hours
    48: 1.50,  # +50% after 48 hours
}

cost_at_6h = immediate_cost * 1.10
cost_at_24h = immediate_cost * 1.30
cost_at_48h = immediate_cost * 1.50
```

### 6.6 Action Utility Score

```python
utility = (
    (risk_mitigated / (cost + 1)) *
    feasibility_factor *
    urgency_factor *
    risk_tolerance_factor
)

# Where:
# - feasibility_factor: HIGH=1.0, MEDIUM=0.8, LOW=0.5
# - urgency_factor: IMMEDIATE=1.2, URGENT=1.1, SOON=1.0, WATCH=0.9
# - risk_tolerance_factor: 
#   CONSERVATIVE → prefer safety, accept higher cost
#   AGGRESSIVE → prefer cost savings, accept more risk
```

---

## 7. Constants và Configurations

### 7.1 Chokepoint Parameters

| Chokepoint | Reroute Delay | Reroute Cost/TEU | Alternative Route |
|------------|---------------|------------------|-------------------|
| Red Sea | 7-14 days | $2,500 | Cape of Good Hope |
| Suez | 7-14 days | $2,500 | Cape of Good Hope |
| Panama | 5-10 days | $2,000 | Suez Canal |
| Malacca | 2-4 days | $800 | Lombok Strait |
| Hormuz | 3-7 days | $1,500 | Overland pipeline |

### 7.2 Carrier Information

| Code | Name | Premium % | Capacity |
|------|------|-----------|----------|
| MSCU | MSC | 35% | High |
| MAEU | Maersk | 40% | High |
| CMDU | CMA CGM | 38% | Medium |
| COSU | COSCO | 32% | High |
| EGLV | Evergreen | 34% | Medium |
| HLCU | Hapag-Lloyd | 42% | Medium |
| ONEY | ONE | 36% | Medium |

### 7.3 TEU Conversion

| Container Type | TEU |
|----------------|-----|
| 20GP | 1.0 |
| 20HC | 1.0 |
| 40GP | 2.0 |
| 40HC | 2.0 |
| 45HC | 2.25 |
| 20RF, 40RF | 1.0, 2.0 |

### 7.4 Route Mappings

```python
# Asia → Europe (via Suez/Red Sea)
CNSHA-NLRTM → [malacca, red_sea, suez]
VNHCM-NLRTM → [malacca, red_sea, suez]
VNHCM-DEHAM → [malacca, red_sea, suez]

# Asia → US West Coast (Pacific direct)
CNSHA-USLAX → []  # No chokepoints

# Asia → US East Coast (via Suez)
CNSHA-USNYC → [malacca, red_sea, suez]
```

---

## 8. Tests

### 8.1 Test Summary

| Module | File | Tests | Mô tả |
|--------|------|-------|-------|
| Customer Schemas | test_customer.py | 23 | Profile, Shipment, Context validation |
| Exposure Matcher | test_exposure.py | 19 | Matching logic, confidence calculation |
| Impact Calculator | test_impact.py | 21 | Cost breakdown, delay estimation |
| Action Generator | test_action.py | 14 | Action creation, ranking, utility |
| TradeOff Analyzer | test_tradeoff.py | 15 | Cost escalation, deadlines |
| Decision Schemas | test_decision.py | 22 | Q1-Q7 models, DecisionObject |
| Decision Composer | test_composer.py | 18 | Full pipeline integration |
| RiskCast Service | test_service.py | 18 | Service layer, storage |
| **TOTAL** | | **150** | |

### 8.2 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific module
pytest tests/test_riskcast/test_composer.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_riskcast/test_decision.py::TestDecisionObject::test_all_questions_answered
```

### 8.3 Key Fixtures (conftest.py)

| Fixture | Mô tả |
|---------|-------|
| `sample_profile` | CustomerProfile mẫu |
| `sample_shipment` | Shipment mẫu với exposure to Red Sea |
| `sample_context` | CustomerContext với profile và shipments |
| `sample_signal` | OmenSignal về Red Sea disruption |
| `sample_intelligence` | CorrelatedIntelligence với status CONFIRMED |
| `sample_exposure` | ExposureMatch với affected shipments |
| `sample_impact` | TotalImpact với cost breakdown |
| `sample_action_set` | ActionSet với REROUTE và alternatives |
| `sample_tradeoff` | TradeOffAnalysis |
| `sample_decision` | Complete DecisionObject |

---

## 9. Trạng thái triển khai

### 9.1 Completed (Week 1-3)

| Component | Status | Tests |
|-----------|--------|-------|
| OMEN Schemas | ✅ | - |
| ORACLE Schemas | ✅ | - |
| Customer Schemas | ✅ | 23 |
| Impact Schemas | ✅ | 21 |
| Action Schemas | ✅ | 14 |
| Decision Schemas (Q1-Q7) | ✅ | 22 |
| ExposureMatcher | ✅ | 19 |
| ImpactCalculator | ✅ | 21 |
| ActionGenerator | ✅ | 14 |
| TradeOffAnalyzer | ✅ | 15 |
| DecisionComposer | ✅ | 18 |
| RiskCastService | ✅ | 18 |
| InMemoryCustomerRepository | ✅ | - |
| InMemoryDecisionStore | ✅ | - |

### 9.2 Pending (Week 4)

| Component | Status | Mô tả |
|-----------|--------|-------|
| DecisionTemplates | ⏳ | WhatsApp message templates |
| AlerterService | ⏳ | WhatsApp integration |
| NexusPipeline | ⏳ | End-to-end pipeline |
| Launch Checklist | ⏳ | Production readiness |

---

## 10. Hướng dẫn mở rộng

### 10.1 Thêm Chokepoint mới

```python
# 1. Thêm vào enum (omen/schemas.py)
class Chokepoint(str, Enum):
    ...
    NEW_CHOKEPOINT = "new_chokepoint"

# 2. Thêm parameters (riskcast/constants.py)
CHOKEPOINT_PARAMS["new_chokepoint"] = {
    "reroute_delay_days": (X, Y),
    "reroute_cost_per_teu": Z,
    "holding_cost_per_day_pct": 0.001,
    "alternative_route": "Alternative Name",
}

# 3. Thêm route mappings
ROUTE_CHOKEPOINTS[("ORIGIN", "DEST")] = ["...", "new_chokepoint"]
```

### 10.2 Thêm Action Type mới

```python
# 1. Thêm vào enum (riskcast/constants.py)
class ActionType(str, Enum):
    ...
    NEW_ACTION = "new_action"

# 2. Implement generation logic (riskcast/generators/action.py)
def _generate_new_action(self, exposure, impact, intelligence, context):
    ...
    return Action(
        action_id=f"act_new_{...}",
        action_type=ActionType.NEW_ACTION,
        ...
    )

# 3. Add to generate() method
def generate(self, ...):
    actions = []
    ...
    if should_generate_new_action:
        actions.append(self._generate_new_action(...))
    ...
```

### 10.3 Thêm Data Source mới

```python
# 1. Tạo evidence item mới
EvidenceItem(
    source="NewSource",
    source_type="new_source_type",
    title="...",
    probability=0.XX,  # if applicable
    ...
)

# 2. Update signal với evidence mới
signal.evidence.append(new_evidence)
```

### 10.4 Customize Customer Risk Tolerance

```python
# Trong ActionGenerator
def _compute_utility(self, action, context):
    risk_tolerance = context.profile.risk_tolerance
    
    if risk_tolerance == RiskTolerance.CONSERVATIVE:
        # Prioritize safety, accept higher cost
        return (risk_mitigated * 1.5) / (cost + 1)
    elif risk_tolerance == RiskTolerance.AGGRESSIVE:
        # Prioritize cost savings
        return (risk_mitigated) / (cost * 1.5 + 1)
    else:  # BALANCED
        return risk_mitigated / (cost + 1)
```

---

## Appendix A: Example DecisionObject JSON

```json
{
  "decision_id": "dec_20240205143022_cust_abc",
  "customer_id": "cust_abc123",
  "signal_id": "OMEN-RS-2024-001",
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
    "urgency_reason": "Disruption confirmed, act now"
  },
  "q3_severity": {
    "total_exposure_usd": 235000,
    "exposure_breakdown": {
      "cargo_at_risk": 200000,
      "potential_penalties": 35000
    },
    "expected_delay_days": 12,
    "delay_range": "10-14 days",
    "shipments_affected": 2,
    "severity": "critical"
  },
  "q4_why": {
    "root_cause": "Houthi attacks on commercial vessels",
    "causal_chain": [
      "Houthi attacks detected",
      "Affects Red Sea",
      "Carriers already rerouting",
      "Extended transit times expected"
    ],
    "evidence_summary": "78% signal probability | 87% combined confidence",
    "sources": ["Polymarket", "Reuters"]
  },
  "q5_action": {
    "action_type": "REROUTE",
    "action_summary": "Reroute 2 shipments via Cape with MSC",
    "affected_shipments": ["PO-4521", "PO-4522"],
    "recommended_carrier": "MSCU",
    "estimated_cost_usd": 8500,
    "execution_steps": [
      "Contact MSC booking at bookings@msc.com",
      "Request reroute via Cape of Good Hope",
      "Confirm new ETA with customer"
    ],
    "deadline": "2024-02-05T18:00:00Z",
    "deadline_reason": "Booking window closes for next Cape departure"
  },
  "q6_confidence": {
    "score": 0.87,
    "level": "high",
    "factors": {
      "signal_probability": 0.78,
      "intelligence_correlation": 0.90,
      "impact_assessment": 0.85
    },
    "explanation": "87% confidence, high signal probability, strong correlation with reality"
  },
  "q7_inaction": {
    "expected_loss_if_nothing": 47000,
    "cost_if_wait_6h": 51700,
    "cost_if_wait_24h": 61100,
    "cost_if_wait_48h": 70500,
    "point_of_no_return": "2024-02-06T18:00:00Z",
    "point_of_no_return_reason": "Next Cape departure booking closes",
    "worst_case_cost": 94000,
    "worst_case_scenario": "Full cargo value at risk plus penalties",
    "inaction_summary": "Point of no return in 24h. Expected loss: $47,000"
  },
  "alternative_actions": [
    {
      "action_type": "delay",
      "summary": "Hold shipments at origin for 7 days",
      "cost_usd": 5000,
      "benefit_usd": 25000
    },
    {
      "action_type": "insure",
      "summary": "Purchase additional insurance coverage",
      "cost_usd": 1500,
      "benefit_usd": 35000
    }
  ],
  "generated_at": "2024-02-05T14:30:22Z",
  "expires_at": "2024-02-06T14:30:22Z"
}
```

---

## Appendix B: API Usage Examples

### B.1 Process Signal (Broadcast)

```python
from app.riskcast import get_riskcast_service
from app.oracle.schemas import CorrelatedIntelligence

# Get service
service = get_riskcast_service()

# Process signal for all customers
decisions = service.process_signal(intelligence)

print(f"Generated {len(decisions)} decisions")
for d in decisions:
    print(f"- {d.customer_id}: {d.q5_action.action_summary}")
```

### B.2 Process for Specific Customer

```python
decision = service.process_signal_for_customer(
    intelligence=intelligence,
    customer_id="cust_abc123"
)

if decision:
    print(decision.get_summary())
else:
    print("No exposure for this customer")
```

### B.3 Record Feedback

```python
# Record that user acted
service.record_action_taken("dec_20240205143022_cust_abc")

# Record user feedback
service.record_feedback(
    "dec_20240205143022_cust_abc",
    "Rerouted successfully, saved $30K"
)
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-05
**Author**: AI Assistant
