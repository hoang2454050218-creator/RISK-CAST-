/**
 * useBrief — Morning Brief data hook.
 * Falls back to mock data when backend is unavailable.
 */

import { useQuery } from '@tanstack/react-query';
import { v2Briefs, type MorningBrief } from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';

const mockBrief: MorningBrief = {
  id: 'brief_mock_today',
  brief_date: new Date().toISOString().slice(0, 10),
  content: 'Good morning! The supply chain landscape shows 3 active risk signals today. Red Sea disruptions continue affecting Asia-Europe routes. Panama Canal restrictions are creating delays for trans-Pacific shipments. Monitor rate movements closely.',
  priority_items: [
    { signal_id: 'sig_red_sea_001', signal_type: 'ROUTE_DISRUPTION', severity_score: 9, confidence: 0.87, summary: 'Red Sea shipping disruption continues' },
    { signal_id: 'sig_panama_002', signal_type: 'PORT_CONGESTION', severity_score: 7, confidence: 0.88, summary: 'Panama Canal capacity restrictions extended' },
    { signal_id: 'sig_rates_003', signal_type: 'RATE_SPIKE', severity_score: 6, confidence: 0.75, summary: 'Trans-Pacific spot rates surge 28% WoW' },
  ],
};

export function useBrief() {
  return useQuery<MorningBrief>({
    queryKey: ['v2', 'brief', 'today'],
    queryFn: () => withMockFallback(() => v2Briefs.today(), mockBrief),
    staleTime: 5 * 60_000,    // 5 minutes
    retry: 1,
  });
}

export function useBriefByDate(date: string) {
  return useQuery<MorningBrief>({
    queryKey: ['v2', 'brief', date],
    queryFn: () => withMockFallback(() => v2Briefs.byDate(date), { ...mockBrief, brief_date: date }),
    enabled: !!date,
  });
}
