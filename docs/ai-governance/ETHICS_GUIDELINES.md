# RISKCAST Ethics Guidelines

**Version:** 1.0.0  
**Effective Date:** February 1, 2026  
**Classification:** PUBLIC

---

## Purpose

These guidelines establish the ethical framework for AI decision-making in RISKCAST. They ensure that all recommendations align with organizational values, regulatory requirements, and societal expectations.

---

## Core Ethical Principles

### 1. Beneficence: Do Good

> "AI recommendations must provide net positive value to customers"

**Requirements:**
- Every recommendation must have positive expected utility (benefit > cost)
- Cost/benefit analysis must be transparent and verifiable
- Customer interests take priority over system optimization metrics

**Implementation:**
- Q5 (What to do?) includes explicit cost/benefit calculation
- Q7 (What if nothing?) shows value of action vs inaction
- Recommendations rejected if net benefit is negative

**Assessment Questions:**
- Does this recommendation genuinely help the customer?
- Would we be comfortable explaining this to the customer?
- Is the expected benefit clear and reasonable?

---

### 2. Non-Maleficence: Do No Harm

> "AI recommendations must minimize potential harm"

**Requirements:**
- Action cost must not exceed 50% of assets at risk
- Recommendations must not create new risks exceeding mitigated risks
- Conservative defaults when uncertainty is high

**Implementation:**
- Harm ratio checked for every recommendation
- Confidence thresholds trigger human review
- Fail-safe mechanisms default to no action

**Assessment Questions:**
- Could this recommendation cause harm if wrong?
- Is the potential harm proportionate to the potential benefit?
- Are there safeguards against worst-case outcomes?

---

### 3. Autonomy: Respect Choice

> "Users must have meaningful choice and control"

**Requirements:**
- Alternative actions always provided
- User override capability always available
- No fully autonomous execution without consent

**Implementation:**
- Every decision includes alternative_actions list
- Human review always available on request
- Clear escalation paths documented

**Assessment Questions:**
- Can the user choose differently?
- Is the user's ability to override preserved?
- Are alternatives genuinely viable?

---

### 4. Justice: Fair Treatment

> "Equal treatment regardless of customer characteristics"

**Requirements:**
- No discrimination based on protected attributes
- Consistent treatment for similar situations
- Regular fairness monitoring and audits

**Implementation:**
- Quarterly fairness audits with published results
- 80% rule for disparate impact
- Bias detection with automated alerting

**Assessment Questions:**
- Would we give the same recommendation to any customer?
- Is treatment consistent with similar past cases?
- Have we checked for unintended disparities?

---

### 5. Transparency: Explainable Decisions

> "All decisions must be understandable"

**Requirements:**
- Every decision explains the reasoning (Q4: Why)
- Confidence scores always disclosed
- Limitations clearly documented

**Implementation:**
- 7 Questions framework ensures completeness
- Causal chain explains cause-effect relationships
- Confidence factors break down score components

**Assessment Questions:**
- Can we explain this decision to a non-expert?
- Is the reasoning logical and traceable?
- Are uncertainties and limitations clear?

---

### 6. Accountability: Clear Responsibility

> "Clear ownership and audit trail for all decisions"

**Requirements:**
- Every decision has unique identifier
- Complete audit trail retained
- Clear model ownership assignments

**Implementation:**
- Unique decision_id for every recommendation
- 7-year audit log retention
- Model registry with ownership

**Assessment Questions:**
- Can we trace this decision to its inputs?
- Is it clear who is responsible?
- Can we investigate if something goes wrong?

---

## Ethical Assessment Process

### When Assessment Occurs

Every decision is assessed against ethical principles:

```
Decision Generated
       ↓
Ethical Assessment (automated)
       ↓
All Passed? ─── Yes ──→ Proceed to Delivery
       │
       No
       ↓
Human Review Required
       ↓
Ethics Board (if critical)
```

### Assessment Checklist

| Principle | Check | Pass Criteria |
|-----------|-------|---------------|
| Beneficence | Net benefit > 0 | Benefit exceeds cost |
| Non-maleficence | Harm ratio < 50% | Cost < half of exposure |
| Autonomy | Alternatives ≥ 1 | Options provided |
| Justice | Objective criteria | Based on measurable factors |
| Transparency | Explanation complete | Q4 filled with evidence |
| Accountability | Audit trail | ID, timestamp, signal present |

### Assessment Scoring

| Score Range | Interpretation | Action |
|-------------|----------------|--------|
| 0.9 - 1.0 | Excellent | Proceed |
| 0.7 - 0.9 | Good | Proceed with logging |
| 0.5 - 0.7 | Marginal | Human review |
| < 0.5 | Poor | Reject or escalate |

---

## Societal Impact Assessment

### Impact Levels

| Level | Criteria | Additional Review |
|-------|----------|-------------------|
| NEGLIGIBLE | Individual impact only | None |
| LOW | Small group (<10 shipments) | None |
| MEDIUM | Significant group (10-50 shipments) | Manager review |
| HIGH | Large scale (>50 shipments or >$10M) | Ethics Board |
| CRITICAL | Major societal implications | Executive + External |

### Stakeholder Considerations

| Stakeholder | Considerations |
|-------------|----------------|
| Customer | Direct benefit, clear explanation, choice preserved |
| Supply Chain Partners | Coordination, advance notice, fair terms |
| End Consumers | Delivery timing, product availability |
| Society | Economic efficiency, environmental impact |

---

## Ethical Risk Categories

### Category 1: Harm to Customer

**Risk:** Recommendation causes financial loss to customer

**Mitigations:**
- Positive net benefit requirement
- Conservative estimates for costs
- Human review for high values
- Override always available

### Category 2: Unfair Treatment

**Risk:** Systematic bias against certain customer groups

**Mitigations:**
- Quarterly fairness audits
- 80% parity requirement
- Protected attribute monitoring
- Bias detection alerts

### Category 3: Lack of Transparency

**Risk:** Customer cannot understand why recommendation was made

**Mitigations:**
- 7 Questions framework
- Causal chain requirement
- Confidence disclosure
- Right to explanation

### Category 4: Autonomy Violation

**Risk:** Customer feels forced into a decision

**Mitigations:**
- Alternatives always provided
- Override always available
- No automatic execution
- Clear escalation path

### Category 5: Accountability Gap

**Risk:** Unable to determine responsibility for poor outcome

**Mitigations:**
- Unique decision IDs
- Complete audit trail
- Model ownership registry
- Incident review process

---

## Decision Scenarios

### Scenario 1: High-Value, High-Confidence

**Situation:** $2M exposure, 85% confidence, clear benefit

**Assessment:**
- Beneficence: ✅ Net benefit positive ($1.7M)
- Non-maleficence: ✅ Harm ratio 15%
- Autonomy: ✅ Alternatives provided
- Justice: ✅ Objective criteria
- Transparency: ✅ Clear explanation
- Accountability: ✅ Full audit trail

**Decision:** Proceed with recommendation (human review due to value)

### Scenario 2: Low-Value, Low-Confidence

**Situation:** $50K exposure, 45% confidence, marginal benefit

**Assessment:**
- Beneficence: ⚠️ Marginal benefit
- Non-maleficence: ✅ Low harm potential
- Confidence: ❌ Below threshold

**Decision:** Escalate to human review, suggest monitoring

### Scenario 3: Potential Bias Concern

**Situation:** Small customer receiving different recommendation than enterprise customer for similar exposure

**Assessment:**
- Justice: ⚠️ Potential disparity

**Decision:** 
1. Verify recommendation is exposure-based, not size-based
2. Document justification
3. Flag for fairness monitoring

---

## Ethics Board Escalation

### When to Escalate

| Trigger | Example | Escalation |
|---------|---------|------------|
| Critical violation | All principles failed | Immediate |
| High societal impact | >$10M or >50 shipments | Before delivery |
| Novel situation | Unprecedented scenario | Advisory |
| Customer complaint | Ethics concern raised | 24 hours |
| Regulatory inquiry | External request | Immediate |

### Escalation Process

1. **Identify**: Flag issue in assessment
2. **Document**: Complete ethics assessment record
3. **Notify**: Alert Ethics Board via ethics@company.com
4. **Hold**: Pause recommendation pending review
5. **Review**: Ethics Board convenes (within SLA)
6. **Decide**: Approve, modify, or reject
7. **Document**: Record decision and rationale

---

## Continuous Improvement

### Metrics Tracked

| Metric | Target | Current |
|--------|--------|---------|
| Ethical assessment pass rate | >95% | 97% |
| Ethics escalations per month | <5 | 2 |
| Customer ethics complaints | <1/month | 0 |
| Fairness score | >85% | 90% |

### Review Cadence

| Activity | Frequency | Owner |
|----------|-----------|-------|
| Guidelines review | Annually | Ethics Board |
| Training refresh | Quarterly | All teams |
| Incident review | As needed | Quality Team |
| External audit | Annually | Third party |

---

## Training Requirements

### All Team Members

- Ethics guidelines overview (onboarding)
- Annual ethics refresher
- Bias awareness training

### Model Developers

- Fairness in ML training
- Ethical AI design principles
- Model card documentation

### Decision Reviewers

- Ethics assessment process
- Escalation procedures
- Stakeholder impact analysis

---

## Contacts

| Role | Contact |
|------|---------|
| Ethics Board | ethics@company.com |
| Compliance | compliance@company.com |
| Anonymous Hotline | ethics-hotline@company.com |

---

## Appendix: Ethical AI Frameworks Referenced

| Framework | Organization | Applied |
|-----------|--------------|---------|
| Ethics Guidelines for Trustworthy AI | EU HLEG AI | Core principles |
| Model Cards | Google | Documentation |
| Fairness Indicators | TensorFlow | Metrics |
| Responsible AI Practices | Microsoft | Process |

---

*These guidelines are living documents, updated as ethical AI practices evolve. Questions and suggestions welcome at ethics@company.com.*
