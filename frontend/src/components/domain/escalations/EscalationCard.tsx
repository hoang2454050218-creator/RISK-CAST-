import { motion } from 'framer-motion';
import { Link } from 'react-router';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import {
  AlertTriangle,
  Clock,
  User,
  CheckCircle,
  Users,
  DollarSign,
  Eye,
  ArrowUpRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate } from '@/lib/formatters';
import type { Escalation } from './types';
import { priorityConfig, statusConfig } from './types';

export function EscalationCard({
  escalation,
  index,
  isDark,
}: {
  escalation: Escalation;
  index: number;
  isDark: boolean;
}) {
  const priority = priorityConfig[escalation.priority] ?? priorityConfig.NORMAL;
  const status = statusConfig[escalation.status] ?? statusConfig.PENDING;
  const slaDeadline = escalation.sla_deadline ? new Date(escalation.sla_deadline) : new Date();
  const isOverdue = slaDeadline < new Date();
  const isActive = escalation.status !== 'RESOLVED';
  const isCritical = escalation.priority === 'CRITICAL' && isActive;
  const PriorityIcon = priority.icon;

  return (
    <motion.div
      className={cn(
        'group relative overflow-hidden rounded-xl border shadow-level-1 transition-all duration-200',
        'bg-card',
        priority.border,
        isActive && priority.glow,
        isCritical && 'breathe-glow',
        'hover:shadow-level-2',
        priority.bgTint,
      )}
      whileHover={{ y: -1, transition: { duration: 0.2 } }}
    >
      {/* Left Accent Bar */}
      <div
        className={cn(
          'absolute inset-y-0 left-0 w-[3px] rounded-l-xl bg-gradient-to-b',
          priority.gradient,
        )}
      >
        {isCritical && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-b from-error to-destructive rounded-l-xl"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </div>

      {/* Terminal Corner Decorations (Dark mode only) */}
      {isDark && isCritical && (
        <>
          <div className="absolute top-0 right-0 w-2.5 h-2.5 border-r border-t border-error/30" />
          <div className="absolute bottom-0 right-0 w-2.5 h-2.5 border-r border-b border-error/30" />
        </>
      )}

      <div className="p-4 pl-5">
        <div className="flex items-start gap-4">
          {/* Left: Content */}
          <div className="flex-1 min-w-0 space-y-2.5">
            {/* Badges Row */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                className={cn(
                  'text-[11px] font-mono uppercase tracking-wide border gap-1.5 px-2 py-0.5',
                  priority.badge,
                )}
              >
                {isCritical && (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full rounded-full bg-current opacity-75 animate-ping" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
                  </span>
                )}
                <PriorityIcon className="h-3 w-3" />
                {priority.label}
              </Badge>
              <Badge
                className={cn(
                  'text-[11px] font-mono uppercase tracking-wide border gap-1.5 px-2 py-0.5',
                  status.badge,
                )}
              >
                <span className={cn('w-1.5 h-1.5 rounded-full', status.dotColor)} />
                {status.label}
              </Badge>
              {isOverdue && escalation.status !== 'RESOLVED' && (
                <motion.div
                  animate={{ scale: [1, 1.03, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  <Badge className="text-[11px] font-mono uppercase tracking-wide bg-error/15 text-error border border-error/40 gap-1.5 px-2 py-0.5">
                    <AlertTriangle className="h-3 w-3" />
                    SLA Breached
                  </Badge>
                </motion.div>
              )}
            </div>

            {/* Title & Reason */}
            <div>
              <h3 className="font-semibold text-sm text-foreground leading-snug">
                {escalation.title ?? 'Untitled Escalation'}
              </h3>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1 leading-relaxed">
                {escalation.reason ?? ''}
              </p>
            </div>

            {/* Financial Impact + Metadata Row */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              {/* Exposure - prominent */}
              <span className={cn(
                'inline-flex items-center gap-1.5 text-xs font-mono font-bold px-2 py-0.5 rounded-md',
                (escalation.exposure_usd ?? 0) >= 200000
                  ? 'bg-destructive/10 text-destructive border border-destructive/20'
                  : (escalation.exposure_usd ?? 0) >= 100000
                    ? 'bg-warning/10 text-warning border border-warning/20'
                    : 'bg-muted text-foreground border border-border/40',
              )}>
                <DollarSign className="h-3.5 w-3.5" />
                {formatCurrency(escalation.exposure_usd ?? 0, { compact: true })} at risk
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs font-mono text-foreground font-medium">
                <Users className="h-3.5 w-3.5 text-muted-foreground" />
                {escalation.customer ?? 'Unknown'}
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                <Clock className="h-3.5 w-3.5" />
                {formatDate(escalation.created_at ?? new Date().toISOString(), { relative: true })}
              </span>
              {escalation.assigned_to && (
                <span className="inline-flex items-center gap-1.5 text-xs font-mono text-info">
                  <User className="h-3.5 w-3.5" />
                  {escalation.assigned_to}
                </span>
              )}
            </div>
          </div>

          {/* Right: SLA + Action */}
          <div className="flex flex-col items-end gap-3 flex-shrink-0">
            {/* SLA Countdown Box */}
            <div
              className={cn(
                'px-3.5 py-2.5 rounded-lg border text-right min-w-[110px]',
                'bg-muted/50 border-border',
                isOverdue && isActive && 'bg-error/5 border-error/20',
              )}
            >
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-mono mb-1 flex items-center justify-end gap-1">
                <Clock className="h-3 w-3" />
                SLA
              </p>
              {escalation.status !== 'RESOLVED' ? (
                <CompactCountdown
                  deadline={slaDeadline}
                  className={cn(
                    'text-base font-bold font-mono tabular-nums tracking-tight',
                    isOverdue ? 'text-error' : 'text-foreground',
                  )}
                />
              ) : (
                <p className="text-sm text-success font-semibold font-mono flex items-center justify-end gap-1">
                  <CheckCircle className="h-3.5 w-3.5" />
                  Done
                </p>
              )}
            </div>

            {/* Review Button */}
            {escalation.status !== 'RESOLVED' && (
              <Link to={`/human-review/${escalation.id}`} className="w-full">
                <Button
                  size="sm"
                  className={cn(
                    'gap-1.5 h-9 w-full text-xs font-semibold font-mono tracking-wide transition-all duration-200',
                    escalation.priority === 'CRITICAL'
                      ? 'bg-destructive hover:bg-destructive/90 text-destructive-foreground shadow-sm'
                      : 'bg-accent hover:bg-accent-hover text-white shadow-sm',
                  )}
                >
                  <Eye className="h-3.5 w-3.5" />
                  REVIEW
                </Button>
              </Link>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
