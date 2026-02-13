/**
 * Customer data generator — linked to shipments and decisions.
 */

import { CUSTOMERS, SHIPMENTS, type MockCustomer } from '../entities';

export interface CustomerListItem {
  id: string;
  name: string;
  industry: string;
  contactName: string;
  contactEmail: string;
  region: string;
  tier: 'enterprise' | 'mid-market' | 'startup';
  activeShipments: number;
  totalExposure: number;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  lastActivity: string;
}

export interface CustomerDetail extends CustomerListItem {
  contactPhone: string;
  onboardedAt: string;
  shipments: Array<{
    id: string;
    carrier: string;
    vesselName: string;
    origin: string;
    destination: string;
    status: string;
    cargoValue: number;
    eta: string;
  }>;
  recentDecisions: Array<{
    id: string;
    title: string;
    severity: string;
    status: string;
    createdAt: string;
  }>;
}

function getRiskLevel(exposure: number): 'critical' | 'high' | 'medium' | 'low' {
  if (exposure > 2_000_000) return 'critical';
  if (exposure > 1_000_000) return 'high';
  if (exposure > 500_000) return 'medium';
  return 'low';
}

export function generateCustomersList(): CustomerListItem[] {
  return CUSTOMERS.map(c => ({
    id: c.id,
    name: c.name,
    industry: c.industry,
    contactName: c.contactName,
    contactEmail: c.contactEmail,
    region: c.region,
    tier: c.tier,
    activeShipments: c.activeShipments,
    totalExposure: c.totalExposure,
    riskLevel: getRiskLevel(c.totalExposure),
    lastActivity: new Date(Date.now() - Math.random() * 7 * 86400000).toISOString(),
  }));
}

export function generateCustomerDetail(customerId: string): CustomerDetail | null {
  const customer = CUSTOMERS.find(c => c.id === customerId);
  if (!customer) return null;

  const customerShipments = SHIPMENTS.filter(s => s.customerId === customerId);

  return {
    id: customer.id,
    name: customer.name,
    industry: customer.industry,
    contactName: customer.contactName,
    contactEmail: customer.contactEmail,
    contactPhone: customer.contactPhone,
    region: customer.region,
    tier: customer.tier,
    activeShipments: customer.activeShipments,
    totalExposure: customer.totalExposure,
    riskLevel: getRiskLevel(customer.totalExposure),
    lastActivity: new Date(Date.now() - Math.random() * 3 * 86400000).toISOString(),
    onboardedAt: customer.onboardedAt,
    shipments: customerShipments.map(s => ({
      id: s.id,
      carrier: s.carrier,
      vesselName: s.vesselName,
      origin: s.origin,
      destination: s.destination,
      status: s.status,
      cargoValue: s.cargoValue,
      eta: s.eta,
    })),
    recentDecisions: [
      { id: 'dec_001', title: 'Red Sea Reroute Advisory', severity: 'HIGH', status: 'PENDING', createdAt: new Date(Date.now() - 3600000).toISOString() },
      { id: 'dec_005', title: 'Insurance Premium Update', severity: 'MEDIUM', status: 'ACKNOWLEDGED', createdAt: new Date(Date.now() - 86400000).toISOString() },
    ],
  };
}
