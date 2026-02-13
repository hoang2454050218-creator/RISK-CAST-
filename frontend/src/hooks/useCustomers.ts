/**
 * Customer hooks — real data from backend API with mock fallback.
 *
 * Includes:
 * - List/detail queries with React Query
 * - Create/update/delete mutations
 * - Automatic cache invalidation
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  v2Customers,
  v2Shipments,
  v2Intelligence,
  type CustomerFullResponse,
  type CustomerCreateRequest,
  type CustomerUpdateRequest,
  type CustomerListResponse,
  type ShipmentCreateRequest,
  type CompanyAnalysis,
} from '@/lib/api-v2';
import { withMockFallback } from '@/lib/api';
import type { CustomerListItem, CustomerDetail } from '@/lib/mock-data';

// ── Mock customer data for offline fallback ─────────────────

const mockCustomersListResponse: CustomerListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
};

const mockCustomerFull: CustomerFullResponse = {
  customer_id: 'mock_001',
  company_name: 'Demo Company',
  industry: 'General',
  primary_phone: '+84000000000',
  secondary_phone: null,
  email: 'demo@example.com',
  risk_tolerance: 'BALANCED',
  notification_enabled: true,
  whatsapp_enabled: true,
  email_enabled: true,
  primary_routes: [],
  relevant_chokepoints: [],
  is_active: true,
  tier: 'standard',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// ── Mock data for legacy format (CustomerListItem) ──────────

const mockLegacyCustomers: CustomerListItem[] = [
  {
    id: 'cust_001',
    name: 'ACME Logistics',
    industry: 'Logistics',
    contactName: 'John Smith',
    contactEmail: 'ops@acmelogistics.com',
    region: 'Asia Pacific',
    tier: 'enterprise',
    activeShipments: 12,
    totalExposure: 2_450_000,
    riskLevel: 'high',
    lastActivity: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    id: 'cust_002',
    name: 'Global Trade Inc',
    industry: 'Trading',
    contactName: 'Sarah Lee',
    contactEmail: 'logistics@globaltrade.com',
    region: 'Europe',
    tier: 'enterprise',
    activeShipments: 8,
    totalExposure: 1_800_000,
    riskLevel: 'medium',
    lastActivity: new Date(Date.now() - 5 * 86400000).toISOString(),
  },
  {
    id: 'cust_003',
    name: 'VinaTech Export',
    industry: 'Manufacturing',
    contactName: 'Nguyen Van A',
    contactEmail: 'shipping@vinatech.vn',
    region: 'Asia Pacific',
    tier: 'mid-market',
    activeShipments: 5,
    totalExposure: 750_000,
    riskLevel: 'medium',
    lastActivity: new Date(Date.now() - 1 * 86400000).toISOString(),
  },
];

// ── Query Keys ──────────────────────────────────────────────

export const customerKeys = {
  all: ['customers'] as const,
  lists: () => [...customerKeys.all, 'list'] as const,
  details: () => [...customerKeys.all, 'detail'] as const,
  detail: (id: string) => [...customerKeys.details(), id] as const,
  analysis: (id: string) => [...customerKeys.all, 'analysis', id] as const,
};

// ── Helper: Convert backend response → legacy CustomerListItem ──

function toCustomerListItem(c: CustomerFullResponse): CustomerListItem {
  const riskMap: Record<string, CustomerListItem['riskLevel']> = {
    LOW: 'low',
    BALANCED: 'medium',
    HIGH: 'high',
  };
  return {
    id: c.customer_id,
    name: c.company_name,
    industry: c.industry || 'General',
    contactName: c.company_name,
    contactEmail: c.email || '',
    region: c.primary_routes[0] || 'Global',
    tier: (c.tier as CustomerListItem['tier']) || 'startup',
    activeShipments: 0,
    totalExposure: 0,
    riskLevel: riskMap[c.risk_tolerance] || 'medium',
    lastActivity: c.updated_at,
  };
}

// ── Queries ─────────────────────────────────────────────────

export function useCustomersList() {
  return useQuery<CustomerListItem[]>({
    queryKey: customerKeys.lists(),
    queryFn: async () => {
      try {
        const response = await v2Customers.list({ page: 1, page_size: 100 });
        // Handle both array format and paginated format
        if (Array.isArray(response)) {
          return (response as unknown as CustomerFullResponse[]).map(toCustomerListItem);
        }
        if (response.items && Array.isArray(response.items)) {
          return response.items.map(toCustomerListItem);
        }
        return mockLegacyCustomers;
      } catch {
        return mockLegacyCustomers;
      }
    },
    staleTime: 30_000,
    retry: 2,
  });
}

export function useCustomer(id: string | undefined) {
  return useQuery({
    queryKey: customerKeys.detail(id ?? ''),
    queryFn: async () => {
      if (!id) return null;
      try {
        const customer = await v2Customers.get(id);
        return customer;
      } catch {
        // Fallback to legacy mock
        return null;
      }
    },
    enabled: !!id,
    staleTime: 30_000,
    retry: 2,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useCreateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CustomerCreateRequest): Promise<CustomerFullResponse> => {
      try {
        return await v2Customers.create(data);
      } catch {
        // Mock fallback when backend is unavailable — simulate success
        // and store in localStorage for persistence
        const mockResponse: CustomerFullResponse = {
          customer_id: data.customer_id,
          company_name: data.company_name,
          industry: data.industry || null,
          primary_phone: data.primary_phone,
          secondary_phone: data.secondary_phone || null,
          email: data.email || null,
          risk_tolerance: data.risk_tolerance || 'BALANCED',
          notification_enabled: data.notification_enabled ?? true,
          whatsapp_enabled: data.whatsapp_enabled ?? true,
          email_enabled: data.email_enabled ?? true,
          primary_routes: data.primary_routes || [],
          relevant_chokepoints: [],
          is_active: true,
          tier: data.tier || 'standard',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        // Also store extended data locally for full system context
        if (data.cargo_types || data.company_description || data.alert_preferences) {
          try {
            localStorage.setItem(`riskcast:customer-ext:${data.customer_id}`, JSON.stringify({
              cargo_types: data.cargo_types,
              company_description: data.company_description,
              language: data.language,
              timezone: data.timezone,
              max_reroute_premium_pct: data.max_reroute_premium_pct,
              alert_preferences: data.alert_preferences,
            }));
          } catch { /* noop */ }
        }
        // Persist locally
        try {
          const existing = JSON.parse(localStorage.getItem('riskcast:customers') || '[]');
          existing.push(mockResponse);
          localStorage.setItem('riskcast:customers', JSON.stringify(existing));
        } catch { /* noop */ }
        return mockResponse;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CustomerUpdateRequest }) =>
      v2Customers.update(id, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(variables.id) });
    },
  });
}

export function useDeleteCustomer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => v2Customers.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// ── Shipment Mutations ──────────────────────────────────────

export function useCreateShipment(customerId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ShipmentCreateRequest) => v2Shipments.create(customerId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: customerKeys.detail(customerId) });
      queryClient.invalidateQueries({ queryKey: customerKeys.lists() });
    },
  });
}

// ── LLM Intelligence ────────────────────────────────────────

export function useCompanyAnalysis(customerId: string | undefined) {
  return useQuery<CompanyAnalysis | null>({
    queryKey: customerKeys.analysis(customerId ?? ''),
    queryFn: async () => {
      if (!customerId) return null;
      try {
        return await v2Intelligence.getCompanyInsights(customerId);
      } catch {
        return null;
      }
    },
    enabled: !!customerId,
    staleTime: 5 * 60_000, // 5 min cache
    retry: 1,
  });
}

export function useAnalyzeCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (customerId: string) => v2Intelligence.analyzeCompany(customerId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: customerKeys.analysis(data.company_id) });
    },
  });
}
