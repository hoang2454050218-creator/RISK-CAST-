/**
 * Escalation hooks — real data from backend API with mock fallback.
 *
 * Uses withMockFallback for graceful degradation when backend is offline.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getEscalations,
  getEscalation,
  approveEscalation,
  rejectEscalation,
  assignEscalation,
  commentEscalation,
  withMockFallback,
} from '@/lib/api';

import type { Escalation } from '@/components/domain/escalations';

// ── Mock escalation data for offline fallback ───────────────

const mockEscalations: Escalation[] = [
  {
    id: 'esc_001',
    decision_id: 'dec_003',
    title: 'Red Sea Reroute — Exposure Exceeds $200K Threshold',
    reason: 'Automated escalation: cargo exposure $235,000 requires manager sign-off for REROUTE action',
    priority: 'CRITICAL',
    status: 'PENDING',
    exposure_usd: 235000,
    customer: 'ACME Logistics',
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    sla_deadline: new Date(Date.now() + 4 * 3600000).toISOString(),
    assigned_to: 'David Park',
  },
  {
    id: 'esc_002',
    decision_id: 'dec_007',
    title: 'Panama Canal Congestion — Insurance Premium Spike',
    reason: 'Insurance cost increase >15% triggers mandatory review per risk policy',
    priority: 'HIGH',
    status: 'IN_REVIEW',
    exposure_usd: 180000,
    customer: 'Global Trade Inc',
    created_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    sla_deadline: new Date(Date.now() + 16 * 3600000).toISOString(),
    assigned_to: 'Sarah Chen',
  },
  {
    id: 'esc_003',
    decision_id: 'dec_012',
    title: 'Malacca Strait Delay — Multi-Customer Impact',
    reason: 'Delay affects 3+ customers with combined exposure >$500K',
    priority: 'HIGH',
    status: 'PENDING',
    exposure_usd: 520000,
    customer: 'VinaTech Export',
    created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    sla_deadline: new Date(Date.now() + 8 * 3600000).toISOString(),
  },
  {
    id: 'esc_004',
    decision_id: 'dec_015',
    title: 'Cape Route Schedule Change — ETA Review',
    reason: 'Reroute extends transit by 12 days — customer notification required',
    priority: 'NORMAL',
    status: 'RESOLVED',
    exposure_usd: 95000,
    customer: 'Maersk Line',
    created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
    sla_deadline: new Date(Date.now() - 12 * 3600000).toISOString(),
    assigned_to: 'Minh Nguyen',
  },
];

export const escalationKeys = {
  all: ['escalations'] as const,
  lists: () => [...escalationKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...escalationKeys.lists(), filters] as const,
  details: () => [...escalationKeys.all, 'detail'] as const,
  detail: (id: string) => [...escalationKeys.details(), id] as const,
};

export function useEscalationsList(params?: {
  priority?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: escalationKeys.list(params ?? {}),
    queryFn: async () => {
      const data = await withMockFallback(
        () => getEscalations(params),
        { escalations: mockEscalations, total: mockEscalations.length },
      );
      return data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    select: (data) => data.escalations as Escalation[],
    retry: 2,
  });
}

export function useEscalation(id: string | undefined) {
  return useQuery({
    queryKey: escalationKeys.detail(id ?? ''),
    queryFn: () => withMockFallback(
      () => getEscalation(id!),
      mockEscalations.find((e) => e.id === id) ?? mockEscalations[0],
    ),
    enabled: !!id,
    staleTime: 30_000,
    retry: 2,
  });
}

export function useApproveEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: string; notes?: string }) =>
      approveEscalation(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: escalationKeys.lists() }),
  });
}

export function useRejectEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      rejectEscalation(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: escalationKeys.lists() }),
  });
}

export function useAssignEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, assignee }: { id: string; assignee: string }) =>
      assignEscalation(id, assignee),
    onSuccess: () => qc.invalidateQueries({ queryKey: escalationKeys.lists() }),
  });
}

export function useCommentEscalation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, message }: { id: string; message: string }) =>
      commentEscalation(id, message),
    onSuccess: () => qc.invalidateQueries({ queryKey: escalationKeys.lists() }),
  });
}
