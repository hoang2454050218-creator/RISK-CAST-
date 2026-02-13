/**
 * useV2Auth — Auto-manages V2 backend authentication.
 *
 * When V2 token is missing, auto-registers a V2 account
 * using the current V1 user info. Stores V2 token separately.
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

export function useV2Auth() {
  const [token, setToken] = useState<string | null>(localStorage.getItem(V2_TOKEN_KEY));
  const [user, setUser] = useState<V2User | null>(() => {
    const stored = localStorage.getItem(V2_USER_KEY);
    return stored ? JSON.parse(stored) : null;
  });
  const [isConnecting, setIsConnecting] = useState(false);

  const connect = useCallback(async () => {
    if (token) return true;
    setIsConnecting(true);

    try {
      // Try login first
      let res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'demo@riskcast.vn', password: 'riskcast2026' }),
      });

      if (res.status === 401) {
        // Register new account
        res = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_name: 'RiskCast Demo',
            company_slug: `demo-${Date.now()}`,
            email: 'demo@riskcast.vn',
            password: 'riskcast2026',
            name: 'Demo User',
            industry: 'logistics',
          }),
        });
      }

      if (!res.ok) {
        // Slug might exist, try with unique slug
        res = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            company_name: 'RiskCast Demo',
            company_slug: `demo-${Date.now()}`,
            email: `demo-${Date.now()}@riskcast.vn`,
            password: 'riskcast2026',
            name: 'Demo User',
            industry: 'logistics',
          }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        const v2Token = data.access_token;
        const v2User: V2User = {
          user_id: data.user_id,
          company_id: data.company_id,
          email: data.email,
          name: data.name,
          role: data.role,
        };

        localStorage.setItem(V2_TOKEN_KEY, v2Token);
        localStorage.setItem(V2_USER_KEY, JSON.stringify(v2User));
        setToken(v2Token);
        setUser(v2User);
        return true;
      }

      return false;
    } catch {
      return false;
    } finally {
      setIsConnecting(false);
    }
  }, [token]);

  // Auto-connect on mount if no token
  useEffect(() => {
    if (!token) {
      connect();
    }
  }, [token, connect]);

  return { token, user, isConnecting, connect, isAuthenticated: !!token };
}

/** Get stored V2 token (for use in api-v2.ts) */
export function getV2Token(): string | null {
  return localStorage.getItem(V2_TOKEN_KEY);
}
