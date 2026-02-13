/**
 * useFeedback — Suggestion feedback hooks.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { v2Feedback } from '@/lib/api-v2';

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: ({ suggestionId, decision, reason_code, reason_text }: {
      suggestionId: string;
      decision: 'accepted' | 'rejected' | 'deferred';
      reason_code?: string;
      reason_text?: string;
    }) => v2Feedback.submit(suggestionId, { decision, reason_code, reason_text }),
  });
}

export function useFeedbackStats() {
  return useQuery({
    queryKey: ['v2', 'feedback', 'stats'],
    queryFn: () => v2Feedback.stats(),
    staleTime: 60_000,
  });
}
