/**
 * Reality Engine hook — uses real signals + analytics from backend with mock fallback.
 *
 * Uses withMockFallback for graceful degradation when backend is offline.
 * The "reality" view is built from real OMEN signals and internal analytics.
 */

import { useQuery } from '@tanstack/react-query';
import { v2Signals, v2Analytics, type AnalyticsTimeSeries } from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';

export interface RealityRate {
  route: string;
  currentRate: number;
  previousRate: number;
  change: number;
  lastUpdated: string;
}

export interface RealityVesselAlert {
  id: string;
  vesselName: string;
  alertType: string;
  description: string;
  timestamp: string;
  location: string;
}

export interface RealityData {
  signals: Array<{
    id: string;
    signal_type: string;
    severity_score: number | null;
    confidence: number;
    is_active: boolean;
    created_at: string;
  }>;
  risk_trend: AnalyticsTimeSeries | null;
  total_active_signals: number;
  last_updated: string | null;
  rates: RealityRate[];
  vesselAlerts: RealityVesselAlert[];
}

// ── Mock reality data for offline fallback ───────────────────

const mockRealityData: RealityData = {
  signals: [
    {
      id: 'sig_001',
      signal_type: 'GEOPOLITICAL',
      severity_score: 8.5,
      confidence: 0.87,
      is_active: true,
      created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    },
    {
      id: 'sig_002',
      signal_type: 'WEATHER',
      severity_score: 6.2,
      confidence: 0.75,
      is_active: true,
      created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
    },
    {
      id: 'sig_003',
      signal_type: 'PORT_CONGESTION',
      severity_score: 7.1,
      confidence: 0.82,
      is_active: true,
      created_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    },
    {
      id: 'sig_004',
      signal_type: 'MARKET',
      severity_score: 5.4,
      confidence: 0.68,
      is_active: true,
      created_at: new Date(Date.now() - 12 * 3600000).toISOString(),
    },
    {
      id: 'sig_005',
      signal_type: 'GEOPOLITICAL',
      severity_score: 9.1,
      confidence: 0.92,
      is_active: true,
      created_at: new Date(Date.now() - 1 * 3600000).toISOString(),
    },
  ],
  risk_trend: {
    period: '7d',
    generated_at: new Date().toISOString(),
    data_sufficiency: 'mock',
    data_points: 7,
    message: 'Mock data — backend offline',
    series: [
      { date: '2026-02-06', value: 4.2, count: 8 },
      { date: '2026-02-07', value: 5.1, count: 12 },
      { date: '2026-02-08', value: 4.8, count: 10 },
      { date: '2026-02-09', value: 6.3, count: 15 },
      { date: '2026-02-10', value: 5.7, count: 11 },
      { date: '2026-02-11', value: 7.2, count: 18 },
      { date: '2026-02-12', value: 6.8, count: 14 },
    ],
  },
  total_active_signals: 5,
  last_updated: new Date(Date.now() - 1 * 3600000).toISOString(),
  rates: [
    { route: 'Asia–Europe', currentRate: 3200, previousRate: 2850, change: 12.3, lastUpdated: new Date(Date.now() - 2 * 3600000).toISOString() },
    { route: 'Asia–US East', currentRate: 4100, previousRate: 4300, change: -4.7, lastUpdated: new Date(Date.now() - 1 * 3600000).toISOString() },
  ],
  vesselAlerts: [
    { id: 'va_001', vesselName: 'MSC Oscar', alertType: 'port_congestion', description: 'Port congestion — 48h delay', timestamp: new Date(Date.now() - 3 * 3600000).toISOString(), location: 'Singapore' },
  ],
};

export function useRealityEngine() {
  return useQuery<RealityData>({
    queryKey: ['reality'],
    queryFn: () => withMockFallback(
      async () => {
        // Fetch real signals and risk trend in parallel
        const [signalData, trendData] = await Promise.allSettled([
          v2Signals.list({ active_only: true, limit: 50 }),
          v2Analytics.riskOverTime(7),
        ]);

        const signals =
          signalData.status === 'fulfilled' ? signalData.value.signals : [];
        const trend =
          trendData.status === 'fulfilled' ? trendData.value : null;

        return {
          signals: signals.map((s) => ({
            id: s.id,
            signal_type: s.signal_type,
            severity_score: s.severity_score,
            confidence: s.confidence,
            is_active: s.is_active,
            created_at: s.created_at,
          })),
          risk_trend: trend,
          total_active_signals: signals.length,
          last_updated: signals[0]?.created_at ?? null,
          rates: [],
          vesselAlerts: [],
        };
      },
      mockRealityData,
    ),
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 2,
  });
}
