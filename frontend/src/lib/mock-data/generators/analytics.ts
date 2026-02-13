/**
 * Analytics data generator — time-series metrics, calibration, performance.
 */

import { rng } from '../seed';

export interface AnalyticsData {
  performanceMetrics: {
    totalDecisions: number;
    avgResponseTime: number;
    accuracyRate: number;
    costSaved: number;
    decisionsTrend: number;
    responseTimeTrend: number;
    accuracyTrend: number;
    costSavedTrend: number;
  };
  decisionsByWeek: Array<{ week: string; total: number; acknowledged: number; overridden: number; escalated: number }>;
  decisionsByType: Array<{ name: string; value: number; color: string }>;
  calibrationData: Array<{ predicted: number; actual: number; count: number }>;
  systemMetrics: {
    signalsProcessed: number;
    avgLatency: number;
    uptime: number;
    apiCalls: number;
  };
}

export function generateAnalyticsData(_dateRange?: string): AnalyticsData {
  const weeks = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8'];

  return {
    performanceMetrics: {
      totalDecisions: rng.int(120, 180),
      avgResponseTime: rng.float(1.2, 2.5),
      accuracyRate: rng.float(0.72, 0.88),
      costSaved: rng.int(800000, 1500000),
      decisionsTrend: rng.int(5, 20),
      responseTimeTrend: rng.float(-0.3, 0.1),
      accuracyTrend: rng.float(0.02, 0.08),
      costSavedTrend: rng.int(50000, 200000),
    },
    decisionsByWeek: weeks.map(week => ({
      week,
      total: rng.int(12, 28),
      acknowledged: rng.int(8, 20),
      overridden: rng.int(1, 5),
      escalated: rng.int(0, 3),
    })),
    decisionsByType: [
      { name: 'REROUTE', value: rng.int(35, 50), color: 'var(--color-action-reroute)' },
      { name: 'DELAY', value: rng.int(15, 25), color: 'var(--color-action-delay)' },
      { name: 'INSURE', value: rng.int(10, 20), color: 'var(--color-action-insure)' },
      { name: 'MONITOR', value: rng.int(20, 35), color: 'var(--color-action-monitor)' },
      { name: 'DO_NOTHING', value: rng.int(5, 15), color: 'var(--color-action-nothing)' },
    ],
    calibrationData: [
      { predicted: 0.1, actual: 0.08, count: 12 },
      { predicted: 0.2, actual: 0.18, count: 18 },
      { predicted: 0.3, actual: 0.32, count: 25 },
      { predicted: 0.4, actual: 0.38, count: 30 },
      { predicted: 0.5, actual: 0.52, count: 28 },
      { predicted: 0.6, actual: 0.57, count: 22 },
      { predicted: 0.7, actual: 0.72, count: 20 },
      { predicted: 0.8, actual: 0.78, count: 15 },
      { predicted: 0.9, actual: 0.88, count: 10 },
    ],
    systemMetrics: {
      signalsProcessed: rng.int(1200, 2500),
      avgLatency: rng.int(120, 350),
      uptime: rng.float(99.5, 99.99),
      apiCalls: rng.int(45000, 85000),
    },
  };
}
