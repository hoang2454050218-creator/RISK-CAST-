/**
 * Plan Context — provides current plan info, limits, features, and usage
 * throughout the application.
 *
 * Usage:
 *   const { plan, features, limits, usage, isFeatureEnabled } = usePlan();
 *   if (isFeatureEnabled('ai_chat')) { ... }
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';

// ─── Types ───────────────────────────────────────────────

export interface PlanLimits {
  max_shipments: number;
  max_customers: number;
  max_routes: number;
  max_team_members: number;
  max_alerts_per_day: number;
  max_chokepoints: number;
  api_rate_limit_per_minute: number;
  historical_data_days: number;
}

export interface PlanFeatures {
  dashboard: boolean;
  dashboard_readonly: boolean;
  signals_monitoring: boolean;
  red_sea_monitoring: boolean;
  weekly_digest: boolean;
  decision_engine: boolean;
  multi_channel_alerts: boolean;
  email_alerts: boolean;
  whatsapp_alerts: boolean;
  discord_alerts: boolean;
  analytics: boolean;
  api_access: boolean;
  scenario_analysis: boolean;
  exposure_mapping: boolean;
  custom_integrations: boolean;
  dedicated_support: boolean;
  sla_guarantee: boolean;
  on_premise: boolean;
  seven_question_format: boolean;
  human_review: boolean;
  audit_trail: boolean;
  morning_briefs: boolean;
  ai_chat: boolean;
}

export interface PlanUsage {
  shipments: number;
  customers: number;
  routes: number;
  team_members: number;
  signals_active: number;
}

export interface PlanInfo {
  plan_id: string;
  plan_name: string;
  display_name: string;
  price_monthly: number;
  price_annual_monthly: number;
  limits: PlanLimits;
  features: PlanFeatures;
  usage: PlanUsage;
  company_name: string;
  company_industry: string | null;
  trial_active: boolean;
  trial_ends_at: string | null;
}

interface PlanContextValue {
  plan: PlanInfo | null;
  isLoading: boolean;
  error: string | null;
  isFeatureEnabled: (feature: keyof PlanFeatures) => boolean;
  isWithinLimit: (resource: keyof PlanLimits, currentValue?: number) => boolean;
  getUsagePercent: (resource: 'shipments' | 'customers' | 'routes' | 'team_members') => number;
  refreshPlan: () => Promise<void>;
  upgradePlan: (planId: string) => Promise<boolean>;
}

// ─── Default plan (free tier fallback) ───────────────────

const DEFAULT_PLAN: PlanInfo = {
  plan_id: 'free',
  plan_name: 'Monitor',
  display_name: 'Monitor',
  price_monthly: 0,
  price_annual_monthly: 0,
  limits: {
    max_shipments: 5,
    max_customers: 2,
    max_routes: 1,
    max_team_members: 1,
    max_alerts_per_day: 3,
    max_chokepoints: 1,
    api_rate_limit_per_minute: 10,
    historical_data_days: 7,
  },
  features: {
    dashboard: true,
    dashboard_readonly: true,
    signals_monitoring: true,
    red_sea_monitoring: true,
    weekly_digest: true,
    decision_engine: false,
    multi_channel_alerts: false,
    email_alerts: false,
    whatsapp_alerts: false,
    discord_alerts: false,
    analytics: false,
    api_access: false,
    scenario_analysis: false,
    exposure_mapping: false,
    custom_integrations: false,
    dedicated_support: false,
    sla_guarantee: false,
    on_premise: false,
    seven_question_format: false,
    human_review: false,
    audit_trail: false,
    morning_briefs: false,
    ai_chat: false,
  },
  usage: { shipments: 0, customers: 0, routes: 0, team_members: 0, signals_active: 0 },
  company_name: '',
  company_industry: null,
  trial_active: false,
  trial_ends_at: null,
};

// ─── API helpers ─────────────────────────────────────────

const API_BASE = import.meta.env.VITE_V2_API_URL || '/api/v1';

async function fetchPlan(): Promise<PlanInfo> {
  const token = localStorage.getItem('riskcast:auth-token') || localStorage.getItem('riskcast:v2-token');
  const apiKey = localStorage.getItem('riskcast:api-key') || import.meta.env.VITE_API_KEY || '';

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
  };

  const res = await fetch(`${API_BASE}/plan/current`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch plan: ${res.status}`);
  return res.json();
}

async function requestUpgrade(planId: string): Promise<{ success: boolean; message: string }> {
  const token = localStorage.getItem('riskcast:auth-token') || localStorage.getItem('riskcast:v2-token');
  const apiKey = localStorage.getItem('riskcast:api-key') || import.meta.env.VITE_API_KEY || '';

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
  };

  const res = await fetch(`${API_BASE}/plan/upgrade`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ plan_id: planId }),
  });
  if (!res.ok) throw new Error(`Upgrade failed: ${res.status}`);
  return res.json();
}

// ─── Context ─────────────────────────────────────────────

const PlanContext = createContext<PlanContextValue | undefined>(undefined);

export function PlanProvider({ children }: { children: ReactNode }) {
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshPlan = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchPlan();
      setPlan(data);
    } catch (err) {
      console.warn('[PlanContext] Failed to fetch plan, using default:', err);
      setPlan(DEFAULT_PLAN);
      setError(err instanceof Error ? err.message : 'Failed to load plan');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Small delay to allow auth to initialize first
    const timer = setTimeout(refreshPlan, 500);
    return () => clearTimeout(timer);
  }, [refreshPlan]);

  const isFeatureEnabled = useCallback(
    (feature: keyof PlanFeatures): boolean => {
      if (!plan) return false;
      return plan.features[feature] ?? false;
    },
    [plan],
  );

  const isWithinLimit = useCallback(
    (resource: keyof PlanLimits, currentValue?: number): boolean => {
      if (!plan) return false;
      const limit = plan.limits[resource];
      if (limit >= 99999) return true; // Unlimited
      if (currentValue !== undefined) return currentValue < limit;
      // Auto-check usage
      const usageMap: Partial<Record<keyof PlanLimits, keyof PlanUsage>> = {
        max_shipments: 'shipments',
        max_customers: 'customers',
        max_routes: 'routes',
        max_team_members: 'team_members',
      };
      const usageKey = usageMap[resource];
      if (usageKey) return plan.usage[usageKey] < limit;
      return true;
    },
    [plan],
  );

  const getUsagePercent = useCallback(
    (resource: 'shipments' | 'customers' | 'routes' | 'team_members'): number => {
      if (!plan) return 0;
      const limitMap: Record<string, keyof PlanLimits> = {
        shipments: 'max_shipments',
        customers: 'max_customers',
        routes: 'max_routes',
        team_members: 'max_team_members',
      };
      const limit = plan.limits[limitMap[resource]];
      if (limit >= 99999) return 0; // Unlimited = 0%
      const usage = plan.usage[resource];
      return Math.min(Math.round((usage / limit) * 100), 100);
    },
    [plan],
  );

  const upgradePlan = useCallback(
    async (planId: string): Promise<boolean> => {
      try {
        const result = await requestUpgrade(planId);
        if (result.success) {
          await refreshPlan(); // Refresh to get new plan data
          return true;
        }
        return false;
      } catch {
        return false;
      }
    },
    [refreshPlan],
  );

  return (
    <PlanContext.Provider
      value={{
        plan,
        isLoading,
        error,
        isFeatureEnabled,
        isWithinLimit,
        getUsagePercent,
        refreshPlan,
        upgradePlan,
      }}
    >
      {children}
    </PlanContext.Provider>
  );
}

export function usePlan(): PlanContextValue {
  const ctx = useContext(PlanContext);
  if (!ctx) {
    throw new Error('usePlan must be used within a <PlanProvider>');
  }
  return ctx;
}
