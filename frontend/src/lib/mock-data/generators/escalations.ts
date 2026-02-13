/**
 * Escalation detail generator.
 */

import { rng } from '../seed';

export interface EscalationDetail {
  id: string;
  decisionId: string;
  reason: string;
  priority: 'critical' | 'high' | 'normal';
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  escalatedBy: string;
  escalatedAt: string;
  assignedTo: string | null;
  customer: { name: string; contact: string };
  decision: {
    title: string;
    severity: string;
    exposure: number;
    recommendedAction: string;
  };
  comments: Array<{
    id: string;
    author: string;
    text: string;
    timestamp: string;
  }>;
  timeline: Array<{
    action: string;
    actor: string;
    timestamp: string;
  }>;
}

export function generateEscalationDetail(id: string): EscalationDetail {
  const now = Date.now();

  return {
    id,
    decisionId: `dec_${rng.int(1, 12).toString().padStart(3, '0')}`,
    reason: 'Exposure exceeds $200K threshold — requires manager approval for REROUTE action',
    priority: rng.pick(['critical', 'high', 'normal'] as const),
    status: rng.pick(['pending', 'in_review'] as const),
    escalatedBy: 'Sarah Chen',
    escalatedAt: new Date(now - rng.int(1, 12) * 3600000).toISOString(),
    assignedTo: rng.chance(0.5) ? 'David Park' : null,
    customer: {
      name: rng.pick(['ACME Logistics', 'Global Trade Inc', 'Maersk Line']),
      contact: rng.pick(['Sarah Chen', 'Raj Patel', 'Lars Andersen']),
    },
    decision: {
      title: 'Red Sea Route Disruption — Reroute Required',
      severity: rng.pick(['CRITICAL', 'HIGH']),
      exposure: rng.int(150, 500) * 1000,
      recommendedAction: rng.pick(['REROUTE', 'DELAY', 'INSURE']),
    },
    comments: [
      {
        id: 'cmt_1',
        author: 'Sarah Chen',
        text: 'Escalating due to high exposure. Customer has time-sensitive cargo.',
        timestamp: new Date(now - 10 * 3600000).toISOString(),
      },
      {
        id: 'cmt_2',
        author: 'RISKCAST Engine',
        text: 'Auto-analysis: Reroute via Cape adds 10-12 days, estimated cost increase $8,500/TEU.',
        timestamp: new Date(now - 9.5 * 3600000).toISOString(),
      },
    ],
    timeline: [
      { action: 'Decision created', actor: 'RISKCAST Engine', timestamp: new Date(now - 12 * 3600000).toISOString() },
      { action: 'Escalated for review', actor: 'Sarah Chen', timestamp: new Date(now - 10 * 3600000).toISOString() },
      { action: 'Assigned to David Park', actor: 'System', timestamp: new Date(now - 8 * 3600000).toISOString() },
    ],
  };
}
