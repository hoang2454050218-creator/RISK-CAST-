/**
 * Escalation detail hook — real data from backend API with mock fallback.
 */

import { useQuery } from '@tanstack/react-query';
import { getEscalation, withMockFallback } from '@/lib/api';
import { generateEscalationDetail, type EscalationDetail } from '@/lib/mock-data';

export function useEscalationDetail(id: string | undefined) {
  return useQuery<EscalationDetail>({
    queryKey: ['escalation', id ?? ''],
    queryFn: () =>
      withMockFallback(
        () => getEscalation(id!) as Promise<EscalationDetail>,
        generateEscalationDetail(id ?? 'esc_001'),
      ),
    enabled: !!id,
    staleTime: 15_000,
    retry: 2,
  });
}
