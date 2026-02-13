/**
 * useFeedback — Suggestion feedback hooks with mock fallback.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { v2Feedback } from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';
import { toast } from '@/components/ui/toast';

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: ({ suggestionId, decision, reason_code, reason_text }: {
      suggestionId: string;
      decision: 'accepted' | 'rejected' | 'deferred';
      reason_code?: string;
      reason_text?: string;
    }) => v2Feedback.submit(suggestionId, { decision, reason_code, reason_text }),
    onError: (error: Error) => {
      toast.error(`Feedback failed: ${error.message}`);
    },
  });
}

export function useFeedbackStats() {
  return useQuery({
    queryKey: ['v2', 'feedback', 'stats'],
    queryFn: () => withMockFallback(
      () => v2Feedback.stats(),
      { total: 0, by_decision: {}, acceptance_rate: 0 },
    ),
    staleTime: 60_000,
  });
}
