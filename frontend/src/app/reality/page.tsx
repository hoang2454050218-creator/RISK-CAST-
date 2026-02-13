/**
 * Reality Page — Oracle Reality Engine
 *
 * "Military-grade intelligence overview."
 * Full-screen map + live signal feed + summary cards.
 * Every number is LIVE from React Query cache.
 */

import { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router';
import { motion } from 'framer-motion';
import { useRealityEngine, type RealityRate, type RealityVesselAlert } from '@/hooks/useRealityEngine';
import { useSignalsList } from '@/hooks/useSignals';
import { useDecisionsList } from '@/hooks/useDecisions';
import { useEscalationsList } from '@/hooks/useEscalations';
import { LazyGlobalMap as GlobalMap } from '@/components/domain/map';
import { CHOKEPOINTS, normalizeChokepointId } from '@/components/domain/map/chokepoints';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  Globe,
  Anchor,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  AlertTriangle,
  Activity,
  DollarSign,
  Radio,
  ChevronRight,
  Zap,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem, pageTransition } from '@/lib/animations';
import { AnimatedCurrency } from '@/components/ui/animated-number';
import type { Signal } from '@/types/signal';

// ─── Alert type config ──────────────────────────────────────────
const alertTypeConfig: Record<string, { label: string; className: string }> = {
  DIVERSION: {
    label: 'Diversion',
    className: 'bg-action-reroute/10 text-action-reroute border border-action-reroute/30',
  },
  DELAY: {
    label: 'Delay',
    className: 'bg-warning/10 text-warning border border-warning/30',
  },
  PORT_CHANGE: {
    label: 'Port Change',
    className: 'bg-info/10 text-info border border-info/30',
  },
  SPEED_CHANGE: {
    label: 'Speed Change',
    className: 'bg-muted text-muted-foreground border border-border',
  },
};

// ═══════════════════════════════════════════════════════════════════
// SIGNAL FEED — Live auto-scrolling
// ═══════════════════════════════════════════════════════════════════
function SignalFeed({ signals }: { signals: Signal[] }) {
  const recentSignals = useMemo(
    () =>
      [...signals]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 20),
    [signals],
  );

  if (recentSignals.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
        <Radio className="h-4 w-4 mr-2 animate-pulse" />
        Awaiting signal data...
      </div>
    );
  }

  return (
    <div className="divide-y divide-border/30 max-h-[300px] overflow-y-auto scrollbar-thin">
      {recentSignals.map((signal) => (
        <Link
          key={signal.signal_id}
          to={`/signals`}
          className="flex items-start gap-3 px-4 py-2.5 hover:bg-muted/30 transition-colors group"
        >
          <span className="text-[10px] font-mono text-muted-foreground/60 pt-0.5 shrink-0 w-12 text-right tabular-nums">
            {formatDate(signal.created_at, { includeTime: true }).split(',').pop()?.trim() ?? ''}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-foreground/80 line-clamp-1 group-hover:text-foreground transition-colors">
              {signal.event_title}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              {signal.affected_chokepoints.length > 0 && (
                <span className="text-[10px] font-mono text-action-reroute/70">
                  {signal.affected_chokepoints.map(normalizeChokepointId).join(', ')}
                </span>
              )}
              <span className="text-[10px] font-mono text-muted-foreground/50">
                {Math.round(signal.probability * 100)}%
              </span>
            </div>
          </div>
          <ChevronRight className="h-3 w-3 text-muted-foreground/30 shrink-0 mt-1 group-hover:text-muted-foreground/60 transition-colors" />
        </Link>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// CHOKEPOINT HEALTH LIST
// ═══════════════════════════════════════════════════════════════════
function ChokepointHealthList({ signals }: { signals: Signal[] }) {
  const navigate = useNavigate();

  const chokepointData = useMemo(() => {
    const signalsByCP = new Map<string, number>();
    for (const s of signals) {
      if (s.status !== 'ACTIVE' && s.status !== 'CONFIRMED') continue;
      for (const cp of s.affected_chokepoints) {
        const id = normalizeChokepointId(cp);
        signalsByCP.set(id, (signalsByCP.get(id) ?? 0) + 1);
      }
    }

    return CHOKEPOINTS.map((cp) => {
      const count = signalsByCP.get(cp.id) ?? 0;
      const status = count >= 3 ? 'disrupted' : count >= 1 ? 'degraded' : 'operational';
      return { ...cp, signalCount: count, status };
    });
  }, [signals]);

  return (
    <div className="space-y-1.5">
      {chokepointData.map((cp) => {
        const colorMap: Record<string, { dot: string; text: string }> = {
          operational: { dot: 'bg-success', text: 'text-success' },
          degraded: { dot: 'bg-warning', text: 'text-warning' },
          disrupted: { dot: 'bg-error', text: 'text-error' },
        };
        const colors = colorMap[cp.status] ?? colorMap.operational;

        return (
          <button
            key={cp.id}
            onClick={() => navigate(`/signals?chokepoint=${cp.id}`)}
            className="w-full flex items-center justify-between rounded-lg px-3 py-2.5 bg-muted/20 border border-border/30 hover:bg-muted/40 transition-colors text-left"
          >
            <div className="flex items-center gap-2.5">
              <motion.span
                className={cn('inline-block h-2.5 w-2.5 rounded-full', colors.dot)}
                animate={
                  cp.status === 'disrupted'
                    ? { scale: [1, 1.3, 1], opacity: [1, 0.5, 1] }
                    : {}
                }
                transition={{ duration: 1.5, repeat: Infinity }}
              />
              <span className="text-xs font-medium text-foreground">{cp.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-muted-foreground/60">{cp.region}</span>
              {cp.signalCount > 0 ? (
                <Badge variant="secondary" className="text-[9px] px-1.5 py-0">
                  {cp.signalCount} signal{cp.signalCount !== 1 ? 's' : ''}
                </Badge>
              ) : (
                <span className="text-[9px] font-mono text-success/70 font-semibold">OK</span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// MAIN REALITY PAGE
// ═══════════════════════════════════════════════════════════════════
export function RealityPage() {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const navigate = useNavigate();
  const { data: realityData, isLoading, error, refetch } = useRealityEngine();
  const { data: signals = [] } = useSignalsList();
  const { data: decisions = [] } = useDecisionsList();
  const { data: escalations = [] } = useEscalationsList();

  // ── Derived metrics ──────────────────────────────────────────
  const activeSignals = signals.filter(
    (s) => s.status === 'ACTIVE' || s.status === 'CONFIRMED',
  );
  const pendingDecisions = decisions.filter((d) => d.status === 'PENDING');
  const immediateDecisions = pendingDecisions.filter((d) => d.q2_when?.urgency === 'IMMEDIATE');
  const pendingEscalations = escalations.filter(
    (e) => e.status === 'PENDING' || e.status === 'IN_REVIEW',
  );

  // Reality engine data
  type RateRow = {
    route: string;
    currentRate: number;
    previousRate: number;
    change: number;
    trend: 'UP' | 'DOWN' | 'STABLE';
    lastUpdated: string;
  };
  type VesselAlertRow = {
    id: string;
    vesselName: string;
    alertType: string;
    description: string;
    timestamp: string;
    location: string;
  };

  const rates: RateRow[] = (realityData?.rates ?? []).map((r: RealityRate) => ({
    route: r.route,
    currentRate: r.currentRate,
    previousRate: r.previousRate,
    change: Math.round(r.change * 10) / 10,
    trend: r.change > 2 ? 'UP' : r.change < -2 ? 'DOWN' : ('STABLE' as const),
    lastUpdated: r.lastUpdated,
  }));

  const vesselAlerts: VesselAlertRow[] = (realityData?.vesselAlerts ?? []).map((a: RealityVesselAlert) => ({
    id: a.id,
    vesselName: a.vesselName,
    alertType: a.alertType === 'port_congestion' ? 'PORT_CHANGE' : a.alertType.toUpperCase(),
    description: a.description,
    timestamp: a.timestamp,
    location: a.location,
  }));

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <Globe className="h-8 w-8 animate-pulse text-accent mx-auto" />
          <p className="text-sm text-muted-foreground">Loading reality data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-sm text-error">Failed to load reality data</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-5 pb-8"
      variants={pageTransition}
      initial="hidden"
      animate="visible"
    >
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <motion.div
            className="p-2.5 rounded-xl bg-gradient-to-br from-accent/20 to-accent/5 border border-accent/20"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 8, repeat: Infinity }}
          >
            <Globe className="h-5 w-5 text-accent" />
          </motion.div>
          <div>
            <h1 className="text-xl font-bold text-foreground tracking-tight">
              Reality Engine
            </h1>
            <p className="text-xs text-muted-foreground font-mono">
              LIVE{' '}
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-success animate-pulse mx-1 align-middle" />
              {activeSignals.length} active signals · {pendingDecisions.length} pending decisions
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="gap-2 border-accent/30 hover:border-accent/50"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>

      {/* ── Map + Disruptions Grid ──────────────────────────────── */}
      <div className="grid gap-5 lg:grid-cols-5">
        {/* Full interactive map — 3 columns */}
        <motion.div
          className="lg:col-span-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, ...springs.smooth }}
        >
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border/40 bg-muted/10 flex items-center justify-between">
              <span className="text-xs font-semibold text-foreground flex items-center gap-2">
                <Globe className="h-3.5 w-3.5 text-accent" />
                Global Overview
              </span>
              <span className="text-[10px] font-mono text-muted-foreground/60">
                Click chokepoint to filter signals
              </span>
            </div>
            <GlobalMap
              signals={signals}
              onChokepointClick={(cpId) => navigate(`/signals?chokepoint=${cpId}`)}
              className="h-[360px] lg:h-[420px] border-0 rounded-none"
            />
          </div>
        </motion.div>

        {/* Active Disruptions sidebar — 2 columns */}
        <motion.div
          className="lg:col-span-2 space-y-4"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, ...springs.smooth }}
        >
          {/* Chokepoint Health */}
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border/40 bg-muted/10">
              <span className="text-xs font-semibold text-foreground flex items-center gap-2">
                <Shield className="h-3.5 w-3.5 text-action-reroute" />
                Chokepoint Status
              </span>
            </div>
            <div className="p-3">
              <ChokepointHealthList signals={signals} />
            </div>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              icon={Zap}
              accentColor="red"
              value={immediateDecisions.length}
              label="Immediate"
              variant="overlay"
              tier="secondary"
              href="/decisions?urgency=IMMEDIATE"
            />
            <StatCard
              icon={AlertTriangle}
              accentColor="orange"
              value={pendingEscalations.length}
              label="Escalations"
              variant="overlay"
              tier="secondary"
              href="/human-review"
            />
          </div>
        </motion.div>
      </div>

      {/* ── Signal Feed ─────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25, ...springs.smooth }}
      >
        <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/40 bg-muted/10">
            <span className="text-xs font-semibold text-foreground flex items-center gap-2">
              <Radio className="h-3.5 w-3.5 text-info" />
              Signal Feed
              {activeSignals.length > 0 && (
                <Badge variant="secondary" className="text-[9px] px-1.5 py-0 ml-1">
                  {activeSignals.length} active
                </Badge>
              )}
            </span>
            <Link to="/signals">
              <Button variant="ghost" size="sm" className="h-6 text-xs gap-1 text-muted-foreground">
                View all <ChevronRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>
          <SignalFeed signals={signals} />
        </div>
      </motion.div>

      {/* ── Bottom Grid: Rates + Vessel Alerts ──────────────────── */}
      <div className="grid gap-5 lg:grid-cols-2">
        {/* Freight Rates */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, ...springs.smooth }}
        >
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden h-full">
            <div className="px-4 py-2.5 border-b border-border/40 bg-muted/10">
              <span className="text-xs font-semibold text-foreground flex items-center gap-2">
                <DollarSign className="h-3.5 w-3.5 text-success" />
                Spot Rates (FEU)
              </span>
            </div>
            <div className="p-3">
              {rates.length > 0 ? (
                <motion.div
                  className="space-y-2"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                >
                  {rates.map((rate) => (
                    <motion.div
                      key={rate.route}
                      variants={staggerItem}
                      className="flex items-center justify-between px-3 py-2.5 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <p className="text-xs font-medium">{rate.route}</p>
                        <p className="text-[10px] text-muted-foreground/60 font-mono">
                          {formatDate(rate.lastUpdated, { relative: true })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm font-bold tabular-nums">
                          <AnimatedCurrency value={rate.currentRate} />
                        </p>
                        <p
                          className={cn(
                            'text-[10px] font-mono font-bold flex items-center gap-0.5 justify-end',
                            rate.change > 0
                              ? 'text-error'
                              : rate.change < 0
                                ? 'text-success'
                                : 'text-muted-foreground',
                          )}
                        >
                          {rate.change > 0 ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : rate.change < 0 ? (
                            <TrendingDown className="h-3 w-3" />
                          ) : null}
                          {rate.change > 0 ? '+' : ''}
                          {rate.change}%
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              ) : (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-xs">
                  No rate data available
                </div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Vessel Alerts */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, ...springs.smooth }}
        >
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden h-full">
            <div className="px-4 py-2.5 border-b border-border/40 bg-muted/10">
              <span className="text-xs font-semibold text-foreground flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-action-reroute" />
                Vessel Alerts
              </span>
            </div>
            <div className="p-3">
              {vesselAlerts.length > 0 ? (
                <motion.div
                  className="space-y-2"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                >
                  {vesselAlerts.map((alert) => {
                    const config = alertTypeConfig[alert.alertType] ?? alertTypeConfig.DELAY;
                    return (
                      <motion.div
                        key={alert.id}
                        variants={staggerItem}
                        className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        <Anchor className="h-4 w-4 text-action-reroute/60 mt-0.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-0.5">
                            <span className="font-medium text-xs">{alert.vesselName}</span>
                            <Badge className={cn('text-[9px] px-1.5 py-0', config.className)}>
                              {config.label}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-muted-foreground line-clamp-1">
                            {alert.description}
                          </p>
                        </div>
                        <span className="text-[10px] font-mono text-muted-foreground/50 shrink-0">
                          {formatDate(alert.timestamp, { relative: true })}
                        </span>
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-xs">
                  No vessel alerts
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

export default RealityPage;
