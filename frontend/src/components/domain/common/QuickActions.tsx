/**
 * QuickActions — Dashboard happy-path flow: Signal → Decision → Act
 *
 * Shows a visual pipeline with live badge counts guiding the user
 * through the core workflow.
 */

import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Radio, Brain, Zap, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';
import { useDecisionsList } from '@/hooks/useDecisions';
import { useSignalsList } from '@/hooks/useSignals';
import { useEscalationsList } from '@/hooks/useEscalations';

interface StepProps {
  icon: React.ReactNode;
  label: string;
  count: number;
  sublabel: string;
  href: string;
  highlight?: boolean;
}

function Step({ icon, label, count, sublabel, href, highlight }: StepProps) {
  return (
    <Link to={href} className="flex-1 min-w-0">
      <motion.div
        className={cn(
          'relative rounded-xl border p-4 transition-all cursor-pointer',
          'bg-card hover:bg-card-hover',
          highlight
            ? 'border-accent/30 shadow-sm'
            : 'border-border hover:border-border',
        )}
        whileHover={{ y: -2 }}
        transition={springs.snappy}
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-lg border',
              highlight ? 'bg-accent/10 border-accent/20 text-accent' : 'bg-muted border-border text-muted-foreground',
            )}
          >
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-foreground truncate">{label}</span>
              {count > 0 && (
                <span
                  className={cn(
                    'inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold',
                    highlight ? 'bg-accent/20 text-accent' : 'bg-muted text-muted-foreground',
                  )}
                >
                  {count}
                </span>
              )}
            </div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider truncate">{sublabel}</p>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}

function Arrow() {
  return (
    <div className="hidden sm:flex items-center px-1 text-muted-foreground/40">
      <ChevronRight className="h-4 w-4" />
    </div>
  );
}

export function QuickActions({ className }: { className?: string }) {
  const { data: decisions = [] } = useDecisionsList();
  const { data: signals = [] } = useSignalsList();
  const { data: escalations = [] } = useEscalationsList();

  const pendingDecisions = decisions.filter((d) => d.status === 'PENDING').length;
  const activeSignals = signals.filter((s) => s.status === 'ACTIVE' || s.status === 'CONFIRMED').length;
  const pendingEscalations = escalations.filter((e) => e.status === 'PENDING' || e.status === 'IN_REVIEW').length;

  return (
    <div className={cn('flex flex-col sm:flex-row items-stretch gap-2', className)}>
      <Step
        icon={<Radio className="h-5 w-5" />}
        label="Signals"
        count={activeSignals}
        sublabel={`${activeSignals} active today`}
        href="/signals"
        highlight={activeSignals > 0}
      />
      <Arrow />
      <Step
        icon={<Brain className="h-5 w-5" />}
        label="Decisions"
        count={pendingDecisions}
        sublabel={`${pendingDecisions} pending review`}
        href="/decisions"
        highlight={pendingDecisions > 0}
      />
      <Arrow />
      <Step
        icon={<Zap className="h-5 w-5" />}
        label="Actions"
        count={pendingEscalations}
        sublabel={`${pendingEscalations} need approval`}
        href="/human-review"
        highlight={pendingEscalations > 0}
      />
    </div>
  );
}
