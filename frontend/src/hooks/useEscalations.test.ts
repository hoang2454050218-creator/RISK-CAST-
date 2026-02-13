import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  escalationKeys,
  useEscalationsList,
  useEscalation,
  useApproveEscalation,
  useRejectEscalation,
  useAssignEscalation,
  useCommentEscalation,
} from '@/hooks/useEscalations';

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

describe('escalationKeys', () => {
  it('has "all" key equal to ["escalations"]', () => {
    expect(escalationKeys.all).toEqual(['escalations']);
  });

  it('generates correct "detail" key for a given id', () => {
    expect(escalationKeys.detail('esc_001')).toEqual(['escalations', 'detail', 'esc_001']);
  });

  it('generates correct "lists" key', () => {
    expect(escalationKeys.lists()).toEqual(['escalations', 'list']);
  });

  it('generates correct "list" key with filters', () => {
    const filters = { priority: 'CRITICAL' };
    expect(escalationKeys.list(filters)).toEqual(['escalations', 'list', filters]);
  });
});

// ──────────────────────────────────────
// useEscalationsList
// ──────────────────────────────────────

describe('useEscalationsList', () => {
  it('returns escalation data via mock fallback', async () => {
    const { result } = renderHook(() => useEscalationsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data!.length).toBeGreaterThan(0);
  });

  it('each escalation has an id and title', async () => {
    const { result } = renderHook(() => useEscalationsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    for (const escalation of result.current.data!) {
      expect(escalation.id).toBeDefined();
      expect(typeof escalation.id).toBe('string');
      expect(escalation.title).toBeDefined();
    }
  });
});

// ──────────────────────────────────────
// useEscalation
// ──────────────────────────────────────

describe('useEscalation', () => {
  it('returns undefined data when id is undefined (query disabled)', () => {
    const { result } = renderHook(() => useEscalation(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('fetches an escalation when a valid id is provided', async () => {
    const { result } = renderHook(() => useEscalation('esc_001'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
  });
});

// ──────────────────────────────────────
// Mutation hooks
// ──────────────────────────────────────

describe('mutation hooks', () => {
  it('useApproveEscalation returns a mutate function', () => {
    const { result } = renderHook(() => useApproveEscalation(), {
      wrapper: createWrapper(),
    });
    expect(typeof result.current.mutate).toBe('function');
  });

  it('useRejectEscalation returns a mutate function', () => {
    const { result } = renderHook(() => useRejectEscalation(), {
      wrapper: createWrapper(),
    });
    expect(typeof result.current.mutate).toBe('function');
  });

  it('useAssignEscalation returns a mutate function', () => {
    const { result } = renderHook(() => useAssignEscalation(), {
      wrapper: createWrapper(),
    });
    expect(typeof result.current.mutate).toBe('function');
  });

  it('useCommentEscalation returns a mutate function', () => {
    const { result } = renderHook(() => useCommentEscalation(), {
      wrapper: createWrapper(),
    });
    expect(typeof result.current.mutate).toBe('function');
  });
});
