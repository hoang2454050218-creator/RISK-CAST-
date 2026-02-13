/**
 * RISKCAST Signal Types
 *
 * Mirrors: app/omen/schemas.py
 *
 * Signals are raw intelligence from various sources
 * They are NOT decisions - they feed into the decision engine
 */

export type SignalStatus = 'ACTIVE' | 'CONFIRMED' | 'EXPIRED' | 'DISMISSED';

export type SignalSource =
  | 'POLYMARKET'
  | 'NEWS'
  | 'AIS'
  | 'RATES'
  | 'WEATHER'
  | 'GOVERNMENT'
  | 'SOCIAL_MEDIA';

export type EventType =
  | 'ROUTE_DISRUPTION'
  | 'PORT_CONGESTION'
  | 'WEATHER_EVENT'
  | 'GEOPOLITICAL'
  | 'RATE_SPIKE'
  | 'CARRIER_ISSUE'
  | 'CUSTOMS_DELAY';

export interface EvidenceItem {
  source_type: SignalSource;
  source_name: string;
  data_point: string;
  url?: string;
  timestamp: string;
  confidence: number;
  raw_data?: Record<string, unknown>;
}

export interface Signal {
  signal_id: string;
  event_type: EventType;
  event_title: string;
  event_description: string;

  // Probability & Confidence
  probability: number; // Event likelihood (0-1)
  confidence: number; // Data quality (0-1)

  // Affected areas
  affected_chokepoints: string[];
  affected_routes: string[];
  affected_regions: string[];

  // Evidence
  evidence: EvidenceItem[];
  primary_source: SignalSource;

  // Status
  status: SignalStatus;
  created_at: string;
  updated_at: string;
  expires_at?: string;

  // Impact estimation (pre-decision)
  estimated_impact_usd?: number;
  customers_affected?: number;
  shipments_affected?: number;

  // Decisions generated from this signal
  decision_ids: string[];
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
  page?: number;
  page_size?: number;
}
