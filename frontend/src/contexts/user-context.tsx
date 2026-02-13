/**
 * UserContext — Provides user identity data throughout the app.
 *
 * Reads from AuthProvider on mount. Falls back to a default profile
 * if auth context hasn't resolved yet.
 *
 * All components that display user info should consume this context
 * instead of hardcoding names or emails.
 */

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { useAuth, type AuthUser, type AuthRole } from '@/lib/auth';

// ─── Types ───────────────────────────────────────────────
export type UserRole = AuthRole | 'admin' | 'viewer';

export interface UserProfile {
  /** Unique user ID. */
  id: string;
  /** Display name (e.g. "Sarah Chen"). */
  name: string;
  /** Email address. */
  email: string;
  /** Role determines which actions are available. */
  role: UserRole;
  /** Department name. */
  department: string;
  /** URL to avatar image (optional). */
  avatarUrl?: string;
  /** Short initial(s) derived from name, used in avatar fallback. */
  initials: string;
}

interface UserContextValue {
  /** Current user profile. */
  user: UserProfile;
  /** Update profile fields (partial merge). */
  updateUser: (partial: Partial<Omit<UserProfile, 'initials'>>) => void;
  /** Whether the user is authenticated. */
  isAuthenticated: boolean;
}

// ─── Helpers ─────────────────────────────────────────────
function getInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function authUserToProfile(authUser: AuthUser): UserProfile {
  return {
    id: authUser.id,
    name: authUser.name,
    email: authUser.email,
    role: authUser.role,
    department: authUser.department,
    initials: getInitials(authUser.name),
  };
}

const DEFAULT_USER: UserProfile = {
  id: 'usr_default',
  name: 'Demo User',
  email: 'demo@riskcast.io',
  role: 'analyst',
  department: 'Risk Operations',
  initials: 'DU',
};

// ─── Context ─────────────────────────────────────────────
const UserContext = createContext<UserContextValue | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const { user: authUser, isAuthenticated } = useAuth();
  const [user, setUser] = useState<UserProfile>(
    () => (authUser ? authUserToProfile(authUser) : DEFAULT_USER),
  );

  // Sync from auth context when it changes
  useEffect(() => {
    if (authUser) {
      setUser(authUserToProfile(authUser));
    }
  }, [authUser]);

  const updateUser = useCallback((partial: Partial<Omit<UserProfile, 'initials'>>) => {
    setUser((prev) => {
      const next = { ...prev, ...partial };
      next.initials = getInitials(next.name);
      return next;
    });
  }, []);

  return (
    <UserContext.Provider value={{ user, updateUser, isAuthenticated }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error('useUser must be used within a <UserProvider>');
  }
  return ctx;
}
