/**
 * Audit trail generator — system events with integrity hashes.
 */

import { rng } from '../seed';

export interface AuditEvent {
  id: string;
  timestamp: string;
  type: 'DECISION_CREATED' | 'DECISION_ACKNOWLEDGED' | 'DECISION_OVERRIDDEN' | 'DECISION_ESCALATED' | 'SIGNAL_DETECTED' | 'SIGNAL_DISMISSED' | 'CUSTOMER_ONBOARDED' | 'SYSTEM_EVENT' | 'AUTH_EVENT';
  actor: string;
  actorRole: string;
  action: string;
  target: string;
  details: string;
  integrityHash: string;
  severity: 'info' | 'warning' | 'critical';
}

const ACTORS = [
  { name: 'RISKCAST Engine', role: 'SYSTEM' },
  { name: 'Sarah Chen', role: 'ANALYST' },
  { name: 'David Park', role: 'MANAGER' },
  { name: 'Minh Nguyen', role: 'EXECUTIVE' },
];

function generateHash(): string {
  const chars = 'abcdef0123456789';
  let hash = '';
  for (let i = 0; i < 64; i++) hash += chars[Math.floor(rng.next() * chars.length)];
  return hash;
}

export function generateAuditTrail(): AuditEvent[] {
  const now = Date.now();
  const events: AuditEvent[] = [];

  const templates: Array<Omit<AuditEvent, 'id' | 'timestamp' | 'integrityHash'>> = [
    { type: 'DECISION_CREATED', actor: 'RISKCAST Engine', actorRole: 'SYSTEM', action: 'Decision generated', target: 'DEC-2024-001', details: 'Red Sea disruption — REROUTE recommended. Exposure: $235,000', severity: 'warning' },
    { type: 'DECISION_ACKNOWLEDGED', actor: 'Sarah Chen', actorRole: 'ANALYST', action: 'Decision acknowledged', target: 'DEC-2024-001', details: 'Accepted REROUTE recommendation via Cape of Good Hope', severity: 'info' },
    { type: 'SIGNAL_DETECTED', actor: 'RISKCAST Engine', actorRole: 'SYSTEM', action: 'Signal detected', target: 'SIG-RS-0156', details: 'Houthi missile attack — Polymarket probability: 87%', severity: 'critical' },
    { type: 'DECISION_ESCALATED', actor: 'David Park', actorRole: 'MANAGER', action: 'Decision escalated', target: 'DEC-2024-003', details: 'Escalated to executive review — exposure exceeds $500K threshold', severity: 'warning' },
    { type: 'DECISION_OVERRIDDEN', actor: 'Minh Nguyen', actorRole: 'EXECUTIVE', action: 'Decision overridden', target: 'DEC-2024-002', details: 'Override: DELAY instead of REROUTE — vendor commitment window', severity: 'warning' },
    { type: 'CUSTOMER_ONBOARDED', actor: 'David Park', actorRole: 'MANAGER', action: 'Customer onboarded', target: 'VinaTech Export', details: '3 active shipments, $520K total exposure', severity: 'info' },
    { type: 'SYSTEM_EVENT', actor: 'RISKCAST Engine', actorRole: 'SYSTEM', action: 'Model updated', target: 'OMEN v2.4.1', details: 'Signal processing model updated — accuracy +2.3%', severity: 'info' },
    { type: 'AUTH_EVENT', actor: 'Sarah Chen', actorRole: 'ANALYST', action: 'Login', target: 'analyst@riskcast.io', details: 'Successful authentication from 103.15.XX.XX', severity: 'info' },
    { type: 'SIGNAL_DISMISSED', actor: 'Sarah Chen', actorRole: 'ANALYST', action: 'Signal dismissed', target: 'SIG-WE-0089', details: 'Weather event — tropical storm downgraded, no impact on routes', severity: 'info' },
    { type: 'DECISION_CREATED', actor: 'RISKCAST Engine', actorRole: 'SYSTEM', action: 'Decision generated', target: 'DEC-2024-004', details: 'Panama Canal congestion — MONITOR recommended', severity: 'info' },
  ];

  for (let i = 0; i < 50; i++) {
    const template = templates[i % templates.length];
    const hoursAgo = rng.float(0.5, 168); // up to 7 days
    events.push({
      id: `audit_${String(i + 1).padStart(3, '0')}`,
      timestamp: new Date(now - hoursAgo * 3600000).toISOString(),
      integrityHash: generateHash(),
      ...template,
    });
  }

  return events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}
