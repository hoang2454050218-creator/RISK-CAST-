/**
 * Mock Data Engine — barrel export
 *
 * All mock data is cross-referenced via shared entity IDs.
 * Generators produce time-aware data relative to Date.now().
 */

// Legacy exports (used by existing hooks: useDecisions, useSignals, tests)
export { mockDecision, mockDecisions, mockSignals } from './legacy';

// Core
export { rng, getDailySeed, createSeededRandom } from './seed';
export { CHOKEPOINTS, CARRIERS, PORTS, ROUTES, EVENT_TYPES, ACTION_TYPES } from './constants';
export { CUSTOMERS, SHIPMENTS } from './entities';
export type { MockCustomer, MockShipment } from './entities';

// Generators
export { generateDashboardData } from './generators/dashboard';
export type { DashboardData } from './generators/dashboard';

export { generateCustomersList, generateCustomerDetail } from './generators/customers';
export type { CustomerListItem, CustomerDetail } from './generators/customers';

export { generateAnalyticsData } from './generators/analytics';
export type { AnalyticsData } from './generators/analytics';

export { generateAuditTrail } from './generators/audit';
export type { AuditEvent } from './generators/audit';

export { generateRealityData } from './generators/reality';
export type { RealityData } from './generators/reality';

export { generateEscalationDetail } from './generators/escalations';
export type { EscalationDetail } from './generators/escalations';
