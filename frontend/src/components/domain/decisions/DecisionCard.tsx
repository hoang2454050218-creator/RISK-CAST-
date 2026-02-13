/**
 * DecisionCard - Ultra-Premium Bloomberg-Grade Design
 * Glass morphism, glow borders, hero exposure numbers
 * "Each card is a financial decision brief"
 */

import { Link, useNavigate } from 'react-router';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { UrgencyBadge } from '@/components/domain/common/UrgencyBadge';
import { SeverityBadge } from '@/components/domain/common/SeverityBadge';
import { ActionBadge } from '@/components/domain/common/ActionBadge';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import { SwipeableCard, type SwipeAction } from '@/components/ui/swipeable-card';
import {
  ChevronRight,
  Check,
  RefreshCw,
  Eye,
  AlertTriangle,
  Archive,
  Clock,
  ArrowUpRight,
  DollarSign,
  Ship,
  Zap,
  TrendingDown,
  TrendingUp,
  MapPin,
  ShieldAlert,
  Timer,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import { springs } from '@/lib/animations';
import { statusConfig } from './DecisionHeader';
import type { Decision, Urgency } from '@/types/decision';

interface DecisionCardProps {
  decision: Decision;
  onAcknowledge?: (id: string) => void;
  onEscalate?: (id: string) => void;
  onArchive?: (id: string) => void;
  isLoading?: boolean;
  variant?: 'default' | 'compact';
  enableSwipe?: boolean;
  className?: string;
}

const urgencyStyle: Record<Urgency, {
  gradient: string;
  topGradient: string;
  bgTint: string;
  glowClass: string;
  borderClass: string;
  exposureColor: string;
}> = {
  IMMEDIATE: {
    gradient: 'from-urgency-immediate via-urgency-immediate/80 to-urgency-immediate',
    topGradient: 'from-urgency-immediate via-urgency-immediate/80 to-urgency-immediate',
    bgTint: 'from-urgency-immediate/[0.03] to-transparent',
    glowClass: 'rc-glow-red', // lint-ignore-token — glow classes defined in index.css
    borderClass: 'border-urgency-immediate/25',
    exposureColor: 'text-urgency-immediate',
  },
  URGENT: {
    gradient: 'from-urgency-urgent via-urgency-urgent/80 to-urgency-urgent',
    topGradient: 'from-urgency-urgent via-urgency-urgent/80 to-urgency-urgent',
    bgTint: 'from-urgency-urgent/[0.02] to-transparent',
    glowClass: 'rc-glow-amber', // lint-ignore-token
    borderClass: 'border-urgency-urgent/20',
    exposureColor: 'text-urgency-urgent',
  },
  SOON: {
    gradient: 'from-urgency-soon via-urgency-soon/80 to-urgency-soon',
    topGradient: 'from-urgency-soon via-urgency-soon/80 to-urgency-soon',
    bgTint: 'from-urgency-soon/[0.02] to-transparent',
    glowClass: '',
    borderClass: 'border-urgency-soon/15',
    exposureColor: 'text-urgency-soon',
  },
  WATCH: {
    gradient: 'from-accent via-accent/80 to-accent',
    topGradient: 'from-accent via-accent/80 to-accent',
    bgTint: 'from-accent/[0.02] to-transparent',
    glowClass: '',
    borderClass: 'border-border/40',
    exposureColor: 'text-foreground',
  },
};

function getExposureColor(usd: number) {
  if (usd >= 200000) return 'text-urgency-immediate';
  if (usd >= 100000) return 'text-urgency-urgent';
  if (usd >= 50000) return 'text-urgency-soon';
  return 'text-foreground';
}

export function DecisionCard({
  decision,
  onAcknowledge,
  onEscalate,
  onArchive,
  isLoading = false,
  variant = 'default',
  enableSwipe = true,
  className,
}: DecisionCardProps) {
  const navigate = useNavigate();
  const status = statusConfig[decision.status] ?? { label: decision.status ?? 'Unknown', variant: 'secondary' as const };
  const isPending = decision.status === 'PENDING';
  const urgencyKey = decision.q2_when?.urgency ?? 'WATCH';
  const urgency = urgencyStyle[urgencyKey] ?? urgencyStyle.WATCH;
  const isImmediate = urgencyKey === 'IMMEDIATE';
  const exposure = decision.q3_severity?.total_exposure_usd ?? 0;
  const exposureColor = isPending ? getExposureColor(exposure) : 'text-foreground/60';

  if (variant === 'compact') {
    return (
      <CompactDecisionCard
        decision={decision}
        onAcknowledge={onAcknowledge}
        onEscalate={onEscalate}
        onArchive={onArchive}
        isLoading={isLoading}
        enableSwipe={enableSwipe}
        className={className}
      />
    );
  }

  const leftActions: SwipeAction[] = isPending && onAcknowledge
    ? [{ id: 'acknowledge', label: 'Accept', icon: <Check className="h-5 w-5" />, color: 'white', bgColor: 'bg-success', action: () => onAcknowledge(decision.decision_id) }]
    : [];

  const rightActions: SwipeAction[] = [
    ...(onEscalate && isPending ? [{ id: 'escalate', label: 'Escalate', icon: <AlertTriangle className="h-5 w-5" />, color: 'white', bgColor: 'bg-destructive', action: () => onEscalate(decision.decision_id) }] : []),
    ...(onArchive ? [{ id: 'archive', label: 'Archive', icon: <Archive className="h-5 w-5" />, color: 'white', bgColor: 'bg-muted-foreground', action: () => onArchive(decision.decision_id) }] : []),
    { id: 'view', label: 'View', icon: <Eye className="h-5 w-5" />, color: 'white', bgColor: 'bg-muted', action: () => navigate(`/decisions/${decision.decision_id}`) },
  ];

  const cardContent = (
    <motion.div
      role="article"
      aria-label={`Decision: ${decision.q1_what?.event_summary ?? 'Unknown'}`}
      className={cn(
        'group relative h-full flex flex-col overflow-hidden rounded-2xl',
        'bg-card/80 backdrop-blur-sm border shadow-level-1 transition-all duration-200',
        isPending ? urgency.borderClass : 'border-border/40',
        isPending && urgency.glowClass,
        isImmediate && isPending && 'border-l-2 border-l-urgency-immediate/50 breathe-glow',
        'hover:shadow-level-2',
        className,
      )}
      whileHover={{ y: -6, transition: { duration: 0.25, ease: 'easeOut' } }}
    >
      {/* ── Top accent bar with shimmer ── */}
      <div className={cn('h-1.5 w-full bg-gradient-to-r relative overflow-hidden', isPending ? urgency.topGradient : 'from-muted-foreground/40 to-muted-foreground/30')}>
        {isPending && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/25 to-transparent"
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
          />
        )}
      </div>

      {/* ── Background tint ── */}
      {isPending && (
        <div className={cn('absolute inset-0 top-1.5 bg-gradient-to-b pointer-events-none', urgency.bgTint)} />
      )}

      {/* ── Header badges ── */}
      <div className="relative flex items-start justify-between gap-2 p-4 pb-2">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          <UrgencyBadge urgency={decision.q2_when?.urgency ?? 'WATCH'} size="sm" />
          <SeverityBadge severity={decision.q3_severity?.severity ?? 'LOW'} size="sm" />
          <Badge variant={status.variant} size="sm">{status.label}</Badge>
        </div>
        {isPending && decision.expires_at && (
          <div className="flex-shrink-0">
            <CompactCountdown deadline={decision.expires_at} />
          </div>
        )}
        <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-300 group-hover:translate-x-1 group-hover:-translate-y-1">
          <ArrowUpRight className="h-4 w-4 text-accent" />
        </div>
      </div>

      {/* ── Content ── */}
      <div className="px-4 pb-2 flex-1">
        <h3 className="font-semibold text-sm text-foreground leading-snug line-clamp-2 group-hover:text-accent transition-colors duration-200">
          {decision.q1_what?.event_summary ?? 'Decision pending analysis'}
        </h3>
        <p className="text-[11px] text-muted-foreground/60 mt-1.5 line-clamp-2 leading-relaxed">
          {decision.q1_what?.personalized_impact ?? ''}
        </p>
      </div>

      {/* ── Financial Decision Brief Panel ── */}
      {(() => {
        const actionCost = decision.q5_action?.estimated_cost_usd ?? 0;
        const inactionCost = decision.q7_inaction?.inaction_cost_usd ?? 0;
        const savings = Math.max(0, exposure - actionCost);
        const benefit = decision.q5_action?.expected_benefit_usd ?? savings;
        const deadline = decision.q5_action?.deadline ?? decision.expires_at;
        const shipmentsAffected = decision.q3_severity?.shipments_affected ?? 0;
        const topShipment = decision.q3_severity?.breakdown_by_shipment?.[0];
        const worstCase = decision.q7_inaction?.worst_case_scenario;

        return (
          <div className="mx-3 mb-3 rounded-xl overflow-hidden border border-border/30 bg-muted/20">
            {/* Hero: Exposure at risk */}
            <div className="px-4 py-3 border-b border-border/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <DollarSign className="h-4 w-4 text-muted-foreground/40" />
                  <span className="text-[8px] text-muted-foreground/40 uppercase tracking-[0.15em] font-mono font-medium">TOTAL EXPOSURE</span>
                </div>
                <p className={cn('font-mono text-2xl font-black tabular-nums tracking-tight leading-none', exposureColor)}>
                  {formatCurrency(exposure, { compact: true })}
                </p>
              </div>
            </div>

            {/* Financial decision row: Action Cost vs Loss if Nothing */}
            <div className="grid grid-cols-3 divide-x divide-border/20 border-b border-border/20">
              {/* Recommended action + cost */}
              <div className="px-2.5 py-2.5 text-center">
                <div className="flex items-center justify-center gap-1 mb-1">
                  <Zap className="h-3 w-3 text-accent/50" />
                  <span className="text-[7px] text-muted-foreground/40 uppercase tracking-[0.12em] font-mono">Action</span>
                </div>
                <ActionBadge action={decision.q5_action?.recommended_action ?? 'MONITOR'} size="sm" showIcon={false} />
                {actionCost > 0 && (
                  <p className="font-mono text-[10px] text-muted-foreground mt-1 tabular-nums">
                    {formatCurrency(actionCost, { compact: true })}
                  </p>
                )}
              </div>

              {/* You save */}
              {savings > 0 && (
                <div className="px-2.5 py-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <TrendingDown className="h-3 w-3 text-success/50" />
                    <span className="text-[7px] text-muted-foreground/40 uppercase tracking-[0.12em] font-mono">You Save</span>
                  </div>
                  <p className="font-mono text-sm font-bold text-success tabular-nums">
                    {formatCurrency(savings, { compact: true })}
                  </p>
                </div>
              )}

              {/* Loss if nothing */}
              {inactionCost > 0 && (
                <div className="px-2.5 py-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <ShieldAlert className="h-3 w-3 text-destructive/40" />
                    <span className="text-[7px] text-destructive/40 uppercase tracking-[0.12em] font-mono">If Nothing</span>
                  </div>
                  <p className="font-mono text-sm font-bold text-destructive/80 tabular-nums">
                    {formatCurrency(inactionCost, { compact: true })}
                  </p>
                </div>
              )}
            </div>

            {/* Context row: Shipments + Deadline + Route */}
            <div className="grid grid-cols-3 divide-x divide-border/20">
              <div className="px-2.5 py-2 text-center">
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <Ship className="h-3 w-3 text-muted-foreground/40" />
                  <span className="text-[7px] text-muted-foreground/40 uppercase tracking-[0.12em] font-mono">Shipments</span>
                </div>
                <p className="font-mono text-sm font-bold text-foreground tabular-nums">
                  {shipmentsAffected}
                </p>
              </div>

              <div className="px-2.5 py-2 text-center">
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <Timer className="h-3 w-3 text-muted-foreground/40" />
                  <span className="text-[7px] text-muted-foreground/40 uppercase tracking-[0.12em] font-mono">Deadline</span>
                </div>
                {isPending && deadline && (
                  <CompactCountdown deadline={deadline} className="text-sm font-bold font-mono" />
                )}
                {!isPending && <p className="text-sm font-mono text-muted-foreground/50">—</p>}
              </div>

              <div className="px-2.5 py-2 text-center">
                <div className="flex items-center justify-center gap-1 mb-0.5">
                  <MapPin className="h-3 w-3 text-muted-foreground/40" />
                  <span className="text-[7px] text-muted-foreground/40 uppercase tracking-[0.12em] font-mono">Route</span>
                </div>
                <p className="font-mono text-[10px] text-foreground/70 truncate leading-tight">
                  {topShipment?.route ?? decision.q1_what?.affected_routes?.[0] ?? '—'}
                </p>
              </div>
            </div>

            {/* Worst case warning — only for critical/high */}
            {isPending && worstCase && (urgencyKey === 'IMMEDIATE' || urgencyKey === 'URGENT') && (
              <div className="px-3 py-2 border-t border-border/20 bg-destructive/[0.03]">
                <p className="text-[9px] text-destructive/60 font-mono line-clamp-2 leading-relaxed">
                  <AlertTriangle className="h-3 w-3 inline mr-1 -mt-0.5" />
                  {worstCase}
                </p>
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Footer ── */}
      <div className="flex items-center justify-between px-4 py-2.5 mt-auto border-t border-border/30 bg-muted/10">
        <div className="text-xs text-muted-foreground/40 font-mono flex items-center gap-2 truncate min-w-0">
          <span className="px-1.5 py-0.5 rounded-md bg-muted/30 border border-border/20 text-[9px] shrink-0">
            {decision.decision_id.slice(0, 10)}
          </span>
          <span className="truncate">{decision.customer_id}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 ml-2">
          {isPending && onAcknowledge && (
            <Button
              size="sm"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onAcknowledge(decision.decision_id); }}
              disabled={isLoading}
              className="h-7 px-3 text-xs font-semibold font-mono border-0 rounded-lg bg-success hover:bg-success/90 text-success-foreground shadow-sm hover:shadow-lg hover:shadow-success/20 transition-all"
            >
              {isLoading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5 mr-1" />}
              Accept
            </Button>
          )}
          <Link to={`/decisions/${decision.decision_id}`}>
            <Button size="sm" variant="ghost" className="h-7 px-2 text-xs text-muted-foreground/60 hover:text-foreground gap-0.5 rounded-lg">
              Details <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      </div>
    </motion.div>
  );

  if (enableSwipe && (leftActions.length > 0 || rightActions.length > 0)) {
    return (
      <SwipeableCard leftActions={leftActions} rightActions={rightActions} className={cn('touch-pan-y h-full', className)} onSwipeRight={isPending && onAcknowledge ? () => onAcknowledge(decision.decision_id) : undefined}>
        {cardContent}
      </SwipeableCard>
    );
  }
  return cardContent;
}

/* ═══════════════════════════════════════
   COMPACT VARIANT
   ═══════════════════════════════════════ */

function CompactDecisionCard({
  decision,
  onAcknowledge,
  onEscalate,
  onArchive: _onArchive,
  enableSwipe = true,
  className,
}: DecisionCardProps) {
  const status = statusConfig[decision.status] ?? { label: decision.status ?? 'Unknown', variant: 'secondary' as const };
  const deadline = decision.q5_action?.deadline ?? decision.expires_at;
  const isPending = decision.status === 'PENDING';
  const urgencyKey = decision.q2_when?.urgency ?? 'WATCH';
  const urgency = urgencyStyle[urgencyKey] ?? urgencyStyle.WATCH;
  const exposure = decision.q3_severity?.total_exposure_usd ?? 0;
  const actionCost = decision.q5_action?.estimated_cost_usd ?? 0;
  const inactionCost = decision.q7_inaction?.inaction_cost_usd ?? 0;
  const savings = Math.max(0, exposure - actionCost);
  const exposureColor = isPending ? getExposureColor(exposure) : 'text-foreground/60';

  const leftActions: SwipeAction[] = isPending && onAcknowledge
    ? [{ id: 'acknowledge', label: 'Accept', icon: <Check className="h-5 w-5" />, color: 'white', bgColor: 'bg-success', action: () => onAcknowledge(decision.decision_id) }]
    : [];

  const rightActions: SwipeAction[] = [
    ...(onEscalate && isPending ? [{ id: 'escalate', label: 'Escalate', icon: <AlertTriangle className="h-5 w-5" />, color: 'white', bgColor: 'bg-destructive', action: () => onEscalate(decision.decision_id) }] : []),
  ];

  const cardContent = (
    <Link to={`/decisions/${decision.decision_id}`} className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background">
      <motion.div
        className={cn(
          'group relative flex flex-col gap-2 p-4 rounded-2xl overflow-hidden',
          'bg-card/80 backdrop-blur-sm border shadow-level-1 transition-all duration-200',
          isPending ? urgency.borderClass : 'border-border/40',
          isPending && urgency.glowClass,
          'hover:shadow-level-2',
          className,
        )}
        whileHover={{ x: 4 }}
        transition={springs.snappy}
      >
        {isPending && <div className={cn('absolute inset-y-0 left-0 w-1 bg-gradient-to-b rounded-l-2xl', urgency.gradient)} />}

        {/* Row 1: Badges + Exposure */}
        <div className="flex items-start gap-3 pl-1.5">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-1.5">
              <UrgencyBadge urgency={decision.q2_when?.urgency ?? 'WATCH'} size="sm" showIcon={false} />
              <Badge variant={status.variant} size="sm">{status.label}</Badge>
            </div>
            <p className="font-semibold text-sm text-foreground truncate group-hover:text-accent transition-colors">
              {decision.q1_what?.event_summary ?? 'Decision pending'}
            </p>
          </div>
          <div className="text-right flex-shrink-0 space-y-0.5">
            <p className={cn('font-mono text-2xl font-black tabular-nums tracking-tight leading-none', exposureColor)}>
              {formatCurrency(exposure, { compact: true })}
            </p>
            {isPending && (
              <div className="flex items-center justify-end gap-1 text-muted-foreground/40">
                <Clock className="h-2.5 w-2.5" />
                <CompactCountdown deadline={deadline} className="text-[10px] font-mono" />
              </div>
            )}
          </div>
        </div>

        {/* Row 2: Business context — Action, Savings, Inaction Cost */}
        <div className="flex items-center gap-3 pl-3 text-[10px] font-mono">
          {/* Shipments + Route */}
          <span className="flex items-center gap-0.5 text-muted-foreground/50">
            <Ship className="h-2.5 w-2.5" />
            {decision.q3_severity?.shipments_affected ?? 0}
          </span>

          <span className="text-border/30">|</span>

          {/* Action + Cost */}
          <span className="flex items-center gap-1">
            <ActionBadge action={decision.q5_action?.recommended_action ?? 'MONITOR'} size="sm" showIcon={false} />
            {actionCost > 0 && (
              <span className="text-muted-foreground/50">{formatCurrency(actionCost, { compact: true })}</span>
            )}
          </span>

          {/* Savings */}
          {savings > 0 && (
            <>
              <span className="text-border/30">|</span>
              <span className="flex items-center gap-0.5 text-success/70">
                <TrendingDown className="h-2.5 w-2.5" />
                Save {formatCurrency(savings, { compact: true })}
              </span>
            </>
          )}

          {/* Inaction warning */}
          {inactionCost > 0 && isPending && (
            <>
              <span className="text-border/30">|</span>
              <span className="flex items-center gap-0.5 text-destructive/50">
                <AlertTriangle className="h-2.5 w-2.5" />
                Loss: {formatCurrency(inactionCost, { compact: true })}
              </span>
            </>
          )}
        </div>
      </motion.div>
    </Link>
  );

  if (enableSwipe && (leftActions.length > 0 || rightActions.length > 0)) {
    return (
      <SwipeableCard leftActions={leftActions} rightActions={rightActions} className={cn('touch-pan-y', className)} onSwipeRight={isPending && onAcknowledge ? () => onAcknowledge(decision.decision_id) : undefined}>
        {cardContent}
      </SwipeableCard>
    );
  }
  return cardContent;
}

export default DecisionCard;
