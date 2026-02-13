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
  'inline-flex items-center gap-1.5 rounded-full border text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-border/60 bg-muted/80 text-muted-foreground',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        outline: 'text-foreground border-border/80',
        success: 'border-success/10 bg-success/5 text-success',
        warning: 'border-warning/10 bg-warning/5 text-warning',
        info: 'border-info/10 bg-info/5 text-info',

        // Premium variant
        premium:
          'border-action-reroute/12 bg-gradient-to-r from-action-reroute/5 to-accent/5 text-action-reroute',

        // Urgency variants — PRIMARY prominence: these badges STAND OUT
        immediate:
          'border-urgency-immediate/20 bg-urgency-immediate/8 text-urgency-immediate font-semibold shadow-sm',
        urgent: 'border-urgency-urgent/18 bg-urgency-urgent/6 text-urgency-urgent font-semibold',
        soon: 'border-urgency-soon/10 bg-urgency-soon/4 text-urgency-soon',
        watch: 'border-urgency-watch/8 bg-urgency-watch/3 text-urgency-watch',

        // Severity variants — scaled visual weight (critical prominent, low subtle)
        critical:
          'border-severity-critical/20 bg-severity-critical/8 text-severity-critical font-semibold shadow-sm',
        high: 'border-severity-high/15 bg-severity-high/5 text-severity-high',
        medium: 'border-severity-medium/8 bg-severity-medium/4 text-severity-medium',
        low: 'border-severity-low/6 bg-severity-low/3 text-severity-low opacity-80',

        // Confidence variants — informational: LOW prominence
        'confidence-high': 'border-confidence-high/8 bg-confidence-high/4 text-confidence-high',
        'confidence-medium':
          'border-confidence-medium/8 bg-confidence-medium/4 text-confidence-medium',
        'confidence-low': 'border-confidence-low/8 bg-confidence-low/4 text-confidence-low',

        // Action variants — informational: LOW prominence
        reroute: 'border-action-reroute/8 bg-action-reroute/4 text-action-reroute',
        delay: 'border-action-delay/8 bg-action-delay/4 text-action-delay',
        insure: 'border-action-insure/8 bg-action-insure/4 text-action-insure',
        monitor: 'border-action-monitor/8 bg-action-monitor/4 text-action-monitor',
        nothing: 'border-action-nothing/8 bg-action-nothing/4 text-action-nothing',

        // Status variants — MEDIUM prominence: outlined style
        pending: 'border-warning/15 bg-warning/4 text-warning',
        acknowledged: 'border-success/12 bg-success/4 text-success',
        overridden: 'border-action-reroute/12 bg-action-reroute/4 text-action-reroute',
        expired: 'border-muted-foreground/8 bg-muted/50 text-muted-foreground opacity-75',
        escalated: 'border-destructive/15 bg-destructive/5 text-destructive font-semibold',
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
