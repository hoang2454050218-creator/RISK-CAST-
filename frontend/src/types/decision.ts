/**
 * RISKCAST Decision Types
 *
 * Mirrors: app/riskcast/schemas/decision.py
 *
 * THE 7 QUESTIONS FRAMEWORK:
 * Q1: What is happening? (Event detection)
 * Q2: When will it happen? (Timing & urgency)
 * Q3: How bad is it? (Impact severity)
 * Q4: Why? (Root cause)
 * Q5: What to do now? (Recommended action)
 * Q6: Confidence? (Confidence level)
 * Q7: If nothing? (Cost of inaction)
 */

// ============================================
// ENUMS
// ============================================

export type Urgency = 'IMMEDIATE' | 'URGENT' | 'SOON' | 'WATCH';

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type ConfidenceLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export type ActionType = 'REROUTE' | 'DELAY' | 'INSURE' | 'HEDGE' | 'MONITOR' | 'DO_NOTHING';

export type DecisionStatus = 'PENDING' | 'ACKNOWLEDGED' | 'OVERRIDDEN' | 'EXPIRED' | 'ESCALATED';

export type Chokepoint = 'RED_SEA' | 'SUEZ' | 'PANAMA' | 'MALACCA' | 'STRAIT_OF_HORMUZ';

// ============================================
// CONFIDENCE INTERVAL
// ============================================

/**
 * Represents a range with confidence level
 * CRITICAL: Financial data MUST show uncertainty
 */
export interface ConfidenceInterval {
  lower: number;
  upper: number;
  confidence_level: number; // 0.9 = 90% CI
}

// ============================================
// Q1: WHAT IS HAPPENING?
// ============================================

export interface Q1WhatIsHappening {
  event_type: string;
  event_summary: string;
  affected_chokepoints: Chokepoint[];
  affected_routes: string[];
  source_attribution: string;
  personalized_impact: string;
}

// ============================================
// Q2: WHEN WILL IT HAPPEN?
// ============================================

export interface Q2WhenWillItHappen {
  urgency: Urgency;
  decision_deadline: string; // ISO datetime
  event_timeline: string;
  time_to_impact_hours: number;
  escalation_triggers: string[];
}

// ============================================
// Q3: HOW BAD IS IT?
// ============================================

export interface Q3HowBadIsIt {
  severity: Severity;
  total_exposure_usd: number;
  exposure_ci_90: ConfidenceInterval;
  shipments_affected: number;
  teu_affected: number;
  expected_delay_days: number;
  delay_range: [number, number]; // [min, max]
  breakdown_by_shipment: ShipmentExposure[];
}

export interface ShipmentExposure {
  shipment_id: string;
  cargo_value_usd: number;
  exposure_usd: number;
  route: string;
  eta: string;
}

// ============================================
// Q4: WHY IS THIS HAPPENING?
// ============================================

export interface Q4WhyIsThisHappening {
  root_cause: string;
  causal_chain: CausalLink[];
  evidence_sources: EvidenceSource[];
  historical_precedent?: string;
}

export interface CausalLink {
  from_event: string;
  to_event: string;
  relationship: string;
  confidence: number;
}

export interface EvidenceSource {
  source_type: string;
  source_name: string;
  data_point: string;
  timestamp: string;
  confidence: number;
}

// ============================================
// Q5: WHAT TO DO NOW?
// ============================================

export interface Q5WhatToDoNow {
  recommended_action: ActionType;
  action_summary: string;
  action_details: ActionDetails;
  estimated_cost_usd: number;
  cost_ci_90: ConfidenceInterval;
  expected_benefit_usd: number;
  implementation_steps: string[];
  deadline: string; // ISO datetime
  alternatives: AlternativeAction[];
}

export interface ActionDetails {
  // For REROUTE
  new_route?: string;
  carrier?: string;
  vessel?: string;

  // For DELAY
  delay_days?: number;

  // For INSURE
  coverage_type?: string;
  premium_usd?: number;

  // For HEDGE
  instrument?: string;
  notional_usd?: number;
}

export interface AlternativeAction {
  action_type: ActionType;
  summary: string;
  cost_usd: number;
  trade_off: string;
}

// ============================================
// Q6: HOW CONFIDENT ARE WE?
// ============================================

export interface Q6HowConfident {
  overall_confidence: ConfidenceLevel;
  confidence_score: number; // 0-1
  confidence_factors: ConfidenceFactor[];
  key_uncertainties: string[];
  what_could_change: string[];

  // Calibration context — helps user judge if this score is "good"
  calibration?: ConfidenceCalibration;
}

export interface ConfidenceCalibration {
  /** Historical accuracy for decisions at this confidence band (0-1) */
  historical_accuracy: number;
  /** How many past decisions this accuracy is based on */
  sample_size: number;
  /** How this score compares to average for this decision type */
  relative_performance: 'above_average' | 'average' | 'below_average';
  /** Detailed strength/weakness factors */
  calibration_factors: CalibrationFactor[];
}

export interface CalibrationFactor {
  direction: 'positive' | 'negative';
  strength: 'strong' | 'moderate' | 'weak';
  description: string;
}

export interface ConfidenceFactor {
  factor: string;
  contribution: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  weight: number;
  explanation: string;
}

// ============================================
// Q7: WHAT IF WE DO NOTHING?
// ============================================

export interface Q7WhatIfNothing {
  inaction_cost_usd: number;
  inaction_cost_ci_90: ConfidenceInterval;
  inaction_delay_days: number;
  point_of_no_return: string; // ISO datetime
  cost_escalation: CostEscalationPoint[];
  worst_case_scenario: string;
}

export interface CostEscalationPoint {
  timestamp: string;
  cost_usd: number;
  description: string;
}

// ============================================
// COMPLETE DECISION OBJECT
// ============================================

export interface Decision {
  // Metadata
  decision_id: string;
  customer_id: string;
  created_at: string;
  updated_at: string;
  expires_at: string;
  status: DecisionStatus;
  version: number;

  // The 7 Questions
  q1_what: Q1WhatIsHappening;
  q2_when: Q2WhenWillItHappen;
  q3_severity: Q3HowBadIsIt;
  q4_why: Q4WhyIsThisHappening;
  q5_action: Q5WhatToDoNow;
  q6_confidence: Q6HowConfident;
  q7_inaction: Q7WhatIfNothing;

  // Audit
  signal_ids: string[];
  reasoning_trace_id?: string;
}

// ============================================
// API RESPONSE TYPES
// ============================================

export interface DecisionListResponse {
  decisions: Decision[];
  total: number;
  page?: number;
  page_size?: number;
}

export interface DecisionAcknowledgeRequest {
  decision_id: string;
  acknowledged_by: string;
  notes?: string;
}

export interface DecisionOverrideRequest {
  decision_id: string;
  overridden_by: string;
  new_action: ActionType;
  reason: string;
  notes?: string;
}

export interface DecisionEscalateRequest {
  decision_id: string;
  escalated_by: string;
  escalation_reason: string;
  priority: 'NORMAL' | 'HIGH' | 'CRITICAL';
}
