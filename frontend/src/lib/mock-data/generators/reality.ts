/**
 * Reality Engine data generator — chokepoints, rates, vessel alerts.
 */

import { rng } from '../seed';
import { CHOKEPOINTS, CARRIERS } from '../constants';
import { SHIPMENTS } from '../entities';

export interface RealityData {
  chokepoints: Array<{
    id: string;
    name: string;
    region: string;
    status: 'critical' | 'degraded' | 'operational';
    transitDelayDays: number;
    vesselCount: number;
    lastIncident: string;
    trend: 'worsening' | 'stable' | 'improving';
  }>;
  rates: Array<{
    route: string;
    currentRate: number;
    previousRate: number;
    change: number;
    carrier: string;
    lastUpdated: string;
  }>;
  vesselAlerts: Array<{
    id: string;
    vesselName: string;
    alertType: 'diversion' | 'delay' | 'speed_change' | 'port_congestion';
    description: string;
    location: string;
    timestamp: string;
    severity: 'high' | 'medium' | 'low';
  }>;
  lastUpdated: string;
}

export function generateRealityData(): RealityData {
  const now = Date.now();

  const chokepoints = CHOKEPOINTS.map(cp => ({
    id: cp.id,
    name: cp.name,
    region: cp.region,
    status: cp.riskLevel === 'HIGH' ? 'critical' as const : cp.riskLevel === 'MEDIUM' ? 'degraded' as const : 'operational' as const,
    transitDelayDays: cp.riskLevel === 'HIGH' ? rng.int(7, 14) : cp.riskLevel === 'MEDIUM' ? rng.int(1, 5) : 0,
    vesselCount: rng.int(12, 85),
    lastIncident: new Date(now - rng.int(1, 72) * 3600000).toISOString(),
    trend: rng.pick(['worsening', 'stable', 'improving'] as const),
  }));

  const routes = ['Asia-Europe', 'Asia-US East', 'Intra-Asia', 'Asia-Mediterranean', 'Trans-Pacific'];
  const rates = routes.map(route => {
    const current = rng.int(1800, 4500);
    const previous = current + rng.int(-800, 300);
    return {
      route,
      currentRate: current,
      previousRate: previous,
      change: ((current - previous) / previous) * 100,
      carrier: rng.pick([...CARRIERS]),
      lastUpdated: new Date(now - rng.int(1, 12) * 3600000).toISOString(),
    };
  });

  const alertTemplates = SHIPMENTS.slice(0, 5).map((s, i) => ({
    id: `alert_${String(i + 1).padStart(3, '0')}`,
    vesselName: s.vesselName,
    alertType: rng.pick(['diversion', 'delay', 'speed_change', 'port_congestion'] as const),
    description: rng.pick([
      'Vessel diverted to Cape of Good Hope route',
      'Delayed at port due to congestion',
      'Speed reduced to 12 knots — weather advisory',
      'Port congestion — expected 48h additional wait',
    ]),
    location: rng.pick(['Red Sea', 'Gulf of Aden', 'Suez Canal', 'Singapore Strait', 'Malacca Strait']),
    timestamp: new Date(now - rng.int(1, 24) * 3600000).toISOString(),
    severity: rng.pick(['high', 'medium', 'low'] as const),
  }));

  return {
    chokepoints,
    rates,
    vesselAlerts: alertTemplates,
    lastUpdated: new Date(now - rng.int(1, 5) * 60000).toISOString(),
  };
}
