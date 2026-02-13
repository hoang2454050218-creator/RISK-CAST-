import type { Decision } from '@/types/decision';
import type { Signal } from '@/types/signal';

/**
 * Mock decision data for development and testing
 * This represents a realistic Red Sea disruption scenario
 */
export const mockDecision: Decision = {
  // Metadata
  decision_id: 'dec_a1b2c3d4e5f6g7h8i9j0',
  customer_id: 'cust_acme_logistics',
  created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 min ago
  expires_at: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(), // 4 hours from now
  status: 'PENDING',
  version: 3,

  // Q1: What is happening?
  q1_what: {
    event_type: 'ROUTE_DISRUPTION',
    event_summary:
      'Houthi missile attacks force major shipping lines to suspend Red Sea transit. Multiple vessels diverting to Cape of Good Hope route.',
    affected_chokepoints: ['RED_SEA', 'SUEZ'],
    affected_routes: ['Asia-Europe', 'Asia-Mediterranean', 'Middle East-Europe'],
    source_attribution: "Polymarket (87% probability), Reuters, Lloyd's List",
    personalized_impact:
      'Your 5 active shipments from Shanghai to Rotterdam are directly affected. 3 vessels have already announced diversions.',
  },

  // Q2: When?
  q2_when: {
    urgency: 'URGENT',
    decision_deadline: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
    event_timeline:
      'Disruption began 48 hours ago. Major carriers MSC, Maersk, and CMA CGM have suspended bookings. Situation expected to persist 2-4 weeks minimum.',
    time_to_impact_hours: 72,
    escalation_triggers: [
      'If no action within 6 hours, reroute costs increase by 15%',
      'MSC booking window closes in 8 hours',
      'Premium insurance rates expire at midnight UTC',
    ],
  },

  // Q3: How bad?
  q3_severity: {
    severity: 'HIGH',
    total_exposure_usd: 235000,
    exposure_ci_90: {
      lower: 185000,
      upper: 310000,
      confidence_level: 0.9,
    },
    shipments_affected: 5,
    teu_affected: 12,
    expected_delay_days: 12,
    delay_range: [7, 18],
    breakdown_by_shipment: [
      {
        shipment_id: 'PO-4521',
        cargo_value_usd: 450000,
        exposure_usd: 67500,
        route: 'Shanghai → Rotterdam',
        eta: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        shipment_id: 'PO-4533',
        cargo_value_usd: 380000,
        exposure_usd: 57000,
        route: 'Ningbo → Hamburg',
        eta: new Date(Date.now() + 16 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        shipment_id: 'PO-4545',
        cargo_value_usd: 290000,
        exposure_usd: 43500,
        route: 'Shenzhen → Antwerp',
        eta: new Date(Date.now() + 18 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        shipment_id: 'PO-4557',
        cargo_value_usd: 320000,
        exposure_usd: 48000,
        route: 'Qingdao → Rotterdam',
        eta: new Date(Date.now() + 20 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        shipment_id: 'PO-4569',
        cargo_value_usd: 125000,
        exposure_usd: 19000,
        route: 'Shanghai → Felixstowe',
        eta: new Date(Date.now() + 22 * 24 * 60 * 60 * 1000).toISOString(),
      },
    ],
  },

  // Q4: Why?
  q4_why: {
    root_cause:
      'Houthi rebel attacks on commercial shipping in response to Gaza conflict have made Red Sea transit unviable for major carriers.',
    causal_chain: [
      {
        from_event: 'Gaza Conflict Escalation',
        to_event: 'Houthi Retaliation Announcement',
        relationship: 'Political trigger',
        confidence: 0.95,
      },
      {
        from_event: 'Houthi Missile Attacks',
        to_event: 'MSC Vessel Hit (Dec 15)',
        relationship: 'Direct attack',
        confidence: 0.98,
      },
      {
        from_event: 'MSC Vessel Hit',
        to_event: 'Major Carriers Suspend Red Sea Transit',
        relationship: 'Risk mitigation',
        confidence: 0.92,
      },
      {
        from_event: 'Carriers Suspend Transit',
        to_event: 'Your Shipments at Risk',
        relationship: 'Route disruption',
        confidence: 0.88,
      },
    ],
    evidence_sources: [
      {
        source_type: 'PREDICTION_MARKET',
        source_name: 'Polymarket',
        data_point: 'Red Sea shipping disruption continues through Q1 2024: 87% probability',
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        confidence: 0.87,
      },
      {
        source_type: 'NEWS',
        source_name: 'Reuters',
        data_point: 'MSC, Maersk, CMA CGM, Hapag-Lloyd announce Red Sea suspension',
        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        confidence: 0.95,
      },
      {
        source_type: 'AIS_DATA',
        source_name: 'MarineTraffic',
        data_point: '47 vessels observed diverting around Cape of Good Hope in past 24h',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        confidence: 0.92,
      },
      {
        source_type: 'RATES',
        source_name: 'Freightos Baltic Index',
        data_point: 'Asia-Europe spot rates up 35% in 48 hours',
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
        confidence: 0.9,
      },
    ],
    historical_precedent:
      'Similar situation in 2021 Suez blockage resulted in 12% of global trade affected. Cape route adds 10-14 days and $1M+ fuel costs per large vessel.',
  },

  // Q5: What to do?
  q5_action: {
    recommended_action: 'REROUTE',
    action_summary:
      'REROUTE all 5 shipments via Cape of Good Hope with MSC. Book immediately to secure capacity before rate increases.',
    action_details: {
      new_route: 'Cape of Good Hope',
      carrier: 'MSC',
      vessel: 'MSC Aurora (next available)',
    },
    estimated_cost_usd: 42500,
    cost_ci_90: {
      lower: 38000,
      upper: 52000,
      confidence_level: 0.9,
    },
    expected_benefit_usd: 192500, // 235000 - 42500
    implementation_steps: [
      'Contact MSC booking desk immediately (contact: +31 10 429 2888)',
      'Request Cape of Good Hope routing for containers in PO-4521, PO-4533, PO-4545, PO-4557, PO-4569',
      'Confirm revised ETAs with your Rotterdam warehouse',
      'Notify end customers of 10-14 day delay',
      'Update inventory planning for delayed arrival',
    ],
    deadline: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
    alternatives: [
      {
        action_type: 'DELAY',
        summary: 'Hold shipments at origin for 2-3 weeks',
        cost_usd: 28000,
        trade_off: 'Lower cost but adds 21+ days delay. Risk situation worsens.',
      },
      {
        action_type: 'INSURE',
        summary: 'Purchase war risk insurance, proceed via Red Sea',
        cost_usd: 85000,
        trade_off:
          'Covers losses but significant premium. Does not prevent delay if attack occurs.',
      },
      {
        action_type: 'MONITOR',
        summary: 'Wait 24-48 hours for situation clarity',
        cost_usd: 0,
        trade_off: 'Risk of higher reroute costs. MSC capacity may sell out.',
      },
    ],
  },

  // Q6: Confidence
  q6_confidence: {
    overall_confidence: 'HIGH',
    confidence_score: 0.82,
    confidence_factors: [
      {
        factor: 'Multiple corroborating sources',
        contribution: 'POSITIVE',
        weight: 0.15,
        explanation: "Reuters, Lloyd's List, MarineTraffic data all confirm disruption",
      },
      {
        factor: 'Prediction market signal',
        contribution: 'POSITIVE',
        weight: 0.12,
        explanation: 'Polymarket shows 87% probability of continued disruption',
      },
      {
        factor: 'Historical pattern match',
        contribution: 'POSITIVE',
        weight: 0.08,
        explanation: 'Similar to 2021 Suez crisis response patterns',
      },
      {
        factor: 'Rate volatility',
        contribution: 'NEGATIVE',
        weight: -0.05,
        explanation: 'Rapid rate changes add uncertainty to cost estimates',
      },
      {
        factor: 'Geopolitical unpredictability',
        contribution: 'NEGATIVE',
        weight: -0.08,
        explanation: 'Situation could de-escalate suddenly if ceasefire achieved',
      },
    ],
    key_uncertainties: [
      'Duration of Houthi attacks unknown - could end with diplomatic resolution',
      'Carrier capacity on Cape route may become constrained',
      'Fuel price volatility affects reroute cost estimates',
    ],
    what_could_change: [
      'UN Security Council intervention',
      'US Navy increased escort operations',
      'Ceasefire agreement in Gaza',
      'Additional carrier capacity announcements',
    ],
    calibration: {
      historical_accuracy: 0.79,
      sample_size: 847,
      relative_performance: 'above_average',
      calibration_factors: [
        {
          direction: 'positive',
          strength: 'strong',
          description: '3 independent data sources corroborate signal',
        },
        {
          direction: 'positive',
          strength: 'strong',
          description: 'Historical pattern match (89% similarity to 2021 Suez crisis)',
        },
        {
          direction: 'positive',
          strength: 'moderate',
          description: 'Prediction market consensus above 85%',
        },
        {
          direction: 'negative',
          strength: 'weak',
          description: 'Limited real-time vessel tracking data in Red Sea corridor',
        },
        {
          direction: 'negative',
          strength: 'weak',
          description: 'No direct carrier confirmation of reroute capacity',
        },
      ],
    },
  },

  // Q7: If nothing
  q7_inaction: {
    inaction_cost_usd: 235000,
    inaction_cost_ci_90: {
      lower: 185000,
      upper: 310000,
      confidence_level: 0.9,
    },
    inaction_delay_days: 21,
    point_of_no_return: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
    cost_escalation: [
      {
        timestamp: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        cost_usd: 48000,
        description: 'Reroute cost if action taken within 2 hours',
      },
      {
        timestamp: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
        cost_usd: 62000,
        description: 'Reroute cost increases 30% as capacity fills',
      },
      {
        timestamp: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
        cost_usd: 95000,
        description: 'Premium rates kick in, limited vessel options',
      },
      {
        timestamp: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
        cost_usd: 235000,
        description: 'Full exposure realized - cargo stranded or heavily delayed',
      },
    ],
    worst_case_scenario:
      'If no action taken: All 5 shipments delayed 3+ weeks. Customer penalties of $45,000 triggered. Inventory stockouts at Rotterdam DC. Potential loss of Acme Corp contract worth $2.1M annually.',
  },

  // Audit
  signal_ids: [
    'sig_red_sea_attack_001',
    'sig_polymarket_87pct',
    'sig_msc_suspension',
    'sig_rates_spike_35pct',
    'sig_ais_diversion_47v',
  ],
  reasoning_trace_id: 'trace_7q_analysis_a1b2c3',
};

/**
 * Multiple decisions for list view testing
 */
export const mockDecisions: Decision[] = [
  mockDecision,
  {
    ...mockDecision,
    decision_id: 'dec_x9y8z7w6v5u4t3s2r1',
    status: 'ACKNOWLEDGED',
    q2_when: {
      ...mockDecision.q2_when,
      urgency: 'IMMEDIATE',
    },
    q3_severity: {
      ...mockDecision.q3_severity,
      severity: 'CRITICAL',
      total_exposure_usd: 520000,
    },
  },
  {
    ...mockDecision,
    decision_id: 'dec_m1n2o3p4q5r6s7t8u9',
    status: 'PENDING',
    q2_when: {
      ...mockDecision.q2_when,
      urgency: 'SOON',
    },
    q3_severity: {
      ...mockDecision.q3_severity,
      severity: 'MEDIUM',
      total_exposure_usd: 45000,
    },
  },
];

/**
 * Mock signal data for development and testing
 */
export const mockSignals: Signal[] = [
  {
    signal_id: 'sig_red_sea_001',
    event_type: 'ROUTE_DISRUPTION',
    event_title: 'Red Sea Shipping Disruption - Houthi Attacks',
    event_description:
      'Multiple shipping lines suspending Red Sea transit due to Houthi rebel attacks on commercial vessels. Major carriers including MSC, Maersk, and CMA CGM have announced diversions via Cape of Good Hope.',
    probability: 0.87,
    confidence: 0.92,
    affected_chokepoints: ['RED_SEA', 'SUEZ'],
    affected_routes: ['Asia-Europe', 'Asia-Mediterranean', 'Middle East-Europe'],
    affected_regions: ['Red Sea', 'Gulf of Aden', 'Bab el-Mandeb'],
    evidence: [
      {
        source_type: 'POLYMARKET',
        source_name: 'Polymarket',
        data_point: 'Red Sea disruption continues through Q1: 87% probability',
        url: 'https://polymarket.com/event/red-sea',
        timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        confidence: 0.87,
      },
      {
        source_type: 'NEWS',
        source_name: 'Reuters',
        data_point: 'MSC, Maersk, CMA CGM announce Red Sea suspension',
        url: 'https://reuters.com/...',
        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        confidence: 0.95,
      },
      {
        source_type: 'AIS',
        source_name: 'MarineTraffic',
        data_point: '47 vessels observed diverting around Cape of Good Hope in past 24h',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        confidence: 0.92,
      },
      {
        source_type: 'RATES',
        source_name: 'Freightos Baltic Index',
        data_point: 'Asia-Europe spot rates up 35% in 48 hours',
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
        confidence: 0.9,
      },
    ],
    primary_source: 'POLYMARKET',
    status: 'ACTIVE',
    created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
    estimated_impact_usd: 2500000,
    customers_affected: 12,
    shipments_affected: 47,
    decision_ids: ['dec_a1b2c3d4e5f6g7h8i9j0'],
  },
  {
    signal_id: 'sig_panama_002',
    event_type: 'PORT_CONGESTION',
    event_title: 'Panama Canal Capacity Restrictions Extended',
    event_description:
      'Panama Canal Authority extends daily transit limits due to ongoing drought. Wait times averaging 8-12 days for unreserved slots.',
    probability: 0.95,
    confidence: 0.88,
    affected_chokepoints: ['PANAMA'],
    affected_routes: ['Asia-US East Coast', 'South America-US'],
    affected_regions: ['Panama', 'Caribbean'],
    evidence: [
      {
        source_type: 'GOVERNMENT',
        source_name: 'Panama Canal Authority',
        data_point: 'Official announcement: 24 daily transits limit through March',
        timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
        confidence: 0.98,
      },
      {
        source_type: 'AIS',
        source_name: 'VesselFinder',
        data_point: '156 vessels currently waiting for transit',
        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
        confidence: 0.9,
      },
    ],
    primary_source: 'GOVERNMENT',
    status: 'CONFIRMED',
    created_at: new Date(Date.now() - 72 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
    estimated_impact_usd: 1200000,
    customers_affected: 8,
    shipments_affected: 23,
    decision_ids: [],
  },
  {
    signal_id: 'sig_rates_003',
    event_type: 'RATE_SPIKE',
    event_title: 'Trans-Pacific Spot Rates Surge',
    event_description:
      'Shanghai-Los Angeles spot rates increased 28% week-over-week. Pre-Lunar New Year rush combined with Red Sea diversions driving capacity constraints.',
    probability: 1.0,
    confidence: 0.95,
    affected_chokepoints: [],
    affected_routes: ['Asia-US West Coast', 'Asia-US East Coast'],
    affected_regions: ['Pacific'],
    evidence: [
      {
        source_type: 'RATES',
        source_name: 'Freightos Baltic Index',
        data_point: 'FBX China-USWC index: $3,245/FEU (+28% WoW)',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        confidence: 0.98,
      },
      {
        source_type: 'NEWS',
        source_name: 'Journal of Commerce',
        data_point: 'Carriers announcing GRIs for February sailings',
        timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
        confidence: 0.85,
      },
    ],
    primary_source: 'RATES',
    status: 'ACTIVE',
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    estimated_impact_usd: 450000,
    customers_affected: 15,
    shipments_affected: 31,
    decision_ids: [],
  },
];
