import { Badge } from '@/components/ui/badge';
import { Flame, AlertTriangle, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Severity } from '@/types/decision';

interface SeverityConfig {
  icon: typeof Flame;
  variant: 'critical' | 'high' | 'medium' | 'low';
  label: string;
  threshold: string;
}

const severityConfig: Record<Severity, SeverityConfig> = {
  CRITICAL: {
    icon: Flame,
    variant: 'critical',
    label: 'CRITICAL',
    threshold: '>$100K',
  },
  HIGH: {
    icon: AlertTriangle,
    variant: 'high',
    label: 'HIGH',
    threshold: '$25K-$100K',
  },
  MEDIUM: {
    icon: AlertCircle,
    variant: 'medium',
    label: 'MEDIUM',
    threshold: '$5K-$25K',
  },
  LOW: {
    icon: CheckCircle,
    variant: 'low',
    label: 'LOW',
    threshold: '<$5K',
  },
};

interface SeverityBadgeProps {
  severity: Severity;
  showIcon?: boolean;
  showThreshold?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function SeverityBadge({
  severity,
  showIcon = true,
  showThreshold = false,
  size = 'md',
  className,
}: SeverityBadgeProps) {
  const config = severityConfig[severity];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-0.5',
    lg: 'text-sm px-3 py-1',
  };

  const iconSizes = {
    sm: 'h-3 w-3',
    md: 'h-3.5 w-3.5',
    lg: 'h-4 w-4',
  };

  return (
    <div className={cn('inline-flex flex-col gap-1', className)}>
      <Badge
        variant={config.variant}
        className={cn('gap-1.5 font-semibold uppercase tracking-wide', sizeClasses[size])}
      >
        {showIcon && <Icon className={iconSizes[size]} />}
        {config.label}
      </Badge>

      {showThreshold && <span className="text-xs text-muted-foreground">{config.threshold}</span>}
    </div>
  );
}

/**
 * Get severity level from USD exposure amount
 */
export function getSeverityFromAmount(amountUsd: number): Severity {
  if (amountUsd > 100_000) return 'CRITICAL';
  if (amountUsd > 25_000) return 'HIGH';
  if (amountUsd > 5_000) return 'MEDIUM';
  return 'LOW';
}

/**
 * Severity thresholds in USD
 */
export const SEVERITY_THRESHOLDS = {
  LOW: 5_000,
  MEDIUM: 25_000,
  HIGH: 100_000,
} as const;
