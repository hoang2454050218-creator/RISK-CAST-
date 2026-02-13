/**
 * RiskCast V2 API Client
 *
 * Points to the V2 backend (port 8002).
 * Handles auth tokens, SSE streaming, and typed responses.
 */

const V2_BASE = import.meta.env.VITE_V2_API_URL || '/api/v1';
const V2_TOKEN_KEY = 'riskcast:v2-token';

function getToken(): string | null {
  return localStorage.getItem(V2_TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken() || localStorage.getItem('riskcast:auth-token');
  const apiKey = localStorage.getItem('riskcast:api-key') || import.meta.env.VITE_API_KEY || '';
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  // Strip trailing slashes before query string to prevent 404s
  // e.g. "/signals/?foo=bar" → "/signals?foo=bar", "/customers/" → "/customers"
  const cleanPath = path.replace(/\/+(\?|$)/, '$1');

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000); // 15s timeout

  try {
    const res = await fetch(`${V2_BASE}${cleanPath}`, {
      ...init,
      headers: { ...authHeaders(), ...init?.headers },
      signal: init?.signal || controller.signal,
    });
    clearTimeout(timeout);

    if (!res.ok) {
      // Auto-clear tokens on 401 — forces re-login
      if (res.status === 401) {
        localStorage.removeItem(V2_TOKEN_KEY);
        localStorage.removeItem('riskcast:auth-token');
        localStorage.removeItem('riskcast:auth-user');
      }
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiV2Error(res.status, body.detail || 'Request failed');
    }
    return res.json();
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof ApiV2Error) throw err;
    throw new ApiV2Error(0, err instanceof Error ? err.message : 'Network error');
  }
}

export class ApiV2Error extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiV2Error';
  }
}

// ── Auth ─────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  company_id: string;
  email: string;
  role: string;
  name: string;
}

export const v2Auth = {
  register: (data: {
    company_name: string;
    company_slug: string;
    email: string;
    password: string;
    name: string;
    industry?: string;
  }) => apiFetch<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

  login: (email: string, password: string) =>
    apiFetch<TokenResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
};

// ── Signals ──────────────────────────────────────────────────

export interface Signal {
  id: string;
  company_id: string;
  source: string;
  signal_type: string;
  entity_type: string | null;
  entity_id: string | null;
  confidence: number;
  severity_score: number | null;
  evidence: Record<string, unknown>;
  context: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
}

export const v2Signals = {
  list: (params?: { active_only?: boolean; min_severity?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.active_only !== undefined) qs.set('active_only', String(params.active_only));
    if (params?.min_severity) qs.set('min_severity', String(params.min_severity));
    if (params?.limit) qs.set('limit', String(params.limit));
    return apiFetch<SignalListResponse>(`/signals/?${qs}`);
  },
  summary: () => apiFetch<{ by_type: Array<{ signal_type: string; count: number; avg_severity: number }>; total_active: number }>('/signals/summary'),
  scan: () => apiFetch<{ status: string; signals_upserted: number }>('/signals/scan', { method: 'POST' }),
};

// ── Chat ─────────────────────────────────────────────────────

export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  context_used: Record<string, unknown>;
  created_at: string;
}

export interface Suggestion {
  id: string;
  type: string;
  text: string;
}

export const v2Chat = {
  sessions: () => apiFetch<{ sessions: ChatSession[] }>('/chat/sessions'),
  messages: (sessionId: string) => apiFetch<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),

  /** Returns a ReadableStream for SSE — use with useChat hook */
  sendMessage: async (message: string, sessionId?: string) => {
    const res = await fetch(`${V2_BASE}/chat/message`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new ApiV2Error(res.status, 'Chat request failed');
    return res;
  },
};

// ── Briefs ───────────────────────────────────────────────────

export interface MorningBrief {
  id: string;
  brief_date: string;
  content: string;
  priority_items: Array<{
    signal_id: string;
    signal_type: string;
    severity_score: number;
    confidence: number;
    summary: string;
  }>;
}

export const v2Briefs = {
  today: () => apiFetch<MorningBrief>('/briefs/today'),
  byDate: (date: string) => apiFetch<MorningBrief>(`/briefs/${date}`),
  markRead: (briefId: string) => apiFetch<{ status: string }>(`/briefs/${briefId}/read`, { method: 'POST' }),
};

// ── Feedback ─────────────────────────────────────────────────

export const v2Feedback = {
  submit: (suggestionId: string, data: { decision: string; reason_code?: string; reason_text?: string }) =>
    apiFetch<{ status: string }>(`/feedback/suggestions/${suggestionId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  outcome: (suggestionId: string, outcome: string) =>
    apiFetch<{ status: string }>(`/feedback/suggestions/${suggestionId}/outcome`, {
      method: 'POST',
      body: JSON.stringify({ outcome }),
    }),
  stats: () => apiFetch<{ total: number; by_decision: Record<string, number>; acceptance_rate: number }>('/feedback/stats'),
};

// ── Dashboard ────────────────────────────────────────────────

export interface DataFreshness {
  last_signal_at: string | null;
  last_order_at: string | null;
  last_payment_at: string | null;
  staleness_level: 'fresh' | 'stale' | 'outdated' | 'no_data';
}

export interface DashboardSummary {
  period: string;
  generated_at: string;
  data_freshness: DataFreshness;
  total_orders: number;
  active_signals: number;
  critical_signals: number;
  orders_at_risk: number;
  total_revenue: number;
  total_customers: number;
  signal_trend: Array<{ date: string; count: number }>;
  order_trend: Array<{ date: string; count: number }>;
  risk_trend: Array<{ date: string; avg_risk_score: number; signal_count: number }>;
  pending_decisions: number;
  top_risks: Array<{
    signal_id: string;
    signal_type: string;
    severity_score: number;
    entity_type: string | null;
    entity_id: string | null;
    summary: string;
    // Business decision context (optional — populated when available)
    exposure_usd?: number;
    action_cost_usd?: number;
    inaction_cost_usd?: number;
    recommended_action?: string;
    shipments_affected?: number;
    affected_route?: string;
    deadline?: string;
    confidence?: number;
  }>;
  recent_actions: Array<{
    action_type: string;
    description: string;
    timestamp: string;
    user_name: string | null;
  }>;
  data_completeness: number;
  known_gaps: string[];
  message: string | null;
}

export const v2Dashboard = {
  summary: (periodDays = 7) =>
    apiFetch<DashboardSummary>(`/dashboard/summary?period_days=${periodDays}`),
};

// ── Analytics ────────────────────────────────────────────────

export interface AnalyticsTimeSeries {
  period: string;
  generated_at: string;
  data_sufficiency: string;
  data_points: number;
  message: string | null;
  series: Array<{ date: string; value: number; count: number }>;
}

export interface AnalyticsCategories {
  period: string;
  generated_at: string;
  data_sufficiency: string;
  data_points: number;
  categories: Array<{
    category: string;
    count: number;
    avg_severity: number;
    max_severity: number;
    pct_of_total: number;
  }>;
}

export interface AnalyticsRoutes {
  period: string;
  generated_at: string;
  data_sufficiency: string;
  data_points: number;
  routes: Array<{
    route_id: string;
    route_name: string;
    origin: string;
    destination: string;
    signal_count: number;
    avg_severity: number;
    incident_count: number;
  }>;
}

export const v2Analytics = {
  riskOverTime: (days = 30) =>
    apiFetch<AnalyticsTimeSeries>(`/analytics/risk-over-time?days=${days}`),
  riskByCategory: () =>
    apiFetch<AnalyticsCategories>('/analytics/risk-by-category'),
  riskByRoute: () =>
    apiFetch<AnalyticsRoutes>('/analytics/risk-by-route'),
  topRiskFactors: () =>
    apiFetch<AnalyticsCategories>('/analytics/top-risk-factors'),
};

// ── Audit Trail ──────────────────────────────────────────────

export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  status: string;
  resource_type: string | null;
  resource_id: string | null;
  user_id: string | null;
  api_key_prefix: string | null;
  ip_address: string | null;
  request_method: string | null;
  request_path: string | null;
  details: Record<string, unknown> | null;
}

export interface AuditTrailResponse {
  events: AuditEvent[];
  total: number;
  has_more: boolean;
}

export const v2Audit = {
  list: (params?: { action?: string; offset?: number; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.action) qs.set('action', params.action);
    if (params?.offset) qs.set('offset', String(params.offset));
    if (params?.limit) qs.set('limit', String(params.limit));
    return apiFetch<AuditTrailResponse>(`/audit-trail/?${qs}`);
  },
  integrity: () =>
    apiFetch<{ status: string; total_entries: number; chain_intact: boolean }>('/audit-trail/integrity'),
};

// ── Customers ────────────────────────────────────────────────

export interface CustomerResponse {
  id: string;
  company_id: string;
  name: string;
  code: string | null;
  tier: string;
  contact_email: string | null;
  contact_phone: string | null;
  payment_terms: number;
  created_at: string;
  updated_at: string;
}

export interface CustomerCreateRequest {
  customer_id: string;
  company_name: string;
  industry?: string;
  primary_phone: string;
  secondary_phone?: string;
  email?: string;
  risk_tolerance?: 'LOW' | 'BALANCED' | 'HIGH';
  primary_routes?: string[];
  tier?: string;
  // Extended fields for full system capability
  cargo_types?: string[];
  company_description?: string;
  language?: string;
  timezone?: string;
  max_reroute_premium_pct?: number;
  notification_enabled?: boolean;
  whatsapp_enabled?: boolean;
  email_enabled?: boolean;
  sms_enabled?: boolean;
  alert_preferences?: {
    min_probability?: number;
    min_exposure_usd?: number;
    quiet_hours_start?: string;
    quiet_hours_end?: string;
    max_alerts_per_day?: number;
    include_inaction_cost?: boolean;
    include_confidence?: boolean;
  };
}

export interface CustomerUpdateRequest {
  company_name?: string;
  industry?: string;
  primary_phone?: string;
  secondary_phone?: string;
  email?: string;
  risk_tolerance?: 'LOW' | 'BALANCED' | 'HIGH';
  notification_enabled?: boolean;
  whatsapp_enabled?: boolean;
  email_enabled?: boolean;
  primary_routes?: string[];
  tier?: string;
}

export interface CustomerFullResponse {
  customer_id: string;
  company_name: string;
  industry: string | null;
  primary_phone: string;
  secondary_phone: string | null;
  email: string | null;
  risk_tolerance: string;
  notification_enabled: boolean;
  whatsapp_enabled: boolean;
  email_enabled: boolean;
  primary_routes: string[];
  relevant_chokepoints: string[];
  is_active: boolean;
  tier: string;
  created_at: string;
  updated_at: string;
}

export interface CustomerListResponse {
  items: CustomerFullResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface ShipmentCreateRequest {
  shipment_id: string;
  origin_port: string;
  destination_port: string;
  cargo_value_usd: number;
  cargo_description?: string;
  container_count?: number;
  container_type?: string;
  carrier_code?: string;
  booking_reference?: string;
  vessel_name?: string;
  etd?: string;
  eta?: string;
}

export const v2Customers = {
  list: (params?: { offset?: number; limit?: number; page?: number; page_size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set('page', String(params.page));
    if (params?.page_size) qs.set('page_size', String(params.page_size));
    if (params?.offset) qs.set('offset', String(params.offset));
    if (params?.limit) qs.set('limit', String(params.limit));
    return apiFetch<CustomerListResponse>(`/customers/?${qs}`);
  },
  get: (id: string) => apiFetch<CustomerFullResponse>(`/customers/${id}`),
  create: (data: CustomerCreateRequest) =>
    apiFetch<CustomerFullResponse>('/customers/', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: CustomerUpdateRequest) =>
    apiFetch<CustomerFullResponse>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/customers/${id}`, { method: 'DELETE' }),
  getByChokepoint: (chokepoint: string) =>
    apiFetch<CustomerFullResponse[]>(`/customers/chokepoint/${chokepoint}`),
};

// ── Shipments ────────────────────────────────────────────────

export const v2Shipments = {
  listForCustomer: (customerId: string) =>
    apiFetch<unknown[]>(`/customers/${customerId}/shipments`),
  create: (customerId: string, data: ShipmentCreateRequest) =>
    apiFetch<unknown>(`/customers/${customerId}/shipments`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  delete: (customerId: string, shipmentId: string) =>
    apiFetch<void>(`/customers/${customerId}/shipments/${shipmentId}`, { method: 'DELETE' }),
};

// ── Company Context (LLM-enhanced) ──────────────────────────

export interface CompanyAnalysis {
  company_id: string;
  analysis: string;
  risk_summary: string;
  key_exposures: string[];
  recommendations: string[];
  confidence: number;
  generated_at: string;
}

export const v2Intelligence = {
  analyzeCompany: (customerId: string) =>
    apiFetch<CompanyAnalysis>(`/intelligence/analyze/${customerId}`, { method: 'POST' }),
  getCompanyInsights: (customerId: string) =>
    apiFetch<CompanyAnalysis>(`/intelligence/insights/${customerId}`),
  analyzeSignal: (signalId: string) =>
    apiFetch<{ analysis: string; affected_customers: string[]; severity: string }>(`/intelligence/analyze-signal/${signalId}`, { method: 'POST' }),
};

// ── SSE Helper ───────────────────────────────────────────────

export function createEventSource(): EventSource {
  const token = getToken();
  return new EventSource(`/api/v1/events/stream?token=${token}`);
}
