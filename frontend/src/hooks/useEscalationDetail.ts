/**
 * Escalation detail hook — real data from backend API.
 *
 * ZERO MOCK DATA.
 */

import { useQuery } from '@tanstack/react-query';
import { getEscalation } from '@/lib/api';

export function useEscalationDetail(id: string | undefined) {
  return useQuery({
    queryKey: ['escalation', id ?? ''],
    queryFn: () => getEscalation(id!),
    enabled: !!id,
    staleTime: 15_000,
    retry: 2,
  });
}
