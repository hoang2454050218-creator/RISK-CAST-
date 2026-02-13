/**
 * Dashboard data generator — aggregates from entities.
 */

import { rng } from '../seed';
import { CUSTOMERS, SHIPMENTS } from '../entities';
import { CHOKEPOINTS } from '../constants';

export interface DashboardData {
  stats: {
    activeDecisions: number;
    pendingEscalations: number;
    totalExposure: number;
    avgResponseTime: string;
    activeDecisionsTrend: number;
    pendingEscalationsTrend: number;
    totalExposureTrend: number;
  };
  urgentDecisions: Array<{
    id: string;
    title: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    urgency: 'IMMEDIATE' | 'URGENT' | 'SOON' | 'WATCH';
    customer: string;
    exposure: number;
    deadline: string;
    action: string;
  }>;
  chokepointHealth: Array<{
    id: string;
    name: string;
    status: 'critical' | 'degraded' | 'operational';
    transitDelay: number;
    affectedShipments: number;
  }>;
  recentActivity: Array<{
    id: string;
    type: 'decision' | 'signal' | 'escalation' | 'customer';
    title: string;
    timestamp: string;
    actor: string;
  }>;
  lastUpdated: string;
}

export function generateDashboardData(): DashboardData {
  const now = Date.now();

  const urgentDecisions = [
    {
      id: 'dec_001', title: 'Red Sea Route Disruption — Reroute Required',
      severity: 'CRITICAL' as const, urgency: 'IMMEDIATE' as const,
      customer: 'ACME Logistics', exposure: 235_000,
      deadline: new Date(now + 4 * 3600000).toISOString(), action: 'REROUTE',
    },
    {
      id: 'dec_002', title: 'Suez Canal Congestion — Delay Advisory',
      severity: 'HIGH' as const, urgency: 'URGENT' as const,
      customer: 'Global Trade Inc', exposure: 128_000,
      deadline: new Date(now + 12 * 3600000).toISOString(), action: 'DELAY',
    },
    {
      id: 'dec_003', title: 'Port Congestion Singapore — Monitor',
      severity: 'MEDIUM' as const, urgency: 'SOON' as const,
      customer: 'Pacific Rim Trading', exposure: 67_000,
      deadline: new Date(now + 48 * 3600000).toISOString(), action: 'MONITOR',
    },
  ];

  const chokepointHealth = CHOKEPOINTS.map(cp => ({
    id: cp.id,
    name: cp.name,
    status: cp.riskLevel === 'HIGH' ? 'critical' as const : cp.riskLevel === 'MEDIUM' ? 'degraded' as const : 'operational' as const,
    transitDelay: cp.riskLevel === 'HIGH' ? rng.int(5, 14) : cp.riskLevel === 'MEDIUM' ? rng.int(1, 4) : 0,
    affectedShipments: SHIPMENTS.filter(s => s.chokepoints.includes(cp.id)).length,
  }));

  const recentActivity = [
    { id: 'act_1', type: 'decision' as const, title: 'Decision DEC-001 acknowledged', timestamp: new Date(now - rng.int(5, 30) * 60000).toISOString(), actor: 'Sarah Chen' },
    { id: 'act_2', type: 'signal' as const, title: 'New signal: Houthi attack reported', timestamp: new Date(now - rng.int(30, 90) * 60000).toISOString(), actor: 'OMEN Engine' },
    { id: 'act_3', type: 'escalation' as const, title: 'Escalation ESC-004 approved', timestamp: new Date(now - rng.int(60, 180) * 60000).toISOString(), actor: 'David Park' },
    { id: 'act_4', type: 'customer' as const, title: 'VinaTech Export onboarded', timestamp: new Date(now - rng.int(180, 360) * 60000).toISOString(), actor: 'System' },
    { id: 'act_5', type: 'signal' as const, title: 'Rate spike detected on Asia-Europe', timestamp: new Date(now - rng.int(120, 300) * 60000).toISOString(), actor: 'OMEN Engine' },
  ];

  const totalExposure = CUSTOMERS.reduce((sum, c) => sum + c.totalExposure, 0);

  return {
    stats: {
      activeDecisions: rng.int(8, 14),
      pendingEscalations: rng.int(2, 5),
      totalExposure,
      avgResponseTime: `${rng.float(1.2, 2.8).toFixed(1)}h`,
      activeDecisionsTrend: rng.int(-2, 4),
      pendingEscalationsTrend: rng.int(-1, 2),
      totalExposureTrend: rng.int(-50000, 150000),
    },
    urgentDecisions,
    chokepointHealth,
    recentActivity,
    lastUpdated: new Date(now - rng.int(1, 10) * 60000).toISOString(),
  };
}
