import { renderHook, act } from '@testing-library/react';
import { UserProvider, useUser } from '@/contexts/user-context';
import type { ReactNode } from 'react';

const wrapper = ({ children }: { children: ReactNode }) => <UserProvider>{children}</UserProvider>;

beforeEach(() => {
  localStorage.clear();
});

// ── UserProvider defaults ────────────────────────────────

describe('UserProvider', () => {
  it('provides default user when no localStorage data exists', () => {
    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current.user.name).toBe('Demo User');
    expect(result.current.user.email).toBe('demo@riskcast.io');
  });

  it('user has correct default values', () => {
    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current.user).toEqual({
      name: 'Demo User',
      email: 'demo@riskcast.io',
      role: 'admin',
      initials: 'DU',
    });
  });

  it('updateUser merges partial fields and recomputes initials', () => {
    const { result } = renderHook(() => useUser(), { wrapper });

    act(() => {
      result.current.updateUser({ name: 'Sarah Chen' });
    });

    expect(result.current.user.name).toBe('Sarah Chen');
    expect(result.current.user.initials).toBe('SC');
    // Other fields remain unchanged
    expect(result.current.user.email).toBe('demo@riskcast.io');
    expect(result.current.user.role).toBe('admin');
  });

  it('updateUser can change the role', () => {
    const { result } = renderHook(() => useUser(), { wrapper });

    act(() => {
      result.current.updateUser({ role: 'analyst' });
    });

    expect(result.current.user.role).toBe('analyst');
    // Name and initials untouched
    expect(result.current.user.name).toBe('Demo User');
    expect(result.current.user.initials).toBe('DU');
  });

  it('isAuthenticated is true', () => {
    const { result } = renderHook(() => useUser(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('persists user to localStorage on update', () => {
    const { result } = renderHook(() => useUser(), { wrapper });

    act(() => {
      result.current.updateUser({ name: 'Jane Doe' });
    });

    const stored = JSON.parse(localStorage.getItem('riskcast:user') ?? '{}');
    expect(stored.name).toBe('Jane Doe');
  });
});

// ── useUser outside provider ─────────────────────────────

describe('useUser', () => {
  it('throws when used outside UserProvider', () => {
    // Suppress the React error boundary console noise
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useUser());
    }).toThrow('useUser must be used within a <UserProvider>');

    consoleSpy.mockRestore();
  });
});
