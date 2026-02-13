/**
 * Authentication system for RISKCAST.
 *
 * Calls real V2 backend for login/register.
 * Stores JWT from backend in localStorage (both keys for compat).
 *
 * Exports:
 * - AuthProvider: wrap the app
 * - useAuth: access auth state + actions
 * - ProtectedRoute: redirects unauthenticated users to /auth/login
 */

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

// ─── Types ───────────────────────────────────────────────
export type AuthRole = 'analyst' | 'manager' | 'executive' | 'admin';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: AuthRole;
  department: string;
  createdAt?: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

// ─── Storage Keys ────────────────────────────────────────
const TOKEN_KEY = 'riskcast:auth-token';
const V2_TOKEN_KEY = 'riskcast:v2-token';
const USER_KEY = 'riskcast:auth-user';

// ─── API Base ────────────────────────────────────────────
const API_BASE = import.meta.env.VITE_V2_API_URL || '/api/v1';

// ─── Token Helpers ────────────────────────────────────────
function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    // Real backend tokens have user_id and company_id
    // Old fake tokens have sub/email but no company_id — reject them
    if (!payload.user_id || !payload.company_id) return true;
    if (typeof payload.exp !== 'number') return true;
    // JWT exp is in seconds, not milliseconds
    const expMs = payload.exp > 1e12 ? payload.exp : payload.exp * 1000;
    return Date.now() > expMs;
  } catch {
    return true;
  }
}

function storeTokens(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(V2_TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(V2_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function loadStoredAuth(): { token: string; user: AuthUser } | null {
  try {
    // Try V2 token first, then V1
    const token = localStorage.getItem(V2_TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
    const userJson = localStorage.getItem(USER_KEY);
    if (!token || !userJson) return null;
    if (isTokenExpired(token)) {
      clearTokens();
      return null;
    }
    return { token, user: JSON.parse(userJson) };
  } catch {
    return null;
  }
}

// ─── Context ─────────────────────────────────────────────
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Initialize: check stored auth, or auto-login via API key in dev mode
  useEffect(() => {
    const stored = loadStoredAuth();
    if (stored) {
      // Ensure both token keys are in sync
      storeTokens(stored.token, stored.user);
      setState({
        token: stored.token,
        user: stored.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } else if (import.meta.env.VITE_API_KEY) {
      // Dev mode: API key present — auto-authenticate with dev profile
      // The X-API-Key header in apiFetch will handle backend auth
      const devUser: AuthUser = {
        id: 'dev-admin',
        email: 'dev@riskcast.local',
        name: 'Dev Admin',
        role: 'admin',
        department: 'Development',
      };
      setState({
        token: 'api-key-auth',
        user: devUser,
        isAuthenticated: true,
        isLoading: false,
      });
    } else {
      setState({ token: null, user: null, isAuthenticated: false, isLoading: false });
    }
  }, []);

  // ─── Login (calls real V2 backend) ─────────────────────
  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      if (res.status === 401 || res.status === 403) {
        throw new Error('Invalid email or password.');
      }
      if (res.status === 429) {
        throw new Error(body?.detail || 'Too many attempts. Please try again later.');
      }
      throw new Error(body?.detail || 'Login failed. Please try again.');
    }

    const data = await res.json();
    const token = data.access_token;
    const user: AuthUser = {
      id: data.user_id,
      email: data.email,
      name: data.name || data.email.split('@')[0],
      role: (data.role || 'analyst') as AuthRole,
      department: 'Operations',
    };

    storeTokens(token, user);
    setState({ token, user, isAuthenticated: true, isLoading: false });
  }, []);

  // ─── Register (calls real V2 backend) ──────────────────
  const register = useCallback(async (name: string, email: string, password: string) => {
    if (!name.trim()) throw new Error('Name is required.');
    if (!email.trim()) throw new Error('Email is required.');
    if (password.length < 6) throw new Error('Password must be at least 6 characters.');

    // Generate a company slug from email domain
    const domain = email.split('@')[1]?.split('.')[0] || 'default';
    const slug = `${domain}-${Date.now().toString(36)}`;

    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_name: `${name.trim()}'s Company`,
        company_slug: slug,
        email: email.trim(),
        password,
        name: name.trim(),
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      if (res.status === 409) {
        throw new Error('An account with this email already exists.');
      }
      throw new Error(body?.detail || 'Registration failed. Please try again.');
    }

    const data = await res.json();
    const token = data.access_token;
    const user: AuthUser = {
      id: data.user_id,
      email: data.email,
      name: data.name || name.trim(),
      role: (data.role || 'analyst') as AuthRole,
      department: 'Operations',
      createdAt: new Date().toISOString(),
    };

    storeTokens(token, user);
    setState({ token, user, isAuthenticated: true, isLoading: false });
  }, []);

  // ─── Logout ────────────────────────────────────────────
  const logout = useCallback(() => {
    clearTokens();
    setState({ token: null, user: null, isAuthenticated: false, isLoading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an <AuthProvider>');
  }
  return ctx;
}

// ─── Protected Route ─────────────────────────────────────
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent" />
          <p className="text-sm text-muted-foreground font-mono">Authenticating...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
