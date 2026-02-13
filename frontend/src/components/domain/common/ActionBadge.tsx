import { Badge } from '@/components/ui/badge';
import { Navigation, Clock, Shield, TrendingUp, Eye, CircleSlash } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ActionType } from '@/types/decision';

interface ActionConfig {
  icon: typeof Navigation;
  variant: 'reroute' | 'delay' | 'insure' | 'monitor' | 'nothing';
  label: string;
  description: string;
}

const actionConfig: Record<ActionType, ActionConfig> = {
  REROUTE: {
    icon: Navigation,
    variant: 'reroute',
    label: 'REROUTE',
    description: 'Change shipping route',
  },
  DELAY: {
    icon: Clock,
    variant: 'delay',
    label: 'DELAY',
    description: 'Postpone shipment',
  },
  INSURE: {
    icon: Shield,
    variant: 'insure',
    label: 'INSURE',
    description: 'Purchase insurance coverage',
  },
  HEDGE: {
    icon: TrendingUp,
    variant: 'reroute', // Using reroute color for hedge
    label: 'HEDGE',
    description: 'Financial hedging',
  },
  MONITOR: {
    icon: Eye,
    variant: 'monitor',
    label: 'MONITOR',
    description: 'Watch and wait',
  },
  DO_NOTHING: {
    icon: CircleSlash,
    variant: 'nothing',
    label: 'NO ACTION',
    description: 'Accept current risk',
  },
};

interface ActionBadgeProps {
  action: ActionType;
  showIcon?: boolean;
  showDescription?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ActionBadge({
  action,
  showIcon = true,
  showDescription = false,
  size = 'md',
  className,
}: ActionBadgeProps) {
  const config = actionConfig[action];
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

      {showDescription && (
        <span className="text-xs text-muted-foreground">{config.description}</span>
      )}
    </div>
  );
}

/**
 * Get action icon component
 */
export function getActionIcon(action: ActionType) {
  return actionConfig[action].icon;
}

/**
 * Get action color class
 */
export function getActionColorClass(action: ActionType): string {
  const colorMap: Record<ActionType, string> = {
    REROUTE: 'text-action-reroute',
    DELAY: 'text-action-delay',
    INSURE: 'text-action-insure',
    HEDGE: 'text-action-reroute',
    MONITOR: 'text-action-monitor',
    DO_NOTHING: 'text-action-nothing',
  };
  return colorMap[action];
}
