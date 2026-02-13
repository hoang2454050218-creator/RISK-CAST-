/**
 * useV2Auth — Manages V2 backend authentication.
 *
 * Checks for existing valid token → uses it.
 * If expired/missing → user must authenticate via login page.
 * NO auto-registration. NO hardcoded credentials.
 */

import { useState, useEffect, useCallback } from 'react';

const V2_TOKEN_KEY = 'riskcast:v2-token';
const V2_USER_KEY = 'riskcast:v2-user';

interface V2User {
  user_id: string;
  company_id: string;
  email: string;
  name: string;
  role: string;
}

/** Check if a JWT token is expired */
function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return false; // No expiry = treat as valid
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export function useV2Auth() {
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem(V2_TOKEN_KEY);
    // Validate stored token on init — clear if expired
    if (stored && isTokenExpired(stored)) {
      localStorage.removeItem(V2_TOKEN_KEY);
      localStorage.removeItem(V2_USER_KEY);
      return null;
    }
    return stored;
  });

  const [user, setUser] = useState<V2User | null>(() => {
    try {
      const stored = localStorage.getItem(V2_USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [isConnecting] = useState(false);

  /** Store tokens after successful auth from login page */
  const setAuth = useCallback((newToken: string, newUser: V2User) => {
    localStorage.setItem(V2_TOKEN_KEY, newToken);
    localStorage.setItem(V2_USER_KEY, JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  }, []);

  /** Clear auth state */
  const clearAuth = useCallback(() => {
    localStorage.removeItem(V2_TOKEN_KEY);
    localStorage.removeItem(V2_USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  // Validate token on mount — if expired, clear
  useEffect(() => {
    if (token && isTokenExpired(token)) {
      clearAuth();
    }
  }, [token, clearAuth]);

  return {
    token,
    user,
    isConnecting,
    setAuth,
    clearAuth,
    isAuthenticated: !!token && !isTokenExpired(token),
  };
}

/** Get stored V2 token (for use in api-v2.ts) */
export function getV2Token(): string | null {
  const token = localStorage.getItem(V2_TOKEN_KEY);
  if (token && isTokenExpired(token)) {
    localStorage.removeItem(V2_TOKEN_KEY);
    return null;
  }
  return token;
}
