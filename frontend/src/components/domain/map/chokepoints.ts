/**
 * Chokepoint geographic data — real-world coordinates
 *
 * These are fixed positions on the globe — no backend needed.
 * Status is derived from live signals via affected_chokepoints.
 */

export interface ChokepointGeo {
  id: string;
  name: string;
  region: string;
  lng: number;
  lat: number;
  /** Zoom level where this chokepoint is most readable */
  idealZoom: number;
}

export const CHOKEPOINTS: ChokepointGeo[] = [
  {
    id: 'SUEZ',
    name: 'Suez Canal',
    region: 'Egypt',
    lng: 32.35,
    lat: 30.46,
    idealZoom: 6,
  },
  {
    id: 'RED_SEA',
    name: 'Bab el-Mandeb',
    region: 'Red Sea',
    lng: 43.33,
    lat: 12.58,
    idealZoom: 6,
  },
  {
    id: 'PANAMA',
    name: 'Panama Canal',
    region: 'Central America',
    lng: -79.91,
    lat: 9.08,
    idealZoom: 6,
  },
  {
    id: 'MALACCA',
    name: 'Strait of Malacca',
    region: 'Southeast Asia',
    lng: 101.2,
    lat: 2.5,
    idealZoom: 6,
  },
  {
    id: 'STRAIT_OF_HORMUZ',
    name: 'Strait of Hormuz',
    region: 'Persian Gulf',
    lng: 56.27,
    lat: 26.59,
    idealZoom: 6,
  },
  {
    id: 'CAPE_OF_GOOD_HOPE',
    name: 'Cape of Good Hope',
    region: 'South Africa',
    lng: 18.49,
    lat: -34.36,
    idealZoom: 5,
  },
];

/** Map from any variant of chokepoint ID to our canonical ID */
const ID_ALIASES: Record<string, string> = {
  SUEZ: 'SUEZ',
  suez_canal: 'SUEZ',
  'suez-canal': 'SUEZ',
  RED_SEA: 'RED_SEA',
  'red-sea': 'RED_SEA',
  bab_el_mandeb: 'RED_SEA',
  PANAMA: 'PANAMA',
  panama_canal: 'PANAMA',
  'panama-canal': 'PANAMA',
  MALACCA: 'MALACCA',
  malacca_strait: 'MALACCA',
  'strait-of-malacca': 'MALACCA',
  STRAIT_OF_HORMUZ: 'STRAIT_OF_HORMUZ',
  hormuz: 'STRAIT_OF_HORMUZ',
  'strait-of-hormuz': 'STRAIT_OF_HORMUZ',
  CAPE_OF_GOOD_HOPE: 'CAPE_OF_GOOD_HOPE',
  'cape-of-good-hope': 'CAPE_OF_GOOD_HOPE',
  cape_of_good_hope: 'CAPE_OF_GOOD_HOPE',
};

export function normalizeChokepointId(raw: string): string {
  return ID_ALIASES[raw] ?? raw.toUpperCase();
}

export type ChokepointStatus = 'operational' | 'degraded' | 'disrupted';

export interface ChokepointState extends ChokepointGeo {
  status: ChokepointStatus;
  signalCount: number;
  /** Most severe urgency affecting this chokepoint */
  worstUrgency?: string;
}
