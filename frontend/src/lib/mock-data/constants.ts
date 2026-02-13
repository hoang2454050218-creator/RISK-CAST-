/**
 * Industry-accurate constants for mock data generation.
 * Based on real logistics industry data.
 */

export const CHOKEPOINTS = [
  { id: 'RED_SEA', name: 'Red Sea / Bab el-Mandeb', region: 'Middle East', riskLevel: 'HIGH' as const },
  { id: 'SUEZ', name: 'Suez Canal', region: 'Egypt', riskLevel: 'HIGH' as const },
  { id: 'MALACCA', name: 'Strait of Malacca', region: 'Southeast Asia', riskLevel: 'MEDIUM' as const },
  { id: 'PANAMA', name: 'Panama Canal', region: 'Central America', riskLevel: 'MEDIUM' as const },
  { id: 'STRAIT_OF_HORMUZ', name: 'Strait of Hormuz', region: 'Persian Gulf', riskLevel: 'WATCH' as const },
] as const;

export const CARRIERS = [
  'MSC', 'Maersk', 'CMA CGM', 'COSCO', 'Hapag-Lloyd',
  'ONE', 'Evergreen', 'Yang Ming', 'HMM', 'ZIM',
] as const;

export const PORTS = [
  { code: 'CNSHA', name: 'Shanghai', country: 'China' },
  { code: 'SGSIN', name: 'Singapore', country: 'Singapore' },
  { code: 'NLRTM', name: 'Rotterdam', country: 'Netherlands' },
  { code: 'DEHAM', name: 'Hamburg', country: 'Germany' },
  { code: 'GBFXT', name: 'Felixstowe', country: 'United Kingdom' },
  { code: 'AEJEA', name: 'Jebel Ali', country: 'UAE' },
  { code: 'USNYC', name: 'New York/New Jersey', country: 'USA' },
  { code: 'USCHS', name: 'Charleston', country: 'USA' },
  { code: 'VNHPH', name: 'Hai Phong', country: 'Vietnam' },
  { code: 'KRPUS', name: 'Busan', country: 'South Korea' },
] as const;

export const ROUTES = [
  { name: 'Asia-Europe', origin: 'CNSHA', destination: 'NLRTM', chokepoints: ['RED_SEA', 'SUEZ'] },
  { name: 'Asia-Mediterranean', origin: 'CNSHA', destination: 'DEHAM', chokepoints: ['RED_SEA', 'SUEZ'] },
  { name: 'Asia-US East Coast', origin: 'CNSHA', destination: 'USNYC', chokepoints: ['SUEZ', 'PANAMA'] },
  { name: 'SE Asia-Europe', origin: 'SGSIN', destination: 'GBFXT', chokepoints: ['MALACCA', 'RED_SEA', 'SUEZ'] },
  { name: 'Vietnam-Europe', origin: 'VNHPH', destination: 'DEHAM', chokepoints: ['MALACCA', 'RED_SEA'] },
  { name: 'Middle East-Europe', origin: 'AEJEA', destination: 'NLRTM', chokepoints: ['RED_SEA', 'SUEZ'] },
  { name: 'Korea-US East Coast', origin: 'KRPUS', destination: 'USCHS', chokepoints: ['PANAMA'] },
] as const;

export const EVENT_TYPES = [
  'ROUTE_DISRUPTION',
  'PORT_CONGESTION',
  'WEATHER_EVENT',
  'GEOPOLITICAL',
  'RATE_SPIKE',
  'CARRIER_ISSUE',
  'CUSTOMS_DELAY',
] as const;

export const ACTION_TYPES = ['REROUTE', 'DELAY', 'INSURE', 'MONITOR', 'DO_NOTHING'] as const;

export const URGENCY_LEVELS = ['IMMEDIATE', 'URGENT', 'SOON', 'WATCH'] as const;
export const SEVERITY_LEVELS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const;

/** Red Sea reroute parameters */
export const RED_SEA_PARAMS = {
  rerouteDelayDays: [7, 14] as [number, number],
  rerouteCostPerTeu: 2500,
  holdingCostPerDayPct: 0.001,
};
