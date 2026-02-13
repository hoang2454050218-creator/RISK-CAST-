# RISKCAST Data Dictionary

## Overview

This document provides a comprehensive data dictionary for the RISKCAST platform, including all entities, attributes, relationships, and data quality rules.

---

## Core Entities

### 1. CustomerProfile

**Description**: Represents a customer organization using RISKCAST.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `customer_id` | UUID | Yes | Unique identifier | Primary key |
| `company_name` | String | Yes | Legal company name | Max 255 chars |
| `industry` | Enum | Yes | Industry classification | LOGISTICS, RETAIL, MANUFACTURING, etc. |
| `tier` | Enum | Yes | Subscription tier | FREE, STARTER, PROFESSIONAL, ENTERPRISE |
| `whatsapp_number` | String | Yes | Primary contact number | E.164 format |
| `email` | String | Yes | Primary contact email | Valid email format |
| `timezone` | String | Yes | Preferred timezone | IANA timezone |
| `alert_preferences` | JSON | No | Notification settings | Valid AlertPreferences |
| `onboarded_at` | DateTime | Yes | Onboarding timestamp | UTC |
| `active` | Boolean | Yes | Account status | Default: true |
| `created_at` | DateTime | Yes | Creation timestamp | UTC, auto-generated |
| `updated_at` | DateTime | Yes | Last update timestamp | UTC, auto-updated |

**Indexes**:
- Primary: `customer_id`
- Unique: `whatsapp_number`, `email`
- Index: `tier`, `active`

**Relationships**:
- One-to-Many: `Shipment`
- One-to-Many: `Decision`
- One-to-Many: `Alert`

---

### 2. Shipment

**Description**: An active shipment being tracked for a customer.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `shipment_id` | UUID | Yes | Unique identifier | Primary key |
| `customer_id` | UUID | Yes | Owning customer | Foreign key |
| `reference_number` | String | Yes | Customer's PO/reference | Max 100 chars |
| `cargo_value_usd` | Decimal | Yes | Total cargo value | >= 0, 2 decimal places |
| `container_count` | Integer | Yes | Number of containers | >= 1 |
| `container_type` | Enum | Yes | Container size | TEU_20, FEU_40, FEU_40HC |
| `origin_port` | String | Yes | Origin port code | UN/LOCODE format |
| `destination_port` | String | Yes | Destination port code | UN/LOCODE format |
| `route_chokepoints` | Array[String] | Yes | Chokepoints on route | Valid chokepoint IDs |
| `carrier` | String | No | Shipping carrier | Max 100 chars |
| `vessel_imo` | String | No | Vessel IMO number | 7 digits |
| `eta` | DateTime | Yes | Estimated arrival | UTC |
| `etd` | DateTime | No | Estimated departure | UTC |
| `status` | Enum | Yes | Shipment status | PENDING, IN_TRANSIT, DELAYED, DELIVERED |
| `created_at` | DateTime | Yes | Creation timestamp | UTC |
| `updated_at` | DateTime | Yes | Last update | UTC |

**Indexes**:
- Primary: `shipment_id`
- Index: `customer_id`, `status`
- Index: `route_chokepoints` (GIN)
- Index: `eta`

**Computed Fields**:
- `teu_count`: Calculated from container_count and container_type
- `exposure_usd`: cargo_value_usd * risk_factor

---

### 3. OmenSignal

**Description**: A detected signal from external data sources.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `signal_id` | UUID | Yes | Unique identifier | Primary key |
| `source` | Enum | Yes | Signal source | POLYMARKET, NEWS, AIS, SOCIAL |
| `source_id` | String | Yes | External source ID | Max 255 chars |
| `chokepoint` | Enum | Yes | Affected chokepoint | RED_SEA, SUEZ, PANAMA, etc. |
| `event_type` | Enum | Yes | Type of event | ATTACK, WEATHER, CLOSURE, etc. |
| `probability` | Decimal | Yes | Event probability | 0.0 to 1.0 |
| `confidence_score` | Decimal | Yes | Data quality score | 0.0 to 1.0 |
| `evidence` | Array[JSON] | Yes | Supporting evidence | Array of EvidenceItem |
| `headline` | String | Yes | Event headline | Max 500 chars |
| `description` | String | No | Detailed description | Max 5000 chars |
| `event_time` | DateTime | No | When event occurred | UTC |
| `expires_at` | DateTime | Yes | Signal expiration | UTC |
| `status` | Enum | Yes | Signal status | ACTIVE, CONFIRMED, EXPIRED, INVALID |
| `created_at` | DateTime | Yes | Detection timestamp | UTC |

**Indexes**:
- Primary: `signal_id`
- Unique: `source`, `source_id`
- Index: `chokepoint`, `status`
- Index: `expires_at`

**Data Quality Rules**:
- `probability` and `confidence_score` must be between 0 and 1
- `expires_at` must be after `created_at`
- `evidence` must contain at least 1 item for CONFIRMED signals

---

### 4. DecisionObject

**Description**: A generated decision for a customer based on signals and shipments.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `decision_id` | UUID | Yes | Unique identifier | Primary key |
| `customer_id` | UUID | Yes | Target customer | Foreign key |
| `signal_id` | UUID | Yes | Triggering signal | Foreign key |
| `q1_what` | JSON | Yes | Event description | Q1What schema |
| `q2_when` | JSON | Yes | Timing information | Q2When schema |
| `q3_severity` | JSON | Yes | Impact severity | Q3Severity schema |
| `q4_why` | JSON | Yes | Causal explanation | Q4Why schema |
| `q5_action` | JSON | Yes | Recommended action | Q5Action schema |
| `q6_confidence` | JSON | Yes | Confidence assessment | Q6Confidence schema |
| `q7_inaction` | JSON | Yes | Inaction consequences | Q7Inaction schema |
| `version` | String | Yes | Schema version | Semantic version |
| `ml_model_version` | String | No | ML model used | Semantic version |
| `status` | Enum | Yes | Decision status | GENERATED, DELIVERED, ACKNOWLEDGED, EXPIRED |
| `created_at` | DateTime | Yes | Generation timestamp | UTC |
| `expires_at` | DateTime | Yes | Decision expiration | UTC |
| `acknowledged_at` | DateTime | No | When acknowledged | UTC |

**Indexes**:
- Primary: `decision_id`
- Index: `customer_id`, `status`
- Index: `signal_id`
- Index: `created_at`, `expires_at`

**Embedded Schemas**:

#### Q1What
```json
{
  "event_description": "string (required)",
  "personalized_summary": "string (required)",
  "affected_shipments": ["string"] 
}
```

#### Q2When
```json
{
  "event_time": "datetime (optional)",
  "decision_deadline": "datetime (required)",
  "urgency": "enum: IMMEDIATE|URGENT|SOON|WATCH",
  "hours_until_deadline": "integer"
}
```

#### Q3Severity
```json
{
  "exposure_usd": "decimal (required, >= 0)",
  "delay_days": "integer (required, >= 0)",
  "affected_shipment_count": "integer (required, >= 0)",
  "severity_level": "enum: LOW|MEDIUM|HIGH|CRITICAL"
}
```

#### Q5Action
```json
{
  "action_type": "enum: REROUTE|DELAY|INSURE|MONITOR|DO_NOTHING",
  "specific_instruction": "string (required)",
  "estimated_cost_usd": "decimal (required, >= 0)",
  "deadline": "datetime (required)",
  "carrier": "string (optional)",
  "route": "string (optional)",
  "booking_reference": "string (optional)"
}
```

#### Q7Inaction
```json
{
  "cost_usd": "decimal (required, >= 0)",
  "additional_delay_days": "integer (required, >= 0)",
  "point_of_no_return": "datetime (required)",
  "consequence": "string (required)"
}
```

---

### 5. Alert

**Description**: A delivered alert to a customer.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `alert_id` | UUID | Yes | Unique identifier | Primary key |
| `customer_id` | UUID | Yes | Recipient customer | Foreign key |
| `decision_id` | UUID | Yes | Related decision | Foreign key |
| `channel` | Enum | Yes | Delivery channel | WHATSAPP, EMAIL, SMS |
| `recipient` | String | Yes | Recipient address | Channel-specific format |
| `message_content` | Text | Yes | Sent message | Max 4000 chars |
| `status` | Enum | Yes | Delivery status | PENDING, SENT, DELIVERED, FAILED, READ |
| `external_id` | String | No | External message ID | Provider's ID |
| `sent_at` | DateTime | No | When sent | UTC |
| `delivered_at` | DateTime | No | When delivered | UTC |
| `read_at` | DateTime | No | When read | UTC |
| `error_message` | String | No | Error if failed | Max 1000 chars |
| `retry_count` | Integer | Yes | Delivery attempts | Default: 0 |
| `created_at` | DateTime | Yes | Creation timestamp | UTC |

**Indexes**:
- Primary: `alert_id`
- Index: `customer_id`, `status`
- Index: `decision_id`
- Index: `sent_at`

---

### 6. APIKey

**Description**: API key for customer authentication.

| Attribute | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `key_id` | UUID | Yes | Unique identifier | Primary key |
| `customer_id` | UUID | Yes | Owning customer | Foreign key |
| `key_hash` | String | Yes | Hashed key value | SHA-256 hash |
| `key_prefix` | String | Yes | Visible prefix | 8 chars |
| `name` | String | Yes | Key name/description | Max 100 chars |
| `scopes` | Array[String] | Yes | Permitted scopes | Valid scope names |
| `rate_limit` | Integer | Yes | Requests per minute | > 0 |
| `expires_at` | DateTime | No | Key expiration | UTC |
| `last_used_at` | DateTime | No | Last usage time | UTC |
| `active` | Boolean | Yes | Key status | Default: true |
| `created_at` | DateTime | Yes | Creation timestamp | UTC |

**Indexes**:
- Primary: `key_id`
- Unique: `key_hash`
- Index: `customer_id`, `active`
- Index: `key_prefix`

---

## Lookup Tables

### Chokepoints

| Code | Name | Region | Risk Factors |
|------|------|--------|--------------|
| `red_sea` | Red Sea / Bab-el-Mandeb | Middle East | Conflict, piracy |
| `suez` | Suez Canal | Middle East | Congestion, blockage |
| `panama` | Panama Canal | Central America | Drought, congestion |
| `malacca` | Strait of Malacca | Southeast Asia | Piracy, congestion |
| `gibraltar` | Strait of Gibraltar | Mediterranean | Weather |
| `hormuz` | Strait of Hormuz | Middle East | Conflict |

### Action Types

| Code | Description | Typical Cost Impact |
|------|-------------|-------------------|
| `reroute` | Change shipping route | High (fuel, time) |
| `delay` | Postpone shipment | Medium (holding) |
| `insure` | Increase insurance | Low-Medium |
| `monitor` | Watch and wait | None |
| `do_nothing` | Accept current plan | None |

### Urgency Levels

| Code | Response Window | Use Case |
|------|-----------------|----------|
| `immediate` | < 4 hours | Active crisis |
| `urgent` | 4-24 hours | Confirmed threat |
| `soon` | 1-7 days | Developing situation |
| `watch` | > 7 days | Monitor only |

---

## Data Quality Rules

### Validation Rules

1. **Customer Data**
   - Email must be valid and verified
   - Phone must be in E.164 format
   - Timezone must be valid IANA timezone

2. **Shipment Data**
   - Cargo value must be positive
   - ETA must be in the future (at creation)
   - Route must include at least origin and destination

3. **Signal Data**
   - Probability between 0 and 1
   - Confidence score between 0 and 1
   - Evidence array must not be empty
   - Expiration must be after creation

4. **Decision Data**
   - All 7 questions must be answered
   - Costs must be in USD
   - Delays must be in days
   - Deadline must be actionable (not in past)

### Retention Rules

| Entity | Active Retention | Archive Retention | Deletion |
|--------|-----------------|-------------------|----------|
| Customer | Indefinite | - | On request |
| Shipment | Until delivered + 90 days | 2 years | 7 years |
| Signal | Until expired + 30 days | 1 year | 3 years |
| Decision | Until expired + 90 days | 2 years | 7 years |
| Alert | 90 days | 2 years | 7 years |

### GDPR Compliance

**Personal Data Fields**:
- CustomerProfile: `company_name`, `whatsapp_number`, `email`
- Alert: `recipient`, `message_content`

**Data Subject Rights**:
- Right to access: Export all customer data
- Right to rectification: Update customer fields
- Right to erasure: Anonymize on request
- Right to portability: JSON export format

---

## Relationships Diagram

```
CustomerProfile
    │
    ├──< Shipment (1:N)
    │       └── route_chokepoints → Chokepoint
    │
    ├──< Decision (1:N)
    │       └── signal_id → OmenSignal
    │
    ├──< Alert (1:N)
    │       └── decision_id → Decision
    │
    └──< APIKey (1:N)

OmenSignal
    │
    ├── chokepoint → Chokepoint
    │
    └──< Decision (1:N)
```

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-15 | Initial data dictionary |
| 1.1.0 | 2024-02-01 | Added ML model version to Decision |
| 1.2.0 | 2024-03-01 | Added GDPR compliance section |
