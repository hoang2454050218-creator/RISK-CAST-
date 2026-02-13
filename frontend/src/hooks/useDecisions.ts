/**
 * Decision hooks — real data from backend API with mock fallback.
 *
 * Transforms V2 backend decisions (flat schema) into the 7-questions format
 * the frontend expects. Falls back to mock data when backend is unavailable.
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import {
  getDecisions,
  getDecision,
  acknowledgeDecision,
  overrideDecision,
  escalateDecision,
  withMockFallback,
} from '@/lib/api';
import { toast } from '@/components/ui/toast';
import { mockDecision, mockDecisions } from '@/lib/mock-data/legacy';
import type {
  Decision,
  DecisionAcknowledgeRequest,
  DecisionOverrideRequest,
  DecisionEscalateRequest,
  Urgency,
  Severity,
  ActionType,
  ConfidenceLevel,
  DecisionStatus,
} from '@/types/decision';

// Query keys
export const decisionKeys = {
  all: ['decisions'] as const,
  lists: () => [...decisionKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...decisionKeys.lists(), filters] as const,
  details: () => [...decisionKeys.all, 'detail'] as const,
  detail: (id: string) => [...decisionKeys.details(), id] as const,
};

// ── Backend → Frontend transformation ────────────────────────

/** Map backend severity to frontend Severity */
function mapSeverity(s: string): Severity {
  const map: Record<string, Severity> = {
    critical: 'CRITICAL', high: 'HIGH', moderate: 'HIGH', medium: 'MEDIUM', low: 'LOW',
    CRITICAL: 'CRITICAL', HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW',
  };
  return map[s] ?? 'LOW';
}

/** Map backend status to frontend DecisionStatus */
function mapStatus(s: string): DecisionStatus {
  const map: Record<string, DecisionStatus> = {
    pending: 'PENDING', recommended: 'PENDING', acknowledged: 'ACKNOWLEDGED',
    acted_upon: 'ACKNOWLEDGED', overridden: 'OVERRIDDEN', escalated: 'ESCALATED',
    expired: 'EXPIRED',
    PENDING: 'PENDING', ACKNOWLEDGED: 'ACKNOWLEDGED', OVERRIDDEN: 'OVERRIDDEN',
    ESCALATED: 'ESCALATED', EXPIRED: 'EXPIRED',
  };
  return map[s] ?? 'PENDING';
}

/** Map risk score to urgency */
function riskScoreToUrgency(score: number): Urgency {
  if (score >= 70) return 'IMMEDIATE';
  if (score >= 50) return 'URGENT';
  if (score >= 30) return 'SOON';
  return 'WATCH';
}

/** Map backend action type to frontend */
function mapActionType(a: string): ActionType {
  const map: Record<string, ActionType> = {
    reroute: 'REROUTE', insure: 'INSURE', delay_shipment: 'DELAY',
    hedge_exposure: 'HEDGE', split_shipment: 'REROUTE', monitor_only: 'MONITOR',
    escalate_to_human: 'DO_NOTHING',
    REROUTE: 'REROUTE', INSURE: 'INSURE', DELAY: 'DELAY',
    HEDGE: 'HEDGE', MONITOR: 'MONITOR', DO_NOTHING: 'DO_NOTHING',
  };
  return map[a] ?? 'MONITOR';
}

/** Map confidence score to level */
function confidenceToLevel(c: number): ConfidenceLevel {
  if (c >= 0.7) return 'HIGH';
  if (c >= 0.4) return 'MEDIUM';
  return 'LOW';
}

/**
 * Check if a decision object is in frontend (7Q) format.
 * If it already has q1_what, it's the frontend format.
 */
function isFrontendDecision(d: unknown): d is Decision {
  return typeof d === 'object' && d !== null && 'q1_what' in d;
}

/**
 * Transform a single backend decision to frontend Decision format.
 * If the decision is already in frontend format, return as-is.
 */
function transformDecision(raw: Record<string, unknown>): Decision {
  if (isFrontendDecision(raw)) return raw;

  const riskScore = Number(raw.risk_score ?? 0);
  const confidence = Number(raw.confidence ?? 0);
  const severity = mapSeverity(String(raw.severity ?? 'low'));
  const urgency = riskScoreToUrgency(riskScore);
  const recAction = raw.recommended_action as Record<string, unknown> | undefined;
  const tradeoff = raw.tradeoff as Record<string, unknown> | undefined;
  const altActions = (raw.alternative_actions ?? []) as Record<string, unknown>[];
  const escalationRules = (raw.escalation_rules ?? []) as Record<string, unknown>[];
  const counterfactuals = (raw.counterfactuals ?? []) as Record<string, unknown>[];
  const dataSources = (raw.data_sources ?? []) as string[];

  return {
    decision_id: String(raw.decision_id ?? ''),
    customer_id: String(raw.company_id ?? raw.entity_id ?? ''),
    created_at: String(raw.generated_at ?? new Date().toISOString()),
    updated_at: String(raw.generated_at ?? new Date().toISOString()),
    expires_at: String(raw.valid_until ?? new Date(Date.now() + 24 * 3600000).toISOString()),
    status: mapStatus(String(raw.status ?? 'pending')),
    version: 1,

    q1_what: {
      event_type: String(raw.entity_type ?? 'UNKNOWN'),
      event_summary: String(raw.situation_summary ?? 'Risk assessment generated'),
      affected_chokepoints: [],
      affected_routes: [],
      source_attribution: dataSources.join(', ') || 'AI Analysis',
      personalized_impact: String(raw.escalation_reason ?? raw.inaction_risk ?? ''),
    },

    q2_when: {
      urgency,
      decision_deadline: String(raw.valid_until ?? new Date(Date.now() + 24 * 3600000).toISOString()),
      event_timeline: '',
      time_to_impact_hours: 24,
      escalation_triggers: escalationRules
        .filter((r) => r.triggered)
        .map((r) => String(r.reason ?? r.rule_name ?? '')),
    },

    q3_severity: {
      severity,
      total_exposure_usd: Number(recAction?.estimated_cost_usd ?? raw.inaction_cost ?? 0),
      exposure_ci_90: {
        lower: Number(raw.ci_lower ?? 0),
        upper: Number(raw.ci_upper ?? 0),
        confidence_level: 0.9,
      },
      shipments_affected: 1,
      teu_affected: 0,
      expected_delay_days: 0,
      delay_range: [0, 0],
      breakdown_by_shipment: [],
    },

    q4_why: {
      root_cause: String(raw.situation_summary ?? ''),
      causal_chain: [],
      evidence_sources: dataSources.map((s, i) => ({
        source_type: 'DATA',
        source_name: s,
        data_point: '',
        timestamp: new Date().toISOString(),
        confidence: confidence,
      })),
    },

    q5_action: {
      recommended_action: mapActionType(String(recAction?.action_type ?? tradeoff?.recommended_action ?? 'monitor_only')),
      action_summary: String(recAction?.description ?? tradeoff?.recommendation_reason ?? ''),
      action_details: {},
      estimated_cost_usd: Number(recAction?.estimated_cost_usd ?? 0),
      cost_ci_90: { lower: 0, upper: 0, confidence_level: 0.9 },
      expected_benefit_usd: Number(recAction?.estimated_benefit_usd ?? 0),
      implementation_steps: (recAction?.requirements as string[] ?? []),
      deadline: String(raw.valid_until ?? new Date(Date.now() + 24 * 3600000).toISOString()),
      alternatives: altActions.map((a) => ({
        action_type: mapActionType(String(a.action_type ?? 'monitor_only')),
        summary: String(a.description ?? ''),
        cost_usd: Number(a.estimated_cost_usd ?? 0),
        trade_off: (a.risks as string[] ?? []).join('; ') || 'See details',
      })),
    },

    q6_confidence: {
      overall_confidence: confidenceToLevel(confidence),
      confidence_score: confidence,
      confidence_factors: [],
      key_uncertainties: [],
      what_could_change: [],
    },

    q7_inaction: {
      inaction_cost_usd: Number(raw.inaction_cost ?? 0),
      inaction_cost_ci_90: { lower: 0, upper: 0, confidence_level: 0.9 },
      inaction_delay_days: 0,
      point_of_no_return: String(raw.valid_until ?? new Date(Date.now() + 24 * 3600000).toISOString()),
      cost_escalation: [],
      worst_case_scenario: String(raw.inaction_risk ?? ''),
    },

    signal_ids: [],
  };
}

/**
 * Hook to fetch list of decisions.
 */
export function useDecisionsList(params?: {
  status?: string;
  customer_id?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: decisionKeys.list(params ?? {}),
    queryFn: async () => {
      const data = await withMockFallback(
        () => getDecisions(params),
        { decisions: mockDecisions, total: mockDecisions.length },
      );
      // Transform backend decisions to frontend format
      const transformed = (data.decisions ?? []).map((d) =>
        transformDecision(d as unknown as Record<string, unknown>),
      );
      return { decisions: transformed, total: data.total ?? transformed.length };
    },
    staleTime: 60_000,
    refetchInterval: 60_000,
    select: (data) => data.decisions as Decision[],
    retry: 2,
  });
}

/**
 * Hook to fetch a single decision.
 */
export function useDecision(decisionId: string | undefined) {
  return useQuery({
    queryKey: decisionKeys.detail(decisionId ?? ''),
    queryFn: async () => {
      const data = await withMockFallback(
        () => getDecision(decisionId!),
        mockDecision,
      );
      return transformDecision(data as unknown as Record<string, unknown>);
    },
    enabled: !!decisionId,
    staleTime: 30_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}

/**
 * Hook to acknowledge a decision.
 */
export function useAcknowledgeDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: DecisionAcknowledgeRequest) => acknowledgeDecision(request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: decisionKeys.detail(variables.decision_id) });
      queryClient.invalidateQueries({ queryKey: decisionKeys.lists() });
      toast.success('Decision acknowledged successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to acknowledge decision: ${error.message}`);
    },
  });
}

/**
 * Hook to override a decision.
 */
export function useOverrideDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: DecisionOverrideRequest) => overrideDecision(request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: decisionKeys.detail(variables.decision_id) });
      queryClient.invalidateQueries({ queryKey: decisionKeys.lists() });
      toast.success('Decision overridden successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to override decision: ${error.message}`);
    },
  });
}

/**
 * Hook to escalate a decision.
 */
export function useEscalateDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: DecisionEscalateRequest) => escalateDecision(request),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: decisionKeys.detail(variables.decision_id) });
      queryClient.invalidateQueries({ queryKey: decisionKeys.lists() });
      toast.success('Decision escalated for human review');
    },
    onError: (error: Error) => {
      toast.error(`Failed to escalate decision: ${error.message}`);
    },
  });
}
