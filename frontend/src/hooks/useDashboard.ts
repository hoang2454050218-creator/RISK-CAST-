/**
 * Dashboard data hook — transforms real backend DashboardSummary
 * into the shape expected by the dashboard page component.
 *
 * Falls back to mock data when backend is unavailable.
 */

import { useQuery } from '@tanstack/react-query';
import { v2Dashboard, type DashboardSummary } from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';
import type { Urgency, Severity } from '@/types/decision';

// ── Shape the dashboard page expects ────────────────────────

export interface DashboardStats {
  activeDecisions: number;
  activeDecisionsTrend: number;
  pendingEscalations: number;
  pendingEscalationsTrend: number;
  avgResponseTime: string;
  totalExposure: number;
  totalExposureTrend: number;
}

export interface UrgentDecision {
  id: string;
  urgency: Urgency;
  severity: Severity;
  customer: string;
  title: string;
  exposure: number;
  deadline: string;
  // Business decision context
  actionType: string;
  actionCost: number;
  inactionCost: number;
  savings: number;
  shipmentsAffected: number;
  route: string;
  confidence: number;
}

export interface ChokepointStatus {
  id: string;
  name: string;
  status: 'operational' | 'degraded' | 'disrupted';
  affectedShipments: number;
  transitDelay: number;
}

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  actor: string;
  timestamp: string;
}

export interface DashboardData {
  stats: DashboardStats;
  urgentDecisions: UrgentDecision[];
  chokepointHealth: ChokepointStatus[];
  recentActivity: ActivityItem[];
  /** Raw API data for components that need it */
  raw: DashboardSummary;
}

// ── Mappers ─────────────────────────────────────────────────

function severityScoreToUrgency(score: number): Urgency {
  if (score >= 8) return 'IMMEDIATE';
  if (score >= 6) return 'URGENT';
  if (score >= 4) return 'SOON';
  return 'WATCH';
}

function severityScoreToSeverity(score: number): Severity {
  if (score >= 8) return 'CRITICAL';
  if (score >= 6) return 'HIGH';
  if (score >= 4) return 'MEDIUM';
  return 'LOW';
}

function stalenessToResponseTime(level: string): string {
  switch (level) {
    case 'fresh':
      return '< 1h';
    case 'stale':
      return '1-6h';
    case 'outdated':
      return '> 6h';
    case 'no_data':
      return 'N/A';
    default:
      return level;
  }
}

// ── Transform API response → dashboard shape ────────────────

function transformDashboardData(raw: DashboardSummary): DashboardData {
  return {
    stats: {
      activeDecisions: raw.pending_decisions ?? 0,
      activeDecisionsTrend: 0,
      pendingEscalations: raw.critical_signals ?? 0,
      pendingEscalationsTrend: 0,
      avgResponseTime: stalenessToResponseTime(
        raw.data_freshness?.staleness_level ?? 'no_data',
      ),
      totalExposure: raw.total_revenue ?? 0,
      totalExposureTrend: 0,
    },

    urgentDecisions: (raw.top_risks ?? []).map((risk, i) => {
      // Extract business context from risk data if available
      const severityScore = risk.severity_score ?? 0;
      const exposure = risk.exposure_usd ?? 0;
      const actionCost = risk.action_cost_usd ?? 0;
      const inactionCost = risk.inaction_cost_usd ?? exposure;

      return {
        id: risk.signal_id ?? `risk-${i}`,
        urgency: severityScoreToUrgency(severityScore),
        severity: severityScoreToSeverity(severityScore),
        customer: risk.entity_id ?? 'Unknown',
        title: risk.summary || `${risk.signal_type} risk detected`,
        exposure,
        deadline: risk.deadline ?? new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        actionType: risk.recommended_action ?? 'MONITOR',
        actionCost,
        inactionCost,
        savings: Math.max(0, inactionCost - actionCost),
        shipmentsAffected: risk.shipments_affected ?? 0,
        route: risk.affected_route ?? '',
        confidence: risk.confidence ?? 0,
      };
    }),

    chokepointHealth: [],

    recentActivity: (raw.recent_actions ?? []).map((action, i) => ({
      id: `action-${i}`,
      type: action.action_type ?? 'signal',
      title: action.description || 'Action performed',
      actor: action.user_name ?? 'System',
      timestamp: action.timestamp ?? new Date().toISOString(),
    })),

    raw,
  };
}

// ── Mock data for offline mode ───────────────────────────────

const mockDashboardSummary: DashboardSummary = {
  total_signals: 47,
  critical_signals: 3,
  total_revenue: 2850000,
  data_freshness: { staleness_level: 'fresh', oldest_signal_hours: 1, newest_signal_hours: 0 },
  pending_decisions: 5,
  top_risks: [
    {
      signal_id: 'sig_red_sea_001',
      signal_type: 'ROUTE_DISRUPTION',
      severity_score: 9,
      entity_type: 'chokepoint',
      entity_id: 'ACME Logistics',
      summary: 'Red Sea disruption — 5 shipments via Suez need rerouting. Cape route adds 10-14 days.',
      exposure_usd: 235000,
      action_cost_usd: 42500,
      inaction_cost_usd: 235000,
      recommended_action: 'REROUTE',
      shipments_affected: 5,
      affected_route: 'Shanghai → Rotterdam',
      deadline: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
      confidence: 0.82,
    },
    {
      signal_id: 'sig_panama_002',
      signal_type: 'PORT_CONGESTION',
      severity_score: 7,
      entity_type: 'chokepoint',
      entity_id: 'Global Trade Inc',
      summary: 'Panama Canal wait 8-12 days. Insurance premium spike 15%. 3 shipments affected.',
      exposure_usd: 180000,
      action_cost_usd: 28000,
      inaction_cost_usd: 95000,
      recommended_action: 'INSURE',
      shipments_affected: 3,
      affected_route: 'Busan → Houston',
      deadline: new Date(Date.now() + 16 * 60 * 60 * 1000).toISOString(),
      confidence: 0.88,
    },
    {
      signal_id: 'sig_rates_003',
      signal_type: 'RATE_SPIKE',
      severity_score: 6,
      entity_type: null,
      entity_id: 'VinaTech Export',
      summary: 'Trans-Pacific rates +28% WoW. Lock current rates or wait for correction.',
      exposure_usd: 45000,
      action_cost_usd: 12000,
      inaction_cost_usd: 45000,
      recommended_action: 'HEDGE',
      shipments_affected: 2,
      affected_route: 'HCMC → Los Angeles',
      deadline: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
      confidence: 0.75,
    },
  ],
  recent_actions: [
    { action_type: 'decision', description: 'Decision acknowledged for Red Sea reroute', timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(), user_name: 'Hoang N.' },
    { action_type: 'signal', description: 'New signal detected: Panama Canal restrictions', timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), user_name: null },
    { action_type: 'escalation', description: 'Escalation resolved for Suez congestion', timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), user_name: 'System' },
  ],
  data_completeness: 0.87,
  known_gaps: [],
  message: null,
};

// ── Hook ────────────────────────────────────────────────────

export function useDashboardData(periodDays = 7) {
  return useQuery<DashboardData>({
    queryKey: ['dashboard', periodDays],
    queryFn: async () => {
      const raw = await withMockFallback(
        () => v2Dashboard.summary(periodDays),
        mockDashboardSummary,
      );
      return transformDashboardData(raw);
    },
    staleTime: 10_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}
