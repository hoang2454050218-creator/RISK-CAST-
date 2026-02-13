import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  signalKeys,
  useSignalsList,
  useSignal,
  useDismissSignal,
  useGenerateDecision,
} from '@/hooks/useSignals';

// Stub fetch so withMockFallback falls back to mock data immediately
const fetchMock = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
vi.stubGlobal('fetch', fetchMock);

afterAll(() => {
  vi.unstubAllGlobals();
});

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// ──────────────────────────────────────
// Query key structure
// ──────────────────────────────────────

describe('signalKeys', () => {
  it('has "all" key equal to ["signals"]', () => {
    expect(signalKeys.all).toEqual(['signals']);
  });

  it('generates correct "detail" key for a given id', () => {
    expect(signalKeys.detail('sig_123')).toEqual(['signals', 'detail', 'sig_123']);
  });

  it('generates correct "lists" key', () => {
    expect(signalKeys.lists()).toEqual(['signals', 'list']);
  });

  it('generates correct "list" key with filters', () => {
    const filters = { event_type: 'ROUTE_DISRUPTION' };
    expect(signalKeys.list(filters)).toEqual(['signals', 'list', filters]);
  });
});

// ──────────────────────────────────────
// useSignalsList
// ──────────────────────────────────────

describe('useSignalsList', () => {
  it('returns signal data via mock fallback', async () => {
    const { result } = renderHook(() => useSignalsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data!.length).toBeGreaterThan(0);
  });

  it('each signal has a signal_id and event_type', async () => {
    const { result } = renderHook(() => useSignalsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    for (const signal of result.current.data!) {
      expect(signal.signal_id).toBeDefined();
      expect(typeof signal.signal_id).toBe('string');
      expect(signal.event_type).toBeDefined();
    }
  });
});

// ──────────────────────────────────────
// useSignal
// ──────────────────────────────────────

describe('useSignal', () => {
  it('returns data when called with a valid signal id', async () => {
    const { result } = renderHook(() => useSignal('sig_red_sea_001'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });

  it('returns undefined data when id is undefined (query disabled)', () => {
    const { result } = renderHook(() => useSignal(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });
});

// ──────────────────────────────────────
// Mutation hooks
// ──────────────────────────────────────

describe('useDismissSignal', () => {
  it('returns a mutate function', () => {
    const { result } = renderHook(() => useDismissSignal(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
  });
});

describe('useGenerateDecision', () => {
  it('returns mutate and mutateAsync functions', () => {
    const { result } = renderHook(() => useGenerateDecision(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
    expect(typeof result.current.mutateAsync).toBe('function');
  });
});
