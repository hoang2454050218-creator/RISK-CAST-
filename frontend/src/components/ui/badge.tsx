import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

// Variants that show a colored dot indicator automatically
const DOT_VARIANTS = new Set([
  'immediate', 'urgent', 'soon', 'watch',
  'critical', 'high', 'medium', 'low',
  'pending', 'acknowledged', 'overridden', 'escalated',
]);

// Map variant → dot color class (uses same CSS-variable tokens)
const DOT_COLORS: Record<string, string> = {
  immediate: 'bg-urgency-immediate',
  urgent: 'bg-urgency-urgent',
  soon: 'bg-urgency-soon',
  watch: 'bg-urgency-watch',
  critical: 'bg-severity-critical',
  high: 'bg-severity-high',
  medium: 'bg-severity-medium',
  low: 'bg-severity-low',
  pending: 'bg-warning',
  acknowledged: 'bg-success',
  overridden: 'bg-action-reroute',
  escalated: 'bg-destructive',
};

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-border bg-muted text-muted-foreground',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        outline: 'text-foreground border-border',
        success: 'border-success/12 bg-success/5 text-success',
        warning: 'border-warning/12 bg-warning/5 text-warning',
        info: 'border-info/12 bg-info/5 text-info',

        // Premium variant
        premium:
          'border-purple-500/15 bg-gradient-to-r from-purple-500/5 to-blue-500/5 text-action-reroute',

        // Urgency variants — ultra-subtle: thin border + barely visible bg + muted text
        immediate:
          'border-urgency-immediate/12 bg-urgency-immediate/5 text-urgency-immediate font-semibold',
        urgent: 'border-urgency-urgent/12 bg-urgency-urgent/5 text-urgency-urgent font-semibold',
        soon: 'border-urgency-soon/12 bg-urgency-soon/5 text-urgency-soon',
        watch: 'border-urgency-watch/12 bg-urgency-watch/5 text-urgency-watch',

        // Severity variants — ultra-subtle
        critical:
          'border-severity-critical/12 bg-severity-critical/5 text-severity-critical font-semibold',
        high: 'border-severity-high/12 bg-severity-high/5 text-severity-high',
        medium: 'border-severity-medium/12 bg-severity-medium/5 text-severity-medium',
        low: 'border-severity-low/12 bg-severity-low/5 text-severity-low',

        // Confidence variants
        'confidence-high': 'border-confidence-high/12 bg-confidence-high/5 text-confidence-high',
        'confidence-medium':
          'border-confidence-medium/12 bg-confidence-medium/5 text-confidence-medium',
        'confidence-low': 'border-confidence-low/12 bg-confidence-low/5 text-confidence-low',

        // Action variants
        reroute: 'border-action-reroute/12 bg-action-reroute/5 text-action-reroute',
        delay: 'border-action-delay/12 bg-action-delay/5 text-action-delay',
        insure: 'border-action-insure/12 bg-action-insure/5 text-action-insure',
        monitor: 'border-action-monitor/12 bg-action-monitor/5 text-action-monitor',
        nothing: 'border-action-nothing/12 bg-action-nothing/5 text-action-nothing',

        // Status variants
        pending: 'border-warning/12 bg-warning/5 text-warning',
        acknowledged: 'border-success/12 bg-success/5 text-success',
        overridden: 'border-purple-500/12 bg-purple-500/5 text-action-reroute',
        expired: 'border-muted-foreground/12 bg-muted text-muted-foreground',
        escalated: 'border-destructive/12 bg-destructive/5 text-destructive',
      },
      size: {
        default: 'px-2 py-0.5 text-[10px]',
        sm: 'px-1.5 py-0.5 text-[9px]',
        lg: 'px-2.5 py-1 text-xs',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {
  pulse?: boolean;
  icon?: React.ReactNode;
}

function Badge({
  className,
  variant,
  size,
  pulse = false,
  icon,
  children,
  ...props
}: BadgeProps) {
  const isUrgent = variant === 'immediate' || variant === 'critical';
  const shouldPulse = pulse || isUrgent;
  const showDot = variant && DOT_VARIANTS.has(variant);
  const dotColor = variant ? DOT_COLORS[variant] : undefined;

  return (
    <div
      className={cn(
        badgeVariants({ variant, size }),
        'uppercase tracking-wider font-mono',
        shouldPulse && 'animate-pulse',
        className,
      )}
      {...props}
    >
      {icon && <span className="-ml-0.5">{icon}</span>}
      {!icon && showDot && dotColor && (
        <span className={cn('h-1.5 w-1.5 rounded-full shrink-0', dotColor)} />
      )}
      {children}
    </div>
  );
}

// Animated Badge with entrance animation
interface AnimatedBadgeProps extends BadgeProps {
  delay?: number;
}

function AnimatedBadge({ delay = 0, ...props }: AnimatedBadgeProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ ...springs.bouncy, delay }}
    >
      <Badge {...props} />
    </motion.div>
  );
}

// Count Badge with animation
interface CountBadgeProps extends Omit<BadgeProps, 'children'> {
  count: number;
  max?: number;
  showZero?: boolean;
}

function CountBadge({
  count,
  max = 99,
  showZero = false,
  variant = 'destructive',
  ...props
}: CountBadgeProps) {
  if (count === 0 && !showZero) return null;

  const displayCount = count > max ? `${max}+` : count.toString();

  return (
    <motion.div
      key={count}
      initial={{ scale: 0.5 }}
      animate={{ scale: 1 }}
      transition={springs.bouncy}
    >
      <Badge variant={variant} size="sm" className="min-w-[1.25rem] justify-center" {...props}>
        {displayCount}
      </Badge>
    </motion.div>
  );
}

// Dot Badge (no text, just a dot indicator)
interface DotBadgeProps {
  color?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
  className?: string;
}

function DotBadge({ color = 'default', size = 'md', pulse = false, className }: DotBadgeProps) {
  const colorClasses = {
    default: 'bg-muted-foreground',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error',
    info: 'bg-info',
  };

  const sizeClasses = {
    sm: 'h-1.5 w-1.5',
    md: 'h-2 w-2',
    lg: 'h-2.5 w-2.5',
  };

  return (
    <span
      className={cn(
        'inline-block rounded-full',
        colorClasses[color],
        sizeClasses[size],
        pulse && 'animate-pulse',
        className,
      )}
    />
  );
}

// Status Dot with label
interface StatusDotProps {
  status: 'online' | 'offline' | 'busy' | 'away';
  showLabel?: boolean;
  className?: string;
}

function StatusDot({ status, showLabel = false, className }: StatusDotProps) {
  const config = {
    online: { color: 'success' as const, label: 'Online' },
    offline: { color: 'default' as const, label: 'Offline' },
    busy: { color: 'error' as const, label: 'Busy' },
    away: { color: 'warning' as const, label: 'Away' },
  };

  const { color, label } = config[status];

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <DotBadge color={color} pulse={status === 'online'} />
      {showLabel && <span className="text-xs text-muted-foreground">{label}</span>}
    </span>
  );
}

export { Badge, AnimatedBadge, CountBadge, DotBadge, StatusDot, badgeVariants };
