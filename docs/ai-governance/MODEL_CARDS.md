# RISKCAST Model Cards

**Version:** 1.0.0  
**Last Updated:** February 5, 2026  
**Classification:** PUBLIC

This document provides Model Cards for all AI/ML systems in RISKCAST, following Google's Model Cards for Model Reporting standard, extended for EU AI Act compliance.

---

## Model Registry Summary

| Model | Status | Risk Level | Owner | Accuracy |
|-------|--------|------------|-------|----------|
| RISKCAST Decision Engine v2.1 | Production | HIGH | Decision Team | 72% |
| OMEN Signal Processor v1.2 | Production | MEDIUM | Signal Team | 78% |
| ORACLE Reality Correlator v1.1 | Production | MEDIUM | Reality Team | 85% |
| Uncertainty Module v2.0 | Production | LOW | Analytics Team | N/A |
| Calibration System v1.0 | Production | LOW | Quality Team | N/A |

---

## RISKCAST Decision Engine

### Model Identity

| Field | Value |
|-------|-------|
| Model ID | `riskcast-decision-v2` |
| Model Name | RISKCAST Decision Engine |
| Version | 2.1.0 |
| Status | Production |
| Risk Level | HIGH |

### Ownership

| Field | Value |
|-------|-------|
| Owner | Decision Team Lead |
| Team | RISKCAST Core |
| Contact | riskcast-core@company.com |

### Description

The RISKCAST Decision Engine is a 6-layer reasoning system that transforms supply chain disruption signals into actionable risk mitigation recommendations. It uses Bayesian uncertainty quantification and multi-layer reasoning (factual, causal, temporal, counterfactual, strategic, meta) to generate decisions with confidence intervals.

### Intended Use

**Primary Use Case:**
- Generate actionable risk mitigation recommendations for supply chain disruptions
- Provide 7-question decision framework with confidence intervals
- Support human decision-makers with cost/benefit analysis

**User Groups:**
- Supply chain managers
- Logistics coordinators
- Risk managers
- Operations teams

### Out-of-Scope Uses

This model should NOT be used for:

- ❌ Medical decision making
- ❌ Financial trading or investment decisions
- ❌ Personal safety or security decisions
- ❌ Autonomous execution without human oversight
- ❌ Decisions involving personal data classification

### Technical Details

| Field | Value |
|-------|-------|
| Model Type | Hybrid (Rule-based + ML components) |
| Algorithm | Multi-layer reasoning with Bayesian uncertainty |
| Latency (p50) | 250ms |
| Latency (p99) | 1500ms |

**Input Features:**
- Signal probability (from OMEN)
- Vessel positions (from AIS)
- Customer shipment context
- Market rate data
- Historical disruption patterns
- Chokepoint status

**Output Format:**
- DecisionObject with 7 Questions
- Confidence intervals (80%, 90%, 95%, 99%)
- VaR and CVaR metrics
- Alternative actions

### Performance Metrics

#### Overall Performance

| Metric | Value |
|--------|-------|
| Accuracy | 72% |
| Precision | 68% |
| Recall | 75% |
| F1 Score | 71% |
| Calibration ECE | 0.08 |

#### Performance by Chokepoint

| Chokepoint | Accuracy | Precision |
|------------|----------|-----------|
| Red Sea | 78% | 75% |
| Panama | 70% | 65% |
| Suez | 68% | 62% |
| Malacca | 65% | 60% |

### Known Limitations

1. **Limited Novel Event Data**: Limited historical data for unprecedented disruption types
2. **External Dependency**: Dependent on Polymarket and AIS data quality
3. **Tail Risk**: May underestimate tail risks in extreme scenarios
4. **Data Freshness**: Performance degrades with stale data (>1 hour)
5. **Geographic Coverage**: Limited to major trade routes

### Failure Modes

| Failure | Behavior |
|---------|----------|
| Signal provider outage | Falls back to conservative estimates |
| Stale data (>1 hour) | Reduces confidence, escalates to human |
| Novel disruption type | Flags for human review |
| Conflicting signals | Requests additional confirmation |

### Fairness Documentation

**Evaluated Groups:**
- Customer size (small, medium, large, enterprise)
- Chokepoint (red_sea, panama, suez, malacca)
- Region (APAC, EMEA, Americas)
- Cargo type (general, hazmat, perishable, high_value)

**Fairness Metrics:**

| Metric | Score |
|--------|-------|
| Demographic parity (customer size) | 92% |
| Equal opportunity (chokepoint) | 88% |
| Calibration by region | 90% |

**Bias Mitigations:**
- Customer size normalization in cost/benefit calculations
- Chokepoint-specific calibration models
- Region-adjusted confidence thresholds
- Exposure-weighted recommendations

### Governance

| Field | Value |
|-------|-------|
| Approval Status | APPROVED |
| Approved By | AI Ethics Board |
| Approval Date | December 1, 2024 |
| Next Review | April 1, 2025 |

**Compliance Notes:**
- EU AI Act: LIMITED RISK - transparency obligations apply
- Human oversight required for decisions > $500K
- Quarterly fairness audit mandated

---

## OMEN Signal Processor

### Model Identity

| Field | Value |
|-------|-------|
| Model ID | `omen-signal-processor` |
| Model Name | OMEN Signal Processor |
| Version | 1.2.0 |
| Status | Production |
| Risk Level | MEDIUM |

### Description

Processes signals from multiple sources (Polymarket, news, AIS anomalies) and validates them through a 4-stage validation pipeline. Outputs calibrated probability estimates with evidence items.

### Intended Use

- Detect and validate supply chain disruption signals
- Provide calibrated probability estimates
- Aggregate evidence from multiple sources

### Technical Details

| Field | Value |
|-------|-------|
| Model Type | Hybrid (Multi-source fusion) |
| Algorithm | Bayesian calibration with evidence fusion |
| Latency (p50) | 150ms |
| Latency (p99) | 800ms |

### Performance

| Metric | Value |
|--------|-------|
| Signal Accuracy | 78% |
| False Positive Rate | 12% |
| Calibration ECE | 0.06 |

### Limitations

- Dependent on Polymarket market liquidity
- News sentiment may lag actual events
- Limited coverage for minor chokepoints

---

## ORACLE Reality Correlator

### Model Identity

| Field | Value |
|-------|-------|
| Model ID | `oracle-reality-correlator` |
| Model Name | ORACLE Reality Correlator |
| Version | 1.1.0 |
| Status | Production |
| Risk Level | MEDIUM |

### Description

Correlates OMEN signals with real-world observations (AIS vessel data, freight rates, port status) to confirm or refute predictions.

### Technical Details

| Field | Value |
|-------|-------|
| Model Type | Rule-based |
| Algorithm | Evidence-based correlation |

### Performance

| Metric | Value |
|--------|-------|
| Correlation Accuracy | 85% |
| False Confirmation Rate | 8% |

---

## Uncertainty Module

### Model Identity

| Field | Value |
|-------|-------|
| Model ID | `uncertainty-bayesian` |
| Model Name | Bayesian Uncertainty Quantification |
| Version | 2.0.0 |
| Status | Production |
| Risk Level | LOW |

### Description

Provides full uncertainty quantification for all numeric outputs including confidence intervals (80%, 90%, 95%, 99%), VaR, CVaR, and propagates uncertainty through arithmetic operations.

### Performance

| Metric | Value |
|--------|-------|
| CI 90% Coverage | 89% |
| CI 95% Coverage | 94% |

---

## Calibration System

### Model Identity

| Field | Value |
|-------|-------|
| Model ID | `calibration-system` |
| Model Name | Prediction Calibration System |
| Version | 1.0.0 |
| Status | Production |
| Risk Level | LOW |

### Description

Monitors and improves calibration of probability predictions. Tracks ECE, Brier score, and generates calibration curves. Alerts on calibration drift.

---

## Appendix: Model Card Updates

### Changelog

| Date | Model | Version | Changes |
|------|-------|---------|---------|
| 2026-02-01 | riskcast-decision | 2.1.0 | Added confidence intervals |
| 2026-01-15 | uncertainty-bayesian | 2.0.0 | Added VaR/CVaR |
| 2025-12-01 | riskcast-decision | 2.0.0 | 6-layer reasoning |

### Review Schedule

| Model | Next Review | Reviewer |
|-------|-------------|----------|
| riskcast-decision-v2 | 2025-04-01 | AI Ethics Board |
| omen-signal-processor | 2025-05-01 | Technical Review Board |
| oracle-reality-correlator | 2025-04-01 | Technical Review Board |

---

*Model cards are updated quarterly. Access the API at `/governance/models` for current versions.*
