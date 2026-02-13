/**
 * useSignalsV2 — V2 signals data hooks.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { v2Signals, type SignalListResponse } from '@/lib/api-v2';

export function useSignalsV2(params?: { active_only?: boolean; min_severity?: number; limit?: number }) {
  return useQuery<SignalListResponse>({
    queryKey: ['v2', 'signals', params],
    queryFn: () => v2Signals.list(params),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useSignalsSummary() {
  return useQuery({
    queryKey: ['v2', 'signals', 'summary'],
    queryFn: () => v2Signals.summary(),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useTriggerScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => v2Signals.scan(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['v2', 'signals'] });
    },
  });
}
