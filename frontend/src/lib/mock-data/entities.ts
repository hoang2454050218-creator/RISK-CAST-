/**
 * Base entities — cross-referenced across all generators.
 * Same shipment ID appears in signals, decisions, and customer views.
 */

import { rng } from './seed';
import { CARRIERS, PORTS, ROUTES } from './constants';

// ─── Customers ───────────────────────────────────────────

export interface MockCustomer {
  id: string;
  name: string;
  industry: string;
  contactName: string;
  contactEmail: string;
  contactPhone: string;
  region: string;
  tier: 'enterprise' | 'mid-market' | 'startup';
  activeShipments: number;
  totalExposure: number;
  onboardedAt: string;
}

export const CUSTOMERS: MockCustomer[] = [
  {
    id: 'cust_001', name: 'Maersk Line', industry: 'Container Shipping',
    contactName: 'Lars Andersen', contactEmail: 'l.andersen@maersk.com', contactPhone: '+45 3363 3363',
    region: 'Europe', tier: 'enterprise', activeShipments: 12, totalExposure: 4_200_000,
    onboardedAt: new Date(Date.now() - 90 * 86400000).toISOString(),
  },
  {
    id: 'cust_002', name: 'ACME Logistics', industry: 'Freight Forwarding',
    contactName: 'Sarah Chen', contactEmail: 's.chen@acmelogistics.com', contactPhone: '+1 212 555 0142',
    region: 'North America', tier: 'mid-market', activeShipments: 5, totalExposure: 850_000,
    onboardedAt: new Date(Date.now() - 60 * 86400000).toISOString(),
  },
  {
    id: 'cust_003', name: 'Global Trade Inc', industry: 'Import/Export',
    contactName: 'Raj Patel', contactEmail: 'r.patel@globaltrade.com', contactPhone: '+44 20 7946 0958',
    region: 'Asia-Pacific', tier: 'enterprise', activeShipments: 8, totalExposure: 2_100_000,
    onboardedAt: new Date(Date.now() - 120 * 86400000).toISOString(),
  },
  {
    id: 'cust_004', name: 'VinaTech Export', industry: 'Electronics Manufacturing',
    contactName: 'Linh Tran', contactEmail: 'linh.tran@vinatech.vn', contactPhone: '+84 28 3822 6777',
    region: 'Southeast Asia', tier: 'mid-market', activeShipments: 3, totalExposure: 520_000,
    onboardedAt: new Date(Date.now() - 45 * 86400000).toISOString(),
  },
  {
    id: 'cust_005', name: 'Nordic Freight AS', industry: 'Bulk Cargo',
    contactName: 'Erik Johansson', contactEmail: 'erik.j@nordicfreight.no', contactPhone: '+47 22 00 2500',
    region: 'Europe', tier: 'mid-market', activeShipments: 4, totalExposure: 680_000,
    onboardedAt: new Date(Date.now() - 30 * 86400000).toISOString(),
  },
  {
    id: 'cust_006', name: 'Pacific Rim Trading', industry: 'Commodities',
    contactName: 'James Wong', contactEmail: 'j.wong@pacificrim.hk', contactPhone: '+852 2522 1838',
    region: 'Asia-Pacific', tier: 'enterprise', activeShipments: 6, totalExposure: 1_850_000,
    onboardedAt: new Date(Date.now() - 75 * 86400000).toISOString(),
  },
  {
    id: 'cust_007', name: 'Desert Storm Logistics', industry: 'Oil & Gas Support',
    contactName: 'Ahmad Al-Rashid', contactEmail: 'a.rashid@desertstorm.ae', contactPhone: '+971 4 330 8888',
    region: 'Middle East', tier: 'mid-market', activeShipments: 2, totalExposure: 390_000,
    onboardedAt: new Date(Date.now() - 20 * 86400000).toISOString(),
  },
  {
    id: 'cust_008', name: 'Harbour Bridge Co', industry: 'Automotive Parts',
    contactName: 'Yuki Tanaka', contactEmail: 'y.tanaka@harbourbridge.jp', contactPhone: '+81 3 6234 5678',
    region: 'Asia-Pacific', tier: 'startup', activeShipments: 2, totalExposure: 180_000,
    onboardedAt: new Date(Date.now() - 14 * 86400000).toISOString(),
  },
];

// ─── Shipments ───────────────────────────────────────────

export interface MockShipment {
  id: string;
  customerId: string;
  carrier: string;
  vesselName: string;
  origin: string;
  destination: string;
  route: string;
  chokepoints: string[];
  cargoValue: number;
  containerCount: number;
  departureDate: string;
  eta: string;
  status: 'in_transit' | 'at_port' | 'delayed' | 'diverted';
}

function generateShipments(): MockShipment[] {
  const shipments: MockShipment[] = [];
  let counter = 1;

  for (const customer of CUSTOMERS) {
    for (let i = 0; i < customer.activeShipments && counter <= 15; i++) {
      const route = rng.pick([...ROUTES]);
      const carrier = rng.pick([...CARRIERS]);
      const origin = PORTS.find(p => p.code === route.origin)!;
      const dest = PORTS.find(p => p.code === route.destination)!;
      const daysAgo = rng.int(1, 20);
      const transitDays = rng.int(14, 35);

      shipments.push({
        id: `SHP-${String(counter).padStart(4, '0')}`,
        customerId: customer.id,
        carrier,
        vesselName: `${carrier} ${rng.pick(['Aurora', 'Horizon', 'Voyager', 'Meridian', 'Frontier', 'Expedition'])}`,
        origin: origin.name,
        destination: dest.name,
        route: route.name,
        chokepoints: [...route.chokepoints],
        cargoValue: rng.int(50, 500) * 1000,
        containerCount: rng.int(2, 40),
        departureDate: new Date(Date.now() - daysAgo * 86400000).toISOString(),
        eta: new Date(Date.now() + (transitDays - daysAgo) * 86400000).toISOString(),
        status: rng.pick(['in_transit', 'in_transit', 'in_transit', 'delayed', 'diverted'] as const),
      });
      counter++;
    }
  }

  return shipments;
}

export const SHIPMENTS = generateShipments();
