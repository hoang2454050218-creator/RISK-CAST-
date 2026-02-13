# RISKCAST AI Governance Policy

**Version:** 1.0.0  
**Effective Date:** February 1, 2026  
**Last Review:** February 5, 2026  
**Next Review:** May 1, 2026  
**Classification:** PUBLIC

---

## 1. Executive Summary

This policy establishes the governance framework for all artificial intelligence and machine learning systems within RISKCAST. It ensures compliance with the EU AI Act, maintains ethical standards, and provides clear guidelines for responsible AI development and deployment.

RISKCAST is classified as **LIMITED RISK** under the EU AI Act, requiring transparency obligations but not conformity assessment.

---

## 2. Scope

### 2.1 Covered Systems

This policy applies to all AI/ML systems within RISKCAST:

| System | Purpose | Risk Level |
|--------|---------|------------|
| RISKCAST Decision Engine | Risk mitigation recommendations | HIGH |
| OMEN Signal Processor | Disruption signal detection | MEDIUM |
| ORACLE Reality Correlator | Signal-reality correlation | MEDIUM |
| Uncertainty Module | Confidence interval calculation | LOW |
| Calibration System | Prediction accuracy monitoring | LOW |

### 2.2 Excluded Systems

This policy does NOT cover:
- Traditional rule-based systems without learning components
- Data pipelines and ETL processes
- Standard business logic

---

## 3. EU AI Act Classification

### 3.1 Risk Classification: LIMITED RISK

RISKCAST is classified as **LIMITED RISK** under EU AI Act Article 6 because:

1. **Not Autonomous**: System provides recommendations, not autonomous actions
2. **Human Oversight**: All final decisions made by humans
3. **Not Critical Infrastructure**: Not used for essential services or critical systems
4. **Not Employment-Related**: Not used for hiring or workforce decisions
5. **Transparency Provided**: Full explanation via 7 Questions framework

### 3.2 Applicable Requirements

As a LIMITED RISK system, RISKCAST must:

- ✅ Inform users they are interacting with AI (Article 52)
- ✅ Document capabilities and limitations
- ✅ Provide decision explanations
- ✅ Enable human oversight
- ✅ Maintain audit trails

---

## 4. Core Principles

### 4.1 Transparency

> "All decisions must be explainable via the 7 Questions framework"

- Every recommendation includes explanation (Q4: Why)
- Confidence scores are always disclosed (Q6: How Confident)
- Limitations are documented and accessible
- Users informed of AI nature upon first interaction

### 4.2 Fairness

> "No discrimination based on protected characteristics"

- Regular bias monitoring across customer segments
- Quarterly fairness audits with published results
- 80% rule (disparate impact) enforced
- Calibration monitoring by group

### 4.3 Accountability

> "Complete audit trail for all decisions with human oversight"

- Every decision has unique ID and timestamp
- Full audit trail retained for 7 years
- Clear ownership for each model
- Human review for high-stakes decisions

### 4.4 Privacy

> "Minimal data collection with purpose limitation"

- Data used only for stated purposes
- Customer data never sold or shared for marketing
- Clear retention policies enforced
- User rights to access, correct, and delete

### 4.5 Safety

> "Fail-safe mechanisms for all critical paths"

- Conservative fallbacks on uncertainty
- Circuit breakers for external dependencies
- Graceful degradation under failure
- Health monitoring and alerting

### 4.6 Human Agency

> "Users can always override AI recommendations"

- Override capability for every recommendation
- Alternative options always provided
- Human review escalation available
- No fully autonomous execution

---

## 5. Governance Structure

### 5.1 AI Ethics Board

The AI Ethics Board provides oversight and guidance:

| Role | Responsibility |
|------|----------------|
| Chief Technology Officer | Technical governance |
| Chief Risk Officer | Risk oversight |
| Head of Legal & Compliance | Regulatory compliance |
| External Ethics Advisor | Independent perspective |

**Meeting Cadence:** Quarterly  
**Authority:** Policy approval, model approval, incident escalation

### 5.2 Model Ownership

| Model | Owner | Team |
|-------|-------|------|
| riskcast-decision-v2 | Decision Team Lead | RISKCAST Core |
| omen-signal-processor | Signal Team Lead | Intelligence |
| oracle-reality-correlator | Reality Team Lead | Intelligence |
| uncertainty-bayesian | Analytics Team Lead | Analytics |
| calibration-system | Quality Team Lead | Quality |

### 5.3 Review Cadence

| Activity | Frequency | Owner |
|----------|-----------|-------|
| Policy Review | Quarterly | AI Ethics Board |
| Fairness Audit | Quarterly | Quality Team |
| Model Performance Review | Monthly | Model Owners |
| Calibration Check | Weekly | Quality Team |
| Incident Review | As needed | On-call Team |

---

## 6. Human Oversight Requirements

### 6.1 Oversight Levels

| Level | Description | When Applied |
|-------|-------------|--------------|
| Human-in-the-Loop | Human approves before action | High-value decisions |
| Human-on-the-Loop | Human monitors, can intervene | Standard decisions |
| Human-in-Command | Human can override anytime | All decisions |

### 6.2 Mandatory Review Thresholds

| Condition | Requirement |
|-----------|-------------|
| Exposure > $500,000 | Human review before delivery |
| Confidence < 50% | Escalation to human reviewer |
| Novel situation | Human review flagged |
| Customer request | Human review provided |

### 6.3 Escalation Timeouts

| Severity | Timeout | Escalation |
|----------|---------|------------|
| Critical | 1 hour | On-call → Manager |
| High | 4 hours | Queue → On-call |
| Medium | 24 hours | Queue → Review team |
| Low | 72 hours | Batched review |

---

## 7. Transparency Requirements

### 7.1 User Disclosure

Upon first interaction, users receive:

```
RISKCAST is an AI-powered decision support system. All recommendations
are generated by artificial intelligence and should be reviewed by
human decision-makers before action. You have the right to request
human review of any recommendation.
```

### 7.2 Decision Explanation (7 Questions)

Every decision must answer:

1. **Q1: What is happening?** - Personalized event summary
2. **Q2: When?** - Timeline and urgency
3. **Q3: How bad?** - Impact with confidence intervals
4. **Q4: Why?** - Causal chain and evidence
5. **Q5: What to do?** - Specific action with cost
6. **Q6: How confident?** - Score with factors
7. **Q7: What if nothing?** - Inaction cost with deadline

### 7.3 Public Documentation

Available at `/governance/transparency`:

- AI Disclosure Statement
- System Capabilities
- Known Limitations
- Data Usage Policy
- Decision Process Documentation

---

## 8. Fairness Requirements

### 8.1 Protected Attributes

Monitored for bias:

- Customer size (small, medium, large, enterprise)
- Geographic region (APAC, EMEA, Americas)
- Chokepoint (red_sea, panama, suez, malacca)
- Cargo type (general, hazmat, perishable, high_value)

### 8.2 Fairness Metrics

| Metric | Threshold | Action if Violated |
|--------|-----------|-------------------|
| Demographic Parity | ≥ 80% ratio | Immediate review |
| Accuracy Parity | ≥ 90% ratio | Investigation |
| Calibration Parity | ≤ 10% difference | Recalibration |

### 8.3 Quarterly Fairness Audit

Each quarter:

1. Generate fairness report via `/governance/fairness/report`
2. Review with AI Ethics Board
3. Document findings and actions
4. Publish summary (without customer data)

---

## 9. Data Governance

### 9.1 Data Minimization

- Collect only data necessary for recommendations
- No collection of personal demographics
- Aggregated data preferred where possible

### 9.2 Purpose Limitation

Data used ONLY for:

- Generating personalized recommendations
- Improving prediction accuracy
- Monitoring fairness and calibration
- Regulatory compliance

### 9.3 Retention Periods

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Decision Records | 3 years | Business continuity |
| Audit Logs | 7 years | Regulatory compliance |
| Calibration Data | 2 years | Model improvement |
| Anonymized Analytics | Indefinite | System improvement |

### 9.4 User Rights

Users may:

- Request explanation of any decision
- Request human review
- Access their data
- Correct inaccurate data
- Request deletion (subject to legal holds)

---

## 10. Incident Response

### 10.1 Incident Categories

| Category | Examples | Response Time |
|----------|----------|---------------|
| Critical | Incorrect high-value recommendation, bias incident | 1 hour |
| High | System degradation, calibration drift | 4 hours |
| Medium | Feature malfunction, data quality issue | 24 hours |
| Low | Minor UI issue, documentation error | 72 hours |

### 10.2 Response Process

1. **Detect**: Automated monitoring or user report
2. **Assess**: Determine severity and impact
3. **Contain**: Limit further impact
4. **Investigate**: Root cause analysis
5. **Remediate**: Fix and verify
6. **Report**: Document and communicate
7. **Review**: Post-incident review

### 10.3 Notification Requirements

| Stakeholder | When Notified | Method |
|-------------|---------------|--------|
| Affected Customers | Critical/High | Email + Dashboard |
| AI Ethics Board | All Critical | Immediate call |
| Regulators | Data breach, safety | Per regulation |

---

## 11. Compliance Monitoring

### 11.1 Automated Checks

| Check | Frequency | Alert Threshold |
|-------|-----------|-----------------|
| Policy enforcement | Every decision | Any violation |
| Fairness metrics | Daily | < 80% parity |
| Calibration ECE | Daily | > 0.15 |
| Human review rate | Weekly | < 20% of required |

### 11.2 Manual Audits

| Audit | Frequency | Auditor |
|-------|-----------|---------|
| Fairness audit | Quarterly | Quality Team |
| Policy compliance | Quarterly | Compliance |
| Model card review | Quarterly | Model Owners |
| External audit | Annual | Third party |

---

## 12. Amendment Process

### 12.1 Policy Changes

1. Proposed changes submitted to AI Ethics Board
2. Impact assessment conducted
3. Stakeholder review (2 weeks)
4. AI Ethics Board approval
5. Communication and training
6. Implementation

### 12.2 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-01 | Initial release |

---

## 13. Contacts

| Role | Contact |
|------|---------|
| AI Ethics Board | ai-ethics@company.com |
| Compliance | compliance@company.com |
| Support | support@company.com |
| DPO | dpo@company.com |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| EU AI Act | European Union Artificial Intelligence Act |
| LIMITED RISK | AI Act category requiring transparency obligations |
| ECE | Expected Calibration Error |
| Disparate Impact | Different outcomes for different groups |
| 80% Rule | Minimum ratio for demographic parity |

---

*This policy is effective as of February 1, 2026. Questions should be directed to ai-ethics@company.com.*
