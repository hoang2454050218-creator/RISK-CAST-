import { Badge } from '@/components/ui/badge';
import { AlertCircle, AlertTriangle, Clock, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Urgency } from '@/types/decision';

interface UrgencyConfig {
  icon: typeof AlertCircle;
  variant: 'immediate' | 'urgent' | 'soon' | 'watch';
  label: string;
  description: string;
}

const urgencyConfig: Record<Urgency, UrgencyConfig> = {
  IMMEDIATE: {
    icon: AlertCircle,
    variant: 'immediate',
    label: 'IMMEDIATE',
    description: 'Action required within hours',
  },
  URGENT: {
    icon: AlertTriangle,
    variant: 'urgent',
    label: 'URGENT',
    description: 'Action required within 24 hours',
  },
  SOON: {
    icon: Clock,
    variant: 'soon',
    label: 'SOON',
    description: 'Action required within 7 days',
  },
  WATCH: {
    icon: Eye,
    variant: 'watch',
    label: 'WATCH',
    description: 'Monitor situation',
  },
};

interface UrgencyBadgeProps {
  urgency: Urgency;
  showIcon?: boolean;
  showDescription?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animate?: boolean;
  className?: string;
}

export function UrgencyBadge({
  urgency,
  showIcon = true,
  showDescription = false,
  size = 'md',
  animate = true,
  className,
}: UrgencyBadgeProps) {
  const config = urgencyConfig[urgency];
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

  const shouldAnimate = animate && urgency === 'IMMEDIATE';

  return (
    <div className={cn('inline-flex flex-col gap-1', className)}>
      <Badge
        variant={config.variant}
        className={cn(
          'gap-1.5 font-semibold uppercase tracking-wide',
          sizeClasses[size],
          shouldAnimate && 'urgency-pulse',
        )}
      >
        {showIcon && <Icon className={iconSizes[size]} />}
        {config.label}
      </Badge>

      {showDescription && (
        <span className="text-xs text-muted-foreground">{config.description}</span>
      )}
    </div>
  );
}

/**
 * Get urgency level from hours until deadline
 */
export function getUrgencyFromHours(hours: number): Urgency {
  if (hours <= 6) return 'IMMEDIATE';
  if (hours <= 24) return 'URGENT';
  if (hours <= 168) return 'SOON'; // 7 days
  return 'WATCH';
}
