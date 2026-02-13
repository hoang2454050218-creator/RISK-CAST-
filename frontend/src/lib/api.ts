/**
 * RISKCAST API Client
 *
 * Handles all communication with the RISKCAST backend.
 * When the backend is offline, falls back to mock data transparently.
 *
 * Uses a health-check gate: checks backend once on startup, and if offline,
 * skips ALL network requests (no ERR_CONNECTION_REFUSED in console).
 * Re-checks every 30s in case backend comes online later.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// ─── Mock disable flag ───────────────────────────────────
// Set VITE_DISABLE_MOCK=true in .env.local to always use real API
const MOCK_DISABLED = import.meta.env.VITE_DISABLE_MOCK === 'true';

// ─── Backend health state ────────────────────────────────
let _backendOnline: boolean | null = null; // null = not checked yet
let _lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 30_000; // Re-check every 30s

async function isBackendOnline(): Promise<boolean> {
  // If mock is disabled, always report backend as online (force real API calls)
  if (MOCK_DISABLED) return true;

  const now = Date.now();
  // Use cached result if checked recently
  if (_backendOnline !== null && now - _lastHealthCheck < HEALTH_CHECK_INTERVAL) {
    return _backendOnline;
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(`/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeout);
    _backendOnline = res.ok || res.status < 500;
  } catch {
    _backendOnline = false;
  }

  _lastHealthCheck = now;
  return _backendOnline;
}

// Run health check immediately on module load (non-blocking)
isBackendOnline();

// ─── Error class ─────────────────────────────────────────
export class ApiError extends Error {
  status: number;
  statusText: string;
  data?: unknown;

  constructor(status: number, statusText: string, data?: unknown) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

// ─── Core fetch wrapper ──────────────────────────────────
async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const cleanEndpoint = endpoint.replace(/\/+$/, '') || endpoint;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const token = localStorage.getItem('riskcast:auth-token');
  const apiKey = localStorage.getItem('riskcast:api-key') || import.meta.env.VITE_API_KEY || '';
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      // Response body is not JSON
    }
    throw new ApiError(response.status, response.statusText, data);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// ─── Mock fallback wrapper ───────────────────────────────
/**
 * Wraps an API call with a mock data fallback.
 *
 * KEY: Checks backend health FIRST. If backend is known to be offline,
 * returns mock data immediately WITHOUT making a network request.
 * This prevents ERR_CONNECTION_REFUSED errors flooding the console.
 */
export async function withMockFallback<T>(apiCall: () => Promise<T>, mockData: T): Promise<T> {
  // When mock is disabled, always call real API — errors propagate to caller
  if (MOCK_DISABLED) {
    return apiCall();
  }

  // Skip network call entirely if backend is known to be offline
  const online = await isBackendOnline();
  if (!online) {
    return mockData;
  }

  try {
    return await apiCall();
  } catch {
    // Any error → fall back to mock data silently
    _backendOnline = false; // Mark offline so subsequent calls skip network
    return mockData;
  }
}

// ============================================
// DECISION ENDPOINTS
// ============================================

import type {
  Decision,
  DecisionListResponse,
  DecisionAcknowledgeRequest,
  DecisionOverrideRequest,
  DecisionEscalateRequest,
} from '@/types/decision';

/**
 * Get list of decisions
 * Backend endpoint: GET /api/v1/decisions/active (list all active decisions)
 * Backend returns: { items: DecisionSummaryResponse[], pagination: PaginationMeta }
 * Frontend expects: { decisions: Decision[], total: number }
 */
export async function getDecisions(params?: {
  status?: string;
  customer_id?: string;
  page?: number;
  page_size?: number;
}): Promise<DecisionListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.customer_id) searchParams.set('customer_id', params.customer_id);
  if (params?.page_size) searchParams.set('limit', String(params.page_size));
  if (params?.page) searchParams.set('offset', String(((params.page || 1) - 1) * (params.page_size || 20)));

  const query = searchParams.toString();
  // Use /decisions/active for listing; backend has no GET /decisions root endpoint
  const endpoint = params?.customer_id
    ? `/decisions/customer/${params.customer_id}${query ? `?${query}` : ''}`
    : `/decisions/active${query ? `?${query}` : ''}`;

  // Backend returns { items, pagination } but frontend expects { decisions, total }
  const response = await apiFetch<{
    items?: unknown[];
    decisions?: unknown[];
    total?: number;
    pagination?: { total: number };
  }>(endpoint);

  return {
    decisions: (response.decisions || response.items || []) as DecisionListResponse['decisions'],
    total: response.total ?? response.pagination?.total ?? 0,
  };
}

/**
 * Get a single decision by ID
 */
export async function getDecision(decisionId: string): Promise<Decision> {
  return apiFetch<Decision>(`/decisions/${decisionId}`);
}

/**
 * Acknowledge a decision
 */
export async function acknowledgeDecision(request: DecisionAcknowledgeRequest): Promise<Decision> {
  return apiFetch<Decision>(`/decisions/${request.decision_id}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Override a decision
 */
export async function overrideDecision(request: DecisionOverrideRequest): Promise<Decision> {
  return apiFetch<Decision>(`/decisions/${request.decision_id}/override`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Escalate a decision
 */
export async function escalateDecision(request: DecisionEscalateRequest): Promise<Decision> {
  return apiFetch<Decision>(`/decisions/${request.decision_id}/escalate`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// ============================================
// SIGNAL ENDPOINTS
// ============================================

export interface Signal {
  signal_id: string;
  event_type: string;
  probability: number;
  confidence: number;
  created_at: string;
  source: string;
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
}

/**
 * Get list of signals
 * Backend endpoint: GET /api/v1/signals (no trailing slash)
 * Backend returns: { items: SignalResponse[], total: number }
 * Frontend expects: { signals: Signal[], total: number }
 */
export async function getSignals(params?: {
  event_type?: string;
  min_probability?: number;
  page?: number;
  page_size?: number;
}): Promise<SignalListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.event_type) searchParams.set('category', params.event_type);
  if (params?.min_probability) searchParams.set('min_probability', String(params.min_probability));
  if (params?.page) searchParams.set('page', String(params.page));
  if (params?.page_size) searchParams.set('page_size', String(params.page_size));

  const query = searchParams.toString();
  const endpoint = `/signals${query ? `?${query}` : ''}`;

  // Backend returns { items, total } but frontend expects { signals, total }
  const response = await apiFetch<{ items?: unknown[]; signals?: unknown[]; total: number }>(
    endpoint,
  );
  return {
    signals: (response.signals || response.items || []) as SignalListResponse['signals'],
    total: response.total,
  };
}

/**
 * Get a single signal by ID
 */
export async function getSignal(signalId: string): Promise<Signal> {
  return apiFetch<Signal>(`/signals/${signalId}`);
}

// ============================================
// CUSTOMER ENDPOINTS
// ============================================

export interface CustomerProfile {
  customer_id: string;
  company_name: string;
  contact_email: string;
  phone_number?: string;
  active_shipments: number;
  total_exposure_usd: number;
}

/**
 * Get customer profile
 */
export async function getCustomerProfile(customerId: string): Promise<CustomerProfile> {
  return apiFetch<CustomerProfile>(`/customers/${customerId}`);
}

// ============================================
// ESCALATION ENDPOINTS
// ============================================

export async function getEscalations(params?: {
  priority?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<{ escalations: unknown[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.priority) sp.set('priority', params.priority);
  if (params?.status) sp.set('status', params.status);
  if (params?.page) sp.set('page', String(params.page));
  if (params?.page_size) sp.set('page_size', String(params.page_size));
  const q = sp.toString();
  // Backend serves escalations under /human/ prefix
  return apiFetch(`/human/escalations${q ? `?${q}` : ''}`);
}

export async function getEscalation(id: string): Promise<unknown> {
  return apiFetch(`/human/escalations/${id}`);
}

export async function approveEscalation(id: string, notes?: string): Promise<unknown> {
  return apiFetch(`/human/escalations/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ resolution: 'approved', notes }),
  });
}

export async function rejectEscalation(id: string, reason: string): Promise<unknown> {
  return apiFetch(`/human/escalations/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ resolution: 'rejected', reason }),
  });
}

export async function assignEscalation(id: string, assignee: string): Promise<unknown> {
  return apiFetch(`/human/escalations/${id}/assign`, {
    method: 'POST',
    body: JSON.stringify({ assignee }),
  });
}

export async function commentEscalation(id: string, message: string): Promise<unknown> {
  return apiFetch(`/human/feedback`, {
    method: 'POST',
    body: JSON.stringify({ escalation_id: id, message }),
  });
}

// ============================================
// CUSTOMER LIST ENDPOINT
// ============================================

export async function getCustomers(params?: {
  page?: number;
  page_size?: number;
}): Promise<{ customers: CustomerProfile[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.page) sp.set('page', String(params.page));
  if (params?.page_size) sp.set('page_size', String(params.page_size));
  const q = sp.toString();
  return apiFetch(`/customers${q ? `?${q}` : ''}`);
}

// ============================================
// DASHBOARD / ANALYTICS ENDPOINTS
// ============================================

export async function getDashboardStats(): Promise<unknown> {
  return apiFetch('/dashboard/stats');
}

export async function getAnalyticsMetrics(params?: { period?: string }): Promise<unknown> {
  const sp = new URLSearchParams();
  if (params?.period) sp.set('period', params.period);
  const q = sp.toString();
  return apiFetch(`/analytics/metrics${q ? `?${q}` : ''}`);
}

// ============================================
// AUDIT TRAIL ENDPOINT
// ============================================

export async function getAuditEvents(params?: {
  actor_type?: string;
  event_type?: string;
  page?: number;
  page_size?: number;
}): Promise<{ events: unknown[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.actor_type) sp.set('actor_type', params.actor_type);
  if (params?.event_type) sp.set('event_type', params.event_type);
  if (params?.page) sp.set('page', String(params.page));
  if (params?.page_size) sp.set('page_size', String(params.page_size));
  const q = sp.toString();
  return apiFetch(`/audit${q ? `?${q}` : ''}`);
}

// ============================================
// REALITY ENGINE ENDPOINTS
// ============================================

export async function getChokepointHealth(): Promise<unknown> {
  return apiFetch('/reality/chokepoints');
}

export async function getFreightRates(): Promise<unknown> {
  return apiFetch('/reality/rates');
}

export async function getVesselTracking(): Promise<unknown> {
  return apiFetch('/reality/vessels');
}

// ============================================
// SIGNAL MUTATIONS
// ============================================

export async function dismissSignal(signalId: string, reason?: string): Promise<unknown> {
  return apiFetch(`/signals/${signalId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function generateDecisionFromSignal(signalId: string): Promise<unknown> {
  return apiFetch(`/signals/${signalId}/generate-decision`, { method: 'POST' });
}

// ============================================
// HEALTH CHECK
// ============================================

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
}

export async function getHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/health');
}
