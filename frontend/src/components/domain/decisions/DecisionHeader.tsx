import { Badge } from '@/components/ui/badge';
import { UrgencyBadge } from '@/components/domain/common/UrgencyBadge';
import { SeverityBadge } from '@/components/domain/common/SeverityBadge';
import { CompactCountdown } from '@/components/domain/common/CountdownTimer';
import { Hash, Building, Calendar, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/formatters';
import type { Decision, DecisionStatus } from '@/types/decision';

interface DecisionHeaderProps {
  decision: Decision;
  showNavigation?: boolean;
  onBack?: () => void;
  className?: string;
}

export const statusConfig: Record<
  DecisionStatus,
  { variant: 'pending' | 'acknowledged' | 'overridden' | 'expired' | 'escalated'; label: string }
> = {
  PENDING: { variant: 'pending', label: 'Pending' },
  ACKNOWLEDGED: { variant: 'acknowledged', label: 'Acknowledged' },
  OVERRIDDEN: { variant: 'overridden', label: 'Overridden' },
  EXPIRED: { variant: 'expired', label: 'Expired' },
  ESCALATED: { variant: 'escalated', label: 'Escalated' },
};

export function DecisionHeader({
  decision,
  showNavigation = false,
  onBack,
  className,
}: DecisionHeaderProps) {
  const status = statusConfig[decision.status];
  const deadline = new Date(decision.expires_at);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Breadcrumb Navigation */}
      {showNavigation && (
        <nav className="flex items-center gap-2 text-sm text-muted-foreground">
          <button onClick={onBack} className="hover:text-foreground transition-colors">
            Decisions
          </button>
          <ChevronRight className="h-4 w-4" />
          <span className="font-medium text-foreground font-mono">
            {decision.decision_id.slice(0, 8)}...
          </span>
        </nav>
      )}

      {/* Main Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        {/* Left: Title and Meta */}
        <div className="space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <UrgencyBadge urgency={decision.q2_when.urgency} size="lg" />
            <SeverityBadge severity={decision.q3_severity.severity} size="lg" />
            <Badge variant={status.variant}>{status.label}</Badge>
          </div>

          <h1 className="text-xl font-semibold text-primary sm:text-2xl">
            {decision.q1_what.event_summary.length > 80
              ? decision.q1_what.event_summary.slice(0, 80) + '...'
              : decision.q1_what.event_summary}
          </h1>

          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Hash className="h-3.5 w-3.5" />
              <span className="font-mono">{decision.decision_id.slice(0, 12)}</span>
            </div>

            <div className="flex items-center gap-1.5">
              <Building className="h-3.5 w-3.5" />
              <span>{decision.customer_id}</span>
            </div>

            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              <span>{formatDate(decision.created_at, { includeTime: true })}</span>
            </div>
          </div>
        </div>

        {/* Right: Countdown */}
        <div className="flex flex-col items-end gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Expires in
          </p>
          <div className="text-2xl font-mono font-semibold font-tabular">
            <CompactCountdown deadline={deadline} />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact header for card/list views
 */
interface CompactDecisionHeaderProps {
  decision: Decision;
  className?: string;
}

export function CompactDecisionHeader({ decision, className }: CompactDecisionHeaderProps) {
  const status = statusConfig[decision.status];

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2 flex-wrap">
        <UrgencyBadge urgency={decision.q2_when.urgency} size="sm" />
        <SeverityBadge severity={decision.q3_severity.severity} size="sm" />
        <Badge variant={status.variant} className="text-[10px]">
          {status.label}
        </Badge>
      </div>

      <p className="font-medium text-sm line-clamp-2">{decision.q1_what.event_summary}</p>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-mono">{decision.decision_id.slice(0, 8)}</span>
        <CompactCountdown deadline={decision.expires_at} className="text-xs" />
      </div>
    </div>
  );
}
