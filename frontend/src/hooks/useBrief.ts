/**
 * useBrief — Morning Brief data hook.
 */

import { useQuery } from '@tanstack/react-query';
import { v2Briefs, type MorningBrief } from '@/lib/api-v2';

export function useBrief() {
  return useQuery<MorningBrief>({
    queryKey: ['v2', 'brief', 'today'],
    queryFn: () => v2Briefs.today(),
    staleTime: 5 * 60_000,    // 5 minutes
    retry: 1,
  });
}

export function useBriefByDate(date: string) {
  return useQuery<MorningBrief>({
    queryKey: ['v2', 'brief', date],
    queryFn: () => v2Briefs.byDate(date),
    enabled: !!date,
  });
}
