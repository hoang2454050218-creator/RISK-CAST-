/**
 * VerdictBanner — Executive Decision Brief
 *
 * Business Decision Language:
 * "What's at risk → What to do → What it costs → What you save → What happens if you don't"
 *
 * Scannable in 3 seconds. Every number is real data from the decision engine.
 * No technical jargon — only money, time, and action.
 */

import { motion } from 'framer-motion';
import {
  Zap,
  Clock,
  Shield,
  ArrowRight,
  DollarSign,
  TrendingDown,
  AlertTriangle,
  Ship,
  MapPin,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatCurrencyRange } from '@/lib/formatters';
import { springs } from '@/lib/animations';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import type { Decision } from '@/types/decision';

interface VerdictBannerProps {
  decision: Decision;
  onAct?: () => void;
  className?: string;
}

const SEVERITY_BORDER: Record<string, string> = {
  CRITICAL: 'border-severity-critical',
  HIGH: 'border-severity-high',
  MEDIUM: 'border-severity-medium',
  LOW: 'border-severity-low',
};

const SEVERITY_BG: Record<string, string> = {
  CRITICAL: 'bg-destructive/[0.03]',
  HIGH: 'bg-urgency-urgent/[0.02]',
  MEDIUM: '',
  LOW: '',
};

const ACTION_LABELS: Record<string, string> = {
  REROUTE: 'Reroute Shipments',
  DELAY: 'Delay Shipment',
  INSURE: 'Buy Insurance',
  MONITOR: 'Monitor Only',
  DO_NOTHING: 'No Action Needed',
  HEDGE: 'Hedge Risk',
};

export function VerdictBanner({ decision, onAct, className }: VerdictBannerProps) {
  const action = decision.q5_action;
  const severity = decision.q3_severity?.severity ?? 'MEDIUM';
  const exposure = decision.q3_severity?.total_exposure_usd ?? 0;
  const actionCost = action?.estimated_cost_usd ?? 0;
  const inactionCost = decision.q7_inaction?.inaction_cost_usd ?? 0;
  const savings = Math.max(0, exposure - actionCost);
  const shipmentsAffected = decision.q3_severity?.shipments_affected ?? 0;
  const deadline = action?.deadline ?? decision.q2_when?.decision_deadline;
  const confidence = decision.q6_confidence?.confidence_score ?? 0;
  const worstCase = decision.q7_inaction?.worst_case_scenario;
  const exposureCI = decision.q3_severity?.exposure_ci_90;
  const actionCostCI = action?.cost_ci_90;
  const inactionCostCI = decision.q7_inaction?.inaction_cost_ci_90;
  const topRoute = decision.q3_severity?.breakdown_by_shipment?.[0]?.route
    ?? decision.q1_what?.affected_routes?.[0]
    ?? '';
  const isPending = decision.status === 'PENDING';

  const actionLabel = ACTION_LABELS[action?.recommended_action ?? ''] ?? action?.recommended_action ?? 'Review';

  return (
    <motion.div
      className={cn(
        'rounded-xl border-l-4 bg-card overflow-hidden',
        SEVERITY_BORDER[severity] ?? 'border-border',
        SEVERITY_BG[severity],
        className,
      )}
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      {/* Row 1: Executive Summary — The one-liner */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 pb-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 min-w-0">
          {/* Exposure headline */}
          <div className="flex items-center gap-1.5">
            <DollarSign className="h-4 w-4 text-destructive/60 flex-shrink-0" />
            <span className={cn(
              'text-lg font-bold font-mono tabular-nums tracking-tight',
              exposure >= 200000 ? 'text-destructive' : exposure >= 100000 ? 'text-urgency-urgent' : 'text-foreground',
            )}>
              {formatCurrency(exposure, { compact: true })}
            </span>
            {exposureCI ? (
              <span className="text-[10px] text-muted-foreground/60 font-mono tabular-nums">
                ({formatCurrencyRange(exposureCI.lower, exposureCI.upper, { compact: true })})
              </span>
            ) : (
              <span className="text-xs text-muted-foreground font-mono">at risk</span>
            )}
          </div>

          {/* Shipments + Route */}
          {shipmentsAffected > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Ship className="h-3.5 w-3.5" />
              <span className="text-xs font-mono">{shipmentsAffected} shipment{shipmentsAffected !== 1 ? 's' : ''}</span>
              {topRoute && (
                <>
                  <MapPin className="h-3.5 w-3.5 ml-1" />
                  <span className="text-xs font-mono truncate max-w-[150px]">{topRoute}</span>
                </>
              )}
            </div>
          )}

          {/* Deadline countdown */}
          {isPending && deadline && (
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span className="text-xs font-mono">Deadline:</span>
              <CompactCountdown deadline={deadline} className="text-xs font-mono font-bold" />
            </div>
          )}
        </div>

        {/* CTA Button */}
        {onAct && isPending && (
          <button
            onClick={onAct}
            className="flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-xs font-bold text-accent-foreground uppercase tracking-wider hover:bg-accent/90 transition-colors flex-shrink-0 shadow-sm"
          >
            Act Now
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Row 2: Financial Decision Grid — The numbers that matter */}
      <div className="grid grid-cols-2 sm:grid-cols-4 border-t border-border/30">
        {/* Recommended Action + Cost */}
        <div className="px-4 py-3 border-b sm:border-b-0 sm:border-r border-border/30">
          <div className="flex items-center gap-1 mb-1">
            <Zap className="h-3 w-3 text-accent/60" />
            <span className="text-[9px] text-muted-foreground/60 uppercase tracking-[0.12em] font-mono">Recommended</span>
          </div>
          <p className="text-sm font-bold font-mono text-accent">{actionLabel}</p>
          {actionCost > 0 && (
            <p className="text-xs font-mono text-muted-foreground mt-0.5 tabular-nums">
              Cost: {formatCurrency(actionCost, { compact: true })}
              {actionCostCI && (
                <span className="text-[10px] text-muted-foreground/50 ml-1">
                  ({formatCurrencyRange(actionCostCI.lower, actionCostCI.upper, { compact: true })})
                </span>
              )}
            </p>
          )}
        </div>

        {/* You Save */}
        <div className="px-4 py-3 border-b sm:border-b-0 sm:border-r border-border/30">
          <div className="flex items-center gap-1 mb-1">
            <TrendingDown className="h-3 w-3 text-success/60" />
            <span className="text-[9px] text-muted-foreground/60 uppercase tracking-[0.12em] font-mono">You Save</span>
          </div>
          <p className={cn(
            'text-lg font-bold font-mono tabular-nums',
            savings > 0 ? 'text-success' : 'text-muted-foreground',
          )}>
            {savings > 0 ? formatCurrency(savings, { compact: true }) : '—'}
          </p>
        </div>

        {/* If You Do Nothing */}
        <div className="px-4 py-3 sm:border-r border-border/30">
          <div className="flex items-center gap-1 mb-1">
            <AlertTriangle className="h-3 w-3 text-destructive/50" />
            <span className="text-[9px] text-destructive/50 uppercase tracking-[0.12em] font-mono">If Nothing</span>
          </div>
          <p className={cn(
            'text-lg font-bold font-mono tabular-nums',
            inactionCost > 0 ? 'text-destructive/80' : 'text-muted-foreground',
          )}>
            {inactionCost > 0 ? formatCurrency(inactionCost, { compact: true }) : '—'}
          </p>
          {inactionCostCI && inactionCost > 0 && (
            <p className="text-[10px] font-mono text-destructive/40 mt-0.5 tabular-nums">
              {formatCurrencyRange(inactionCostCI.lower, inactionCostCI.upper, { compact: true })}
            </p>
          )}
          {decision.q7_inaction?.inaction_delay_days > 0 && (
            <p className="text-[10px] font-mono text-destructive/50 mt-0.5">
              +{decision.q7_inaction.inaction_delay_days}d delay
            </p>
          )}
        </div>

        {/* Confidence */}
        <div className="px-4 py-3">
          <div className="flex items-center gap-1 mb-1">
            <Shield className="h-3 w-3 text-muted-foreground/40" />
            <span className="text-[9px] text-muted-foreground/60 uppercase tracking-[0.12em] font-mono">Confidence</span>
          </div>
          <p className="text-lg font-bold font-mono tabular-nums text-foreground">
            {Math.round(confidence * 100)}%
          </p>
          <p className="text-[10px] font-mono text-muted-foreground/50 mt-0.5">
            {decision.q6_confidence?.overall_confidence ?? ''}
            {decision.q6_confidence?.confidence_factors?.length
              ? ` · ${decision.q6_confidence.confidence_factors.length} factors`
              : ''}
          </p>
        </div>
      </div>

      {/* Row 3: Worst case warning — only for CRITICAL/HIGH when pending */}
      {isPending && worstCase && (severity === 'CRITICAL' || severity === 'HIGH') && (
        <div className="px-4 py-2.5 border-t border-border/30 bg-destructive/[0.03]">
          <p className="text-[10px] text-destructive/60 font-mono leading-relaxed">
            <AlertTriangle className="h-3 w-3 inline mr-1.5 -mt-0.5" />
            <span className="font-bold">Worst case:</span> {worstCase}
          </p>
        </div>
      )}
    </motion.div>
  );
}
