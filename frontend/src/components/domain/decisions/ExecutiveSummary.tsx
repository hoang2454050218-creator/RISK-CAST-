/**
 * ExecutiveSummary — TL;DR card displayed ABOVE the 7 Questions.
 *
 * Must be readable in <5 seconds by an executive:
 *   Line 1: EVENT — what's happening
 *   Line 2: EXPOSURE — how much money at risk
 *   Line 3: ACTION — what to do + cost + savings
 *
 * Data is synthesized from the Decision object, NOT duplicated.
 */

import { motion } from 'framer-motion';
import { ArrowDown, Zap } from 'lucide-react';
import { UrgencyBadge } from '@/components/domain/common/UrgencyBadge';
import { SeverityBadge } from '@/components/domain/common/SeverityBadge';
import { ActionBadge } from '@/components/domain/common/ActionBadge';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import { AnimatedCurrency } from '@/components/ui/animated-number';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';
import { formatCurrency } from '@/lib/formatters';
import type { Decision } from '@/types/decision';

interface ExecutiveSummaryProps {
  decision: Decision;
  /** Ref callback so parent can scroll to Q5 */
  onJumpToRecommendation?: () => void;
  className?: string;
}

export function ExecutiveSummary({
  decision,
  onJumpToRecommendation,
  className,
}: ExecutiveSummaryProps) {
  const { q1_what, q2_when, q3_severity, q5_action, q7_inaction } = decision;

  // Compute savings: inaction cost - action cost
  const savings = q7_inaction.inaction_cost_usd - q5_action.estimated_cost_usd;
  const deadline = q2_when.decision_deadline || decision.expires_at;

  return (
    <motion.div
      className={cn(
        'relative overflow-hidden rounded-xl border',
        'bg-card',
        // Glow border in dark mode
        'border-border',
        'shadow-sm',
        className,
      )}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      {/* Subtle top accent */}
      <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-accent via-action-reroute to-accent" />

      {/* Dark mode corner glow */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

      <div className="p-5 sm:p-6">
        {/* Header row: badges + countdown */}
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              Executive Summary
            </span>
            <UrgencyBadge urgency={q2_when.urgency} size="sm" />
            <SeverityBadge severity={q3_severity.severity} size="sm" />
          </div>

          {deadline && (
            <div className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground flex-shrink-0">
              <span className="hidden sm:inline">Deadline:</span>
              <CompactCountdown
                deadline={new Date(deadline)}
                className="text-sm font-bold text-foreground"
              />
            </div>
          )}
        </div>

        {/* Line 1: EVENT */}
        <h2 className="text-lg sm:text-xl font-semibold text-foreground leading-snug mb-3">
          {q1_what.event_summary.length > 120
            ? q1_what.event_summary.slice(0, 120) + '...'
            : q1_what.event_summary}
        </h2>

        {/* Line 2: EXPOSURE */}
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
          <span className="text-2xl sm:text-3xl font-bold font-mono tabular-nums text-foreground">
            <AnimatedCurrency value={q3_severity.total_exposure_usd} />
          </span>
          <span className="text-sm text-muted-foreground">
            across {q3_severity.shipments_affected} shipment
            {q3_severity.shipments_affected !== 1 ? 's' : ''}
          </span>
          {q3_severity.expected_delay_days > 0 && (
            <>
              <span className="text-muted-foreground/40">|</span>
              <span className="text-sm text-warning font-medium">
                +{q3_severity.expected_delay_days} days delay
              </span>
            </>
          )}
        </div>

        {/* Line 3: ACTION */}
        <div
          className={cn(
            'flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3',
            'p-3 rounded-lg',
            'bg-success/5 border border-success/15',
          )}
        >
          <div className="flex items-center gap-2 flex-shrink-0">
            <Zap className="h-4 w-4 text-success" />
            <span className="text-xs font-mono text-success uppercase tracking-wider font-semibold">
              Recommended
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-sm">
            <ActionBadge action={q5_action.recommended_action} size="sm" />
            <span className="text-foreground font-medium">
              {q5_action.action_summary.length > 80
                ? q5_action.action_summary.slice(0, 80) + '...'
                : q5_action.action_summary}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground sm:ml-auto flex-shrink-0">
            <span>
              Cost:{' '}
              <span className="text-foreground font-semibold">
                {formatCurrency(q5_action.estimated_cost_usd)}
              </span>
            </span>
            {savings > 0 && (
              <>
                <span className="text-muted-foreground/40">|</span>
                <span className="text-success font-semibold">Saves {formatCurrency(savings)}</span>
              </>
            )}
          </div>
        </div>

        {/* Jump to recommendation link */}
        {onJumpToRecommendation && (
          <motion.button
            onClick={onJumpToRecommendation}
            className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-accent transition-colors font-mono"
            whileHover={{ y: 1 }}
          >
            View full analysis
            <ArrowDown className="h-3 w-3" />
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}
