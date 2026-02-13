/**
 * Dashboard Page - Premium Enterprise Command Center
 * Style: Bloomberg data-density + Linear cleanness + subtle glow
 * "Mission control for supply chain risk decisions"
 */

import { Link, useNavigate } from 'react-router';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SkeletonDashboard } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/states';
import { UrgencyBadge } from '@/components/domain/common/UrgencyBadge';
import { SeverityBadge } from '@/components/domain/common/SeverityBadge';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import { StatCard } from '@/components/domain/common/StatCard';
import { useDashboardData } from '@/hooks/useDashboard';
import { useDecisionsList } from '@/hooks/useDecisions';
import { useSignalsList } from '@/hooks/useSignals';
import { useEscalationsList } from '@/hooks/useEscalations';
import { LazyGlobalMap as GlobalMap } from '@/components/domain/map';
import {
  AlertTriangle,
  Bell,
  DollarSign,
  ChevronRight,
  CheckCircle,
  Clock,
  MapPin,
  Zap,
  ShieldCheck,
  Radio,
  Brain,
  Globe,
  Activity,
  ArrowRight,
  TrendingDown,
  Ship,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem, pageTransition } from '@/lib/animations';
import type { Urgency } from '@/types/decision';

// ─── Urgency visual config ──────────────────────────────────
const urgencyConfig: Record<Urgency, {
  gradient: string;
  bg: string;
  border: string;
  glow: string;
  text: string;
}> = {
  IMMEDIATE: {
    gradient: 'from-error via-error/80 to-error/60',
    bg: 'bg-error/[0.06]',
    border: 'border-error/25',
    glow: 'shadow-[0_0_20px_rgba(239,68,68,0.15)]',
    text: 'text-error',
  },
  URGENT: {
    gradient: 'from-warning via-warning/80 to-warning/60',
    bg: 'bg-warning/[0.05]',
    border: 'border-warning/20',
    glow: '',
    text: 'text-warning',
  },
  SOON: {
    gradient: 'from-warning/60 via-warning/40 to-warning/20',
    bg: 'bg-warning/[0.03]',
    border: 'border-warning/15',
    glow: '',
    text: 'text-warning',
  },
  WATCH: {
    gradient: 'from-info via-accent/60 to-accent/40',
    bg: '',
    border: 'border-border',
    glow: '',
    text: 'text-info',
  },
};

// ─── Activity type config ───────────────────────────────────
const activityConfig: Record<string, {
  icon: typeof Activity;
  color: string;
  bg: string;
  dot: string;
}> = {
  decision: { icon: Brain, color: 'text-success', bg: 'bg-success/10', dot: 'bg-success' },
  signal: { icon: Radio, color: 'text-info', bg: 'bg-info/10', dot: 'bg-info' },
  escalation: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10', dot: 'bg-warning' },
  customer: { icon: Globe, color: 'text-accent', bg: 'bg-accent/10', dot: 'bg-accent' },
};

// ─── Time formatting ────────────────────────────────────────
function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// ═══════════════════════════════════════════════════════════════
// PIPELINE STEPPER
// ═══════════════════════════════════════════════════════════════

function PipelineStepper() {
  const { data: decisions = [] } = useDecisionsList();
  const { data: signals = [] } = useSignalsList();
  const { data: escalations = [] } = useEscalationsList();

  const activeSignals = signals.filter((s) => s.status === 'ACTIVE' || s.status === 'CONFIRMED').length;
  const pendingDecisions = decisions.filter((d) => d.status === 'PENDING').length;
  const pendingActions = escalations.filter((e) => e.status === 'PENDING' || e.status === 'IN_REVIEW').length;

  const steps = [
    {
      icon: Radio,
      label: 'Signals',
      count: activeSignals,
      sublabel: 'ACTIVE TODAY',
      href: '/signals',
      color: 'accent' as const,
    },
    {
      icon: Brain,
      label: 'Decisions',
      count: pendingDecisions,
      sublabel: 'PENDING REVIEW',
      href: '/decisions',
      color: 'warning' as const,
    },
    {
      icon: Zap,
      label: 'Actions',
      count: pendingActions,
      sublabel: 'NEED APPROVAL',
      href: '/human-review',
      color: 'success' as const,
    },
  ];

  const colorMap = {
    accent: {
      iconBg: 'bg-accent/10 border-accent/20',
      iconText: 'text-accent',
      badge: 'bg-accent/15 text-accent border-accent/30',
      line: 'from-accent/40 to-accent/10',
      glow: activeSignals > 0 ? 'shadow-[0_0_15px_rgba(59,130,246,0.1)]' : '',
    },
    warning: {
      iconBg: 'bg-warning/10 border-warning/20',
      iconText: 'text-warning',
      badge: 'bg-warning/15 text-warning border-warning/30',
      line: 'from-warning/40 to-warning/10',
      glow: pendingDecisions > 0 ? 'shadow-[0_0_15px_rgba(245,158,11,0.1)]' : '',
    },
    success: {
      iconBg: 'bg-success/10 border-success/20',
      iconText: 'text-success',
      badge: 'bg-success/15 text-success border-success/30',
      line: 'from-success/40 to-success/10',
      glow: pendingActions > 0 ? 'shadow-[0_0_15px_rgba(34,197,94,0.1)]' : '',
    },
  };

  return (
    <div className="relative">
      {/* Glass container */}
      <div className="rounded-2xl border border-border/50 bg-card/60 backdrop-blur-sm shadow-level-1 p-1.5">
        <div className="flex items-stretch gap-1">
          {steps.map((step, i) => {
            const colors = colorMap[step.color];
            const isActive = step.count > 0;

            return (
              <div key={step.label} className="flex items-stretch flex-1">
                <Link to={step.href} className="flex-1">
                  <motion.div
                    className={cn(
                      'relative flex items-center gap-3.5 rounded-xl border p-3.5 transition-all h-full',
                      'bg-card hover:bg-card-hover',
                      isActive ? `${colors.glow} border-border/80` : 'border-transparent',
                    )}
                    whileHover={{ y: -2, scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    transition={springs.snappy}
                  >
                    {/* Icon */}
                    <div className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-lg border shrink-0',
                      isActive ? colors.iconBg : 'bg-muted/50 border-border text-muted-foreground',
                    )}>
                      <step.icon className={cn('h-5 w-5', isActive ? colors.iconText : '')} />
                    </div>

                    {/* Content */}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-foreground">{step.label}</span>
                        {step.count > 0 && (
                          <motion.span
                            className={cn(
                              'inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold border',
                              colors.badge,
                            )}
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={springs.bouncy}
                          >
                            {step.count}
                          </motion.span>
                        )}
                      </div>
                      <p className="text-[9px] font-mono text-muted-foreground tracking-wider mt-0.5">
                        {step.sublabel}
                      </p>
                    </div>
                  </motion.div>
                </Link>

                {/* Connector arrow */}
                {i < steps.length - 1 && (
                  <div className="hidden sm:flex items-center px-1 shrink-0">
                    <div className="flex items-center">
                      <div className={cn('h-px w-4 bg-gradient-to-r', colors.line)} />
                      <ArrowRight className="h-3 w-3 text-muted-foreground/30" />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ═══════════════════════════════════════════════════════════════

export function DashboardPage() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useDashboardData();
  const { data: allSignals = [] } = useSignalsList();

  if (isLoading) return <SkeletonDashboard />;
  if (error) return <ErrorState title="Failed to load dashboard" onRetry={refetch} />;
  if (!data) return null;

  const stats = data.stats ?? {
    activeDecisions: 0,
    activeDecisionsTrend: 0,
    pendingEscalations: 0,
    pendingEscalationsTrend: 0,
    avgResponseTime: 'N/A',
    totalExposure: 0,
    totalExposureTrend: 0,
  };
  const urgentDecisions = data.urgentDecisions ?? [];
  const recentActivity = data.recentActivity ?? [];

  return (
    <motion.div
      className="relative space-y-6 pb-8"
      variants={pageTransition}
      initial="hidden"
      animate="visible"
    >
      {/* ── Gradient mesh background ─────────────────────────── */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-80 overflow-hidden -z-10">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-accent/[0.04] blur-3xl" />
        <div className="absolute -top-20 -left-20 h-60 w-60 rounded-full bg-info/[0.03] blur-3xl" />
        <div className="absolute top-10 left-1/3 h-40 w-40 rounded-full bg-success/[0.03] blur-3xl" />
      </div>

      {/* ── Page Header ──────────────────────────────────────── */}
      <motion.div
        className="flex items-start justify-between gap-4"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight">
            Command Center
          </h1>
          <p className="text-xs text-muted-foreground font-mono mt-1 flex items-center gap-2">
            <span className="uppercase tracking-wider">Supply Chain Intelligence</span>
            <span className="text-border">|</span>
            <span className="text-muted-foreground/60">
              {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
            </span>
          </p>
        </div>

        {/* Live status indicator */}
        <motion.button
          onClick={() => refetch()}
          className={cn(
            'group flex items-center gap-2.5 h-9 pl-3 pr-4 rounded-xl transition-all duration-200',
            'bg-success/[0.06] border border-success/15',
            'hover:bg-success/[0.1] hover:border-success/25 hover:shadow-[0_0_20px_rgba(34,197,94,0.08)]',
          )}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success/40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </span>
          <ShieldCheck className="h-4 w-4 text-success" />
          <div className="flex flex-col items-start leading-none">
            <span className="text-[11px] font-mono font-semibold tracking-wider text-success">
              SYSTEM ONLINE
            </span>
            <span className="text-[8px] font-mono text-success/50 tracking-wider mt-0.5">
              ALL SERVICES OK
            </span>
          </div>
        </motion.button>
      </motion.div>

      {/* ── Workflow Pipeline ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ...springs.smooth }}
      >
        <PipelineStepper />
      </motion.div>

      {/* ── Hero Metric — Total Exposure ──────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12, ...springs.smooth }}
      >
        <StatCard
          label="Total Exposure at Risk"
          value={stats.totalExposure}
          change={stats.totalExposureTrend}
          trend={stats.totalExposureTrend >= 0 ? 'up' : 'down'}
          icon={DollarSign}
          isCurrency
          accentColor="red"
          variant="overlay"
          tier="hero"
          sublabel="Across all active decisions and monitored shipments"
          urgent={stats.totalExposure > 500000}
        />
      </motion.div>

      {/* ── Stats Grid — Supporting Metrics ────────────────────── */}
      <motion.div
        className="grid gap-4 sm:grid-cols-3"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            label="Active Decisions"
            value={stats.activeDecisions}
            change={stats.activeDecisionsTrend}
            trend={stats.activeDecisionsTrend >= 0 ? 'up' : 'down'}
            icon={AlertTriangle}
            href="/decisions"
            accentColor="amber"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            label="Critical Signals"
            value={stats.pendingEscalations}
            change={stats.pendingEscalationsTrend}
            trend={stats.pendingEscalationsTrend >= 0 ? 'up' : 'down'}
            icon={Bell}
            href="/signals"
            urgent={stats.pendingEscalations > 0}
            accentColor="red"
            variant="overlay"
            highlight
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            label="Data Freshness"
            value={stats.avgResponseTime}
            icon={Clock}
            accentColor="blue"
            variant="overlay"
            tier="secondary"
          />
        </motion.div>
      </motion.div>

      {/* ── Main Content Grid ────────────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-3">

        {/* Urgent Decisions — 2 columns */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, ...springs.smooth }}
        >
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden">
            {/* Section header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/40 bg-muted/10">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-warning/10 border border-warning/20">
                  <Zap className="h-3.5 w-3.5 text-warning" />
                </div>
                Decisions Requiring Action
                {urgentDecisions.length > 0 && (
                  <Badge className="ml-1 text-[10px] bg-warning/10 text-warning border-warning/30">
                    {urgentDecisions.length}
                  </Badge>
                )}
              </h2>
              <Link to="/decisions">
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  View all
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>

            {/* Decision items */}
            <div className="p-3 space-y-1.5">
              {urgentDecisions.length > 0 ? (
                <motion.div variants={staggerContainer} initial="hidden" animate="visible">
                  {urgentDecisions.slice(0, 5).map((decision) => {
                    const uc = urgencyConfig[decision.urgency] ?? urgencyConfig.WATCH;
                    return (
                      <motion.div key={decision.id} variants={staggerItem}>
                        <Link to={`/decisions/${decision.id}`}>
                          <motion.div
                            className={cn(
                              'group relative flex flex-col gap-2 rounded-xl p-3.5 transition-all overflow-hidden',
                              'border hover:shadow-sm',
                              uc.bg || 'bg-muted/30',
                              uc.border,
                              uc.glow,
                            )}
                            whileHover={{ y: -2, x: 2 }}
                            transition={springs.snappy}
                          >
                            {/* Left urgency bar */}
                            <div className={cn(
                              'absolute inset-y-0 left-0 w-1 bg-gradient-to-b rounded-l-xl',
                              uc.gradient,
                            )}>
                              {decision.urgency === 'IMMEDIATE' && (
                                <motion.div
                                  className="absolute inset-0 bg-error rounded-l-xl"
                                  animate={{ opacity: [0.4, 1, 0.4] }}
                                  transition={{ duration: 1.5, repeat: Infinity }}
                                />
                              )}
                            </div>

                            {/* Row 1: Badges + Exposure + Countdown */}
                            <div className="flex items-start gap-3 pl-2">
                              <div className="flex-1 space-y-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <UrgencyBadge urgency={decision.urgency} size="sm" />
                                  <SeverityBadge severity={decision.severity} size="sm" />
                                  <span className="text-[10px] text-muted-foreground font-mono truncate">
                                    {decision.customer}
                                  </span>
                                </div>
                                <p className="font-medium text-sm text-foreground/90 line-clamp-1 group-hover:text-foreground transition-colors">
                                  {decision.title}
                                </p>
                              </div>

                              {/* Exposure + countdown */}
                              <div className="text-right space-y-0.5 flex-shrink-0">
                                <p className={cn(
                                  'font-mono text-lg font-bold tabular-nums',
                                  decision.exposure > 0 ? 'text-foreground' : 'text-muted-foreground',
                                )}>
                                  {decision.exposure > 0 ? formatCurrency(decision.exposure, { compact: true }) : '--'}
                                </p>
                                <CompactCountdown
                                  deadline={new Date(decision.deadline)}
                                  className="text-[10px] font-mono text-muted-foreground"
                                />
                              </div>

                              <ChevronRight className="h-4 w-4 text-muted-foreground/30 flex-shrink-0 group-hover:text-muted-foreground/60 transition-colors mt-2" />
                            </div>

                            {/* Row 2: Business decision context */}
                            {(decision.actionCost > 0 || decision.savings > 0 || decision.route) && (
                              <div className="flex items-center gap-3 pl-3 text-[10px] font-mono flex-wrap">
                                {/* Action + Cost */}
                                {decision.actionType && decision.actionType !== 'MONITOR' && (
                                  <div className="flex items-center gap-1">
                                    <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent font-bold text-[9px]">
                                      {decision.actionType}
                                    </span>
                                    {decision.actionCost > 0 && (
                                      <span className="text-muted-foreground">
                                        {formatCurrency(decision.actionCost, { compact: true })}
                                      </span>
                                    )}
                                  </div>
                                )}

                                {/* Savings */}
                                {decision.savings > 0 && (
                                  <div className="flex items-center gap-0.5 text-success/80">
                                    <TrendingDown className="h-3 w-3" />
                                    <span>Save {formatCurrency(decision.savings, { compact: true })}</span>
                                  </div>
                                )}

                                {/* Inaction cost */}
                                {decision.inactionCost > 0 && (
                                  <div className="flex items-center gap-0.5 text-destructive/60">
                                    <AlertTriangle className="h-3 w-3" />
                                    <span>Loss: {formatCurrency(decision.inactionCost, { compact: true })}</span>
                                  </div>
                                )}

                                {/* Route */}
                                {decision.route && (
                                  <>
                                    <span className="text-border/40">|</span>
                                    <div className="flex items-center gap-0.5 text-muted-foreground/50">
                                      <Ship className="h-3 w-3" />
                                      <span>{decision.shipmentsAffected}</span>
                                      <MapPin className="h-3 w-3 ml-0.5" />
                                      <span className="truncate max-w-[120px]">{decision.route}</span>
                                    </div>
                                  </>
                                )}
                              </div>
                            )}
                          </motion.div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <motion.div
                  className="flex flex-col items-center justify-center py-10 text-center"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={springs.bouncy}
                >
                  <div className="relative mb-4">
                    <div className="p-4 rounded-2xl bg-success/[0.06] border border-success/15">
                      <CheckCircle className="h-8 w-8 text-success" />
                    </div>
                    <motion.div
                      className="absolute inset-0 rounded-2xl bg-success/10"
                      animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0, 0.3] }}
                      transition={{ duration: 2.5, repeat: Infinity }}
                    />
                  </div>
                  <p className="font-semibold text-foreground">All caught up!</p>
                  <p className="text-xs text-muted-foreground mt-0.5">No urgent decisions pending</p>
                </motion.div>
              )}
            </div>
          </div>
        </motion.div>

        {/* Global Chokepoint Map — 1 column */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, ...springs.smooth }}
        >
          <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden h-full flex flex-col">
            {/* Header */}
            <div className="px-5 py-3.5 border-b border-border/40 bg-muted/10">
              <h2 className="text-sm font-semibold text-foreground flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-action-reroute/10 border border-action-reroute/20">
                  <Globe className="h-3.5 w-3.5 text-action-reroute" />
                </div>
                Global Chokepoints
              </h2>
            </div>

            {/* Map */}
            <GlobalMap
              signals={allSignals}
              compact
              onChokepointClick={(cpId) => navigate(`/signals?chokepoint=${cpId}`)}
              className="flex-1 min-h-[280px] border-0 rounded-none"
            />
          </div>
        </motion.div>
      </div>

      {/* ── Recent Activity ──────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, ...springs.smooth }}
      >
        <div className="rounded-2xl border border-border/60 bg-card shadow-level-1 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/40 bg-muted/10">
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-info/10 border border-info/20">
                <Activity className="h-3.5 w-3.5 text-info" />
              </div>
              Recent Activity
              {recentActivity.length > 0 && (
                <span className="text-[10px] font-mono text-muted-foreground/60 ml-1">
                  {recentActivity.length} events
                </span>
              )}
            </h2>
          </div>

          <div className="p-4">
            {recentActivity.length > 0 ? (
              <motion.div className="relative" variants={staggerContainer} initial="hidden" animate="visible">
                {/* Vertical timeline line */}
                <div className="absolute left-[15px] top-2 bottom-2 w-px bg-gradient-to-b from-border via-border/60 to-transparent" />

                <div className="space-y-1">
                  {recentActivity.map((activity) => {
                    const config = activityConfig[activity.type] ?? activityConfig.customer;
                    const IconComp = config.icon;

                    return (
                      <motion.div
                        key={activity.id}
                        variants={staggerItem}
                        className="relative flex items-start gap-3.5 pl-1 py-2 rounded-lg hover:bg-muted/30 transition-colors"
                      >
                        {/* Timeline dot */}
                        <div className="relative z-10 shrink-0">
                          <div className={cn(
                            'flex h-[30px] w-[30px] items-center justify-center rounded-lg border',
                            config.bg,
                            'border-border/40',
                          )}>
                            <IconComp className={cn('h-3.5 w-3.5', config.color)} />
                          </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0 pt-1">
                          <p className="text-xs text-foreground leading-relaxed">
                            <span className="font-semibold">{activity.title}</span>
                          </p>
                          <p className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                            {activity.actor}
                          </p>
                        </div>

                        {/* Timestamp */}
                        <span className="text-[10px] font-mono text-muted-foreground/60 shrink-0 pt-1">
                          {timeAgo(activity.timestamp)}
                        </span>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="p-3 rounded-xl bg-muted/50 border border-border/40 mb-3">
                  <Activity className="h-6 w-6 text-muted-foreground/40" />
                </div>
                <p className="text-sm text-muted-foreground">No recent activity</p>
                <p className="text-[11px] text-muted-foreground/60 mt-0.5">Activity will appear here as events occur</p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default DashboardPage;
