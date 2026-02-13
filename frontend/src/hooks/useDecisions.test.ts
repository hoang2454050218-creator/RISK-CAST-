import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  decisionKeys,
  useDecisionsList,
  useDecision,
  useAcknowledgeDecision,
  useOverrideDecision,
  useEscalateDecision,
} from '@/hooks/useDecisions';

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

describe('decisionKeys', () => {
  it('has "all" key equal to ["decisions"]', () => {
    expect(decisionKeys.all).toEqual(['decisions']);
  });

  it('generates correct "lists" key', () => {
    expect(decisionKeys.lists()).toEqual(['decisions', 'list']);
  });

  it('generates correct "detail" key for a given id', () => {
    expect(decisionKeys.detail('abc')).toEqual(['decisions', 'detail', 'abc']);
  });

  it('generates correct "details" base key', () => {
    expect(decisionKeys.details()).toEqual(['decisions', 'detail']);
  });

  it('generates correct "list" key with filters', () => {
    const filters = { status: 'PENDING' };
    expect(decisionKeys.list(filters)).toEqual(['decisions', 'list', filters]);
  });
});

// ──────────────────────────────────────
// useDecisionsList
// ──────────────────────────────────────

describe('useDecisionsList', () => {
  it('returns decision data via mock fallback', async () => {
    const { result } = renderHook(() => useDecisionsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toBeDefined();
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data!.length).toBeGreaterThan(0);
  });

  it('each decision has a decision_id', async () => {
    const { result } = renderHook(() => useDecisionsList(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    for (const decision of result.current.data!) {
      expect(decision.decision_id).toBeDefined();
      expect(typeof decision.decision_id).toBe('string');
    }
  });
});

// ──────────────────────────────────────
// useDecision
// ──────────────────────────────────────

describe('useDecision', () => {
  it('returns undefined data when id is undefined (query disabled)', () => {
    const { result } = renderHook(() => useDecision(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('fetches a decision when a valid id is provided', async () => {
    const { result } = renderHook(() => useDecision('dec_a1b2c3d4e5f6g7h8i9j0'), {
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

describe('useAcknowledgeDecision', () => {
  it('returns a mutate function', () => {
    const { result } = renderHook(() => useAcknowledgeDecision(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
    expect(typeof result.current.mutateAsync).toBe('function');
  });
});

describe('useOverrideDecision', () => {
  it('returns a mutate function', () => {
    const { result } = renderHook(() => useOverrideDecision(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
  });
});

describe('useEscalateDecision', () => {
  it('returns a mutate function', () => {
    const { result } = renderHook(() => useEscalateDecision(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe('function');
  });
});
