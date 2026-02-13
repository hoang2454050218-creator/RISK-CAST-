/**
 * Signal hooks — real data from backend API with mock fallback.
 *
 * Transforms V2 backend signals into the frontend Signal format.
 * Falls back to mock data when backend is unavailable.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSignals, withMockFallback, getSignal, dismissSignal, generateDecisionFromSignal } from '@/lib/api';
import { mockSignals } from '@/lib/mock-data/legacy';
import type { Signal, EventType, SignalSource, SignalStatus } from '@/types/signal';

export const signalKeys = {
  all: ['signals'] as const,
  lists: () => [...signalKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...signalKeys.lists(), filters] as const,
  details: () => [...signalKeys.all, 'detail'] as const,
  detail: (id: string) => [...signalKeys.details(), id] as const,
};

// ── Backend → Frontend transformation ────────────────────────

function isFrontendSignal(s: unknown): s is Signal {
  return typeof s === 'object' && s !== null && 'event_type' in s && 'signal_id' in s && 'event_title' in s;
}

function mapSignalType(t: string): EventType {
  const map: Record<string, EventType> = {
    ROUTE_DISRUPTION: 'ROUTE_DISRUPTION', PORT_CONGESTION: 'PORT_CONGESTION',
    WEATHER_EVENT: 'WEATHER_EVENT', GEOPOLITICAL: 'GEOPOLITICAL',
    RATE_SPIKE: 'RATE_SPIKE', CARRIER_ISSUE: 'CARRIER_ISSUE', CUSTOMS_DELAY: 'CUSTOMS_DELAY',
    route_disruption: 'ROUTE_DISRUPTION', port_congestion: 'PORT_CONGESTION',
    weather_event: 'WEATHER_EVENT', weather: 'WEATHER_EVENT', geopolitical: 'GEOPOLITICAL',
    rate_spike: 'RATE_SPIKE', carrier_issue: 'CARRIER_ISSUE', customs_delay: 'CUSTOMS_DELAY',
    market: 'RATE_SPIKE', operational: 'CARRIER_ISSUE', regulatory: 'CUSTOMS_DELAY',
  };
  return map[t] ?? 'GEOPOLITICAL';
}

function mapSource(s: string): SignalSource {
  const map: Record<string, SignalSource> = {
    POLYMARKET: 'POLYMARKET', NEWS: 'NEWS', AIS: 'AIS', RATES: 'RATES',
    WEATHER: 'WEATHER', GOVERNMENT: 'GOVERNMENT', SOCIAL_MEDIA: 'SOCIAL_MEDIA',
    polymarket: 'POLYMARKET', news: 'NEWS', ais: 'AIS', rates: 'RATES',
    weather: 'WEATHER', government: 'GOVERNMENT', social_media: 'SOCIAL_MEDIA',
    omen_scan: 'NEWS', manual: 'NEWS', api: 'NEWS',
  };
  return map[s] ?? 'NEWS';
}

function mapSignalStatus(raw: Record<string, unknown>): SignalStatus {
  if (raw.status === 'ACTIVE' || raw.status === 'CONFIRMED' || raw.status === 'EXPIRED' || raw.status === 'DISMISSED') {
    return raw.status as SignalStatus;
  }
  return (raw.is_active === true || raw.is_active === 1) ? 'ACTIVE' : 'EXPIRED';
}

function transformSignal(raw: Record<string, unknown>): Signal {
  if (isFrontendSignal(raw)) return raw;

  const context = (raw.context ?? {}) as Record<string, unknown>;
  const evidence = raw.evidence as Record<string, unknown> | undefined;

  return {
    signal_id: String(raw.signal_id ?? raw.id ?? ''),
    event_type: mapSignalType(String(raw.event_type ?? raw.signal_type ?? 'GEOPOLITICAL')),
    event_title: String(raw.event_title ?? raw.title ?? context.title ?? `${raw.signal_type ?? 'Signal'} detected`),
    event_description: String(raw.event_description ?? context.description ?? context.summary ?? ''),
    probability: Number(raw.probability ?? (raw.severity_score ? Number(raw.severity_score) / 100 : 0.5)),
    confidence: Number(raw.confidence ?? 0.5),
    affected_chokepoints: (raw.affected_chokepoints as string[]) ?? [],
    affected_routes: (raw.affected_routes as string[]) ?? [],
    affected_regions: (raw.affected_regions as string[]) ?? [],
    evidence: Array.isArray(raw.evidence)
      ? raw.evidence
      : evidence
        ? [{ source_type: mapSource(String(raw.source ?? '')), source_name: String(raw.source ?? ''), data_point: JSON.stringify(evidence).slice(0, 200), timestamp: String(raw.created_at ?? new Date().toISOString()), confidence: Number(raw.confidence ?? 0.5) }]
        : [],
    primary_source: mapSource(String(raw.primary_source ?? raw.source ?? 'NEWS')),
    status: mapSignalStatus(raw),
    created_at: String(raw.created_at ?? new Date().toISOString()),
    updated_at: String(raw.updated_at ?? new Date().toISOString()),
    estimated_impact_usd: Number(raw.estimated_impact_usd ?? 0),
    customers_affected: Number(raw.customers_affected ?? 0),
    shipments_affected: Number(raw.shipments_affected ?? 0),
    decision_ids: (raw.decision_ids as string[]) ?? [],
  };
}

export function useSignalsList(params?: {
  event_type?: string;
  min_probability?: number;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: signalKeys.list(params ?? {}),
    queryFn: async () => {
      const data = await withMockFallback(
        () => getSignals(params),
        { signals: mockSignals, total: mockSignals.length },
      );
      // Transform backend signals to frontend format
      const signals = (data.signals ?? []).map((s) =>
        transformSignal(s as unknown as Record<string, unknown>),
      );
      return signals;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 2,
  });
}

export function useSignal(signalId: string | undefined) {
  return useQuery({
    queryKey: signalKeys.detail(signalId ?? ''),
    queryFn: async () => {
      const data = await withMockFallback(
        () => getSignal(signalId!),
        mockSignals.find((s) => s.signal_id === signalId) ?? mockSignals[0],
      );
      return transformSignal(data as unknown as Record<string, unknown>);
    },
    enabled: !!signalId,
    staleTime: 30_000,
    retry: 2,
  });
}

export function useDismissSignal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ signalId, reason }: { signalId: string; reason?: string }) =>
      dismissSignal(signalId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: signalKeys.lists() });
    },
  });
}

export function useGenerateDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (signalId: string) => generateDecisionFromSignal(signalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: signalKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
    },
  });
}
