/**
 * Audit trail hook — real event log from backend with mock fallback.
 *
 * Uses withMockFallback for graceful degradation when backend is offline.
 */

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { v2Audit, type AuditEvent, type AuditTrailResponse } from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';

export type { AuditEvent };

// ── Mock audit data for offline fallback ────────────────────

const mockAuditEvents: AuditEvent[] = [
  {
    id: 'audit_001',
    timestamp: new Date(Date.now() - 0.5 * 3600000).toISOString(),
    action: 'DECISION_CREATED',
    status: 'success',
    resource_type: 'decision',
    resource_id: 'dec_001',
    user_id: null,
    api_key_prefix: null,
    ip_address: null,
    request_method: 'POST',
    request_path: '/api/decisions',
    details: { summary: 'Red Sea disruption — REROUTE recommended. Exposure: $235,000' },
  },
  {
    id: 'audit_002',
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    action: 'DECISION_ACKNOWLEDGED',
    status: 'success',
    resource_type: 'decision',
    resource_id: 'dec_001',
    user_id: 'user_sarah',
    api_key_prefix: null,
    ip_address: '103.15.42.10',
    request_method: 'POST',
    request_path: '/api/decisions/dec_001/acknowledge',
    details: { summary: 'Accepted REROUTE recommendation via Cape of Good Hope' },
  },
  {
    id: 'audit_003',
    timestamp: new Date(Date.now() - 4 * 3600000).toISOString(),
    action: 'SIGNAL_DETECTED',
    status: 'success',
    resource_type: 'signal',
    resource_id: 'sig_005',
    user_id: null,
    api_key_prefix: null,
    ip_address: null,
    request_method: null,
    request_path: null,
    details: { summary: 'Houthi missile attack near Bab el-Mandeb — Polymarket probability: 87%' },
  },
  {
    id: 'audit_004',
    timestamp: new Date(Date.now() - 8 * 3600000).toISOString(),
    action: 'DECISION_ESCALATED',
    status: 'success',
    resource_type: 'decision',
    resource_id: 'dec_003',
    user_id: 'user_david',
    api_key_prefix: null,
    ip_address: '10.0.1.55',
    request_method: 'POST',
    request_path: '/api/decisions/dec_003/escalate',
    details: { summary: 'Escalated to executive review — exposure exceeds $500K threshold' },
  },
  {
    id: 'audit_005',
    timestamp: new Date(Date.now() - 12 * 3600000).toISOString(),
    action: 'DECISION_OVERRIDDEN',
    status: 'success',
    resource_type: 'decision',
    resource_id: 'dec_002',
    user_id: 'user_minh',
    api_key_prefix: null,
    ip_address: '10.0.1.12',
    request_method: 'POST',
    request_path: '/api/decisions/dec_002/override',
    details: { summary: 'Override: DELAY instead of REROUTE — vendor commitment window' },
  },
  {
    id: 'audit_006',
    timestamp: new Date(Date.now() - 18 * 3600000).toISOString(),
    action: 'SIGNAL_DETECTED',
    status: 'success',
    resource_type: 'signal',
    resource_id: 'sig_008',
    user_id: null,
    api_key_prefix: null,
    ip_address: null,
    request_method: null,
    request_path: null,
    details: { summary: 'Panama Canal water level critical — transit restrictions expected' },
  },
  {
    id: 'audit_007',
    timestamp: new Date(Date.now() - 24 * 3600000).toISOString(),
    action: 'DECISION_CREATED',
    status: 'success',
    resource_type: 'decision',
    resource_id: 'dec_004',
    user_id: null,
    api_key_prefix: null,
    ip_address: null,
    request_method: 'POST',
    request_path: '/api/decisions',
    details: { summary: 'Panama Canal congestion — MONITOR recommended' },
  },
  {
    id: 'audit_008',
    timestamp: new Date(Date.now() - 36 * 3600000).toISOString(),
    action: 'SIGNAL_DETECTED',
    status: 'success',
    resource_type: 'signal',
    resource_id: 'sig_012',
    user_id: null,
    api_key_prefix: null,
    ip_address: null,
    request_method: null,
    request_path: null,
    details: { summary: 'Typhoon warning — Western Pacific, potential impact on Asia-US East route' },
  },
];

const mockAuditTrailResponse: AuditTrailResponse = {
  events: mockAuditEvents,
  total: mockAuditEvents.length,
  has_more: false,
};

export function useAuditTrail(filters?: { action?: string; offset?: number; limit?: number }) {
  return useQuery<AuditTrailResponse>({
    queryKey: ['audit', filters ?? {}],
    queryFn: () => withMockFallback(
      () => v2Audit.list(filters),
      mockAuditTrailResponse,
      'audit-trail',
    ),
    staleTime: 600_000,
    placeholderData: keepPreviousData,
    retry: 2,
  });
}

export function useAuditIntegrity() {
  return useQuery({
    queryKey: ['audit', 'integrity'],
    queryFn: () => withMockFallback(
      () => v2Audit.integrity(),
      // NEVER fake audit integrity — return null chain_intact when using mock data
      { status: 'unavailable', total_entries: mockAuditEvents.length, chain_intact: null as unknown as boolean },
      'audit-integrity',
    ),
    staleTime: 60_000,
    retry: 1,
  });
}
