import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'circular' | 'rectangular' | 'text';
  width?: string | number;
  height?: string | number;
  animation?: 'shimmer' | 'pulse' | 'none';
}

/**
 * Premium skeleton loading component with shimmer animation
 */
const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  (
    { className, variant = 'default', width, height, animation = 'shimmer', style, ...props },
    ref,
  ) => {
    const variantClasses = {
      default: 'rounded-md',
      circular: 'rounded-full',
      rectangular: 'rounded-none',
      text: 'rounded h-4',
    };

    const shimmerAnimation =
      animation === 'shimmer'
        ? {
            backgroundImage:
              'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.4) 50%, transparent 100%)',
            backgroundSize: '200% 100%',
            animation: 'shimmer 1.5s ease-in-out infinite',
          }
        : {};

    return (
      <div
        ref={ref}
        role="status"
        aria-label="Loading"
        aria-busy="true"
        className={cn(
          'bg-muted relative overflow-hidden',
          variantClasses[variant],
          animation === 'pulse' && 'animate-pulse',
          className,
        )}
        style={{
          width,
          height,
          ...shimmerAnimation,
          ...style,
        }}
        {...props}
      />
    );
  },
);
Skeleton.displayName = 'Skeleton';

/**
 * Animated skeleton with Framer Motion
 */
const AnimatedSkeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, width, height, style, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={cn('bg-muted rounded-md relative overflow-hidden', className)}
        style={{ width, height, ...style }}
        initial={{ opacity: 0.5 }}
        animate={{ opacity: [0.5, 0.8, 0.5] }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        {...props}
      >
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
          animate={{ x: ['-100%', '100%'] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'linear',
          }}
        />
      </motion.div>
    );
  },
);
AnimatedSkeleton.displayName = 'AnimatedSkeleton';

/**
 * Skeleton text line
 */
interface SkeletonTextProps {
  lines?: number;
  className?: string;
  lastLineWidth?: string;
}

function SkeletonText({ lines = 3, className, lastLineWidth = '70%' }: SkeletonTextProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          style={{
            width: i === lines - 1 ? lastLineWidth : '100%',
          }}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton avatar
 */
interface SkeletonAvatarProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

function SkeletonAvatar({ size = 'md', className }: SkeletonAvatarProps) {
  const sizes = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  };

  return <Skeleton variant="circular" className={cn(sizes[size], className)} />;
}

/**
 * Skeleton card for loading states
 */
interface SkeletonCardProps {
  showHeader?: boolean;
  showFooter?: boolean;
  lines?: number;
  className?: string;
}

function SkeletonCard({
  showHeader = true,
  showFooter = false,
  lines = 3,
  className,
}: SkeletonCardProps) {
  return (
    <div className={cn('bg-card rounded-lg border border-border p-6 space-y-4', className)}>
      {showHeader && (
        <div className="flex items-center gap-4">
          <SkeletonAvatar />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      )}

      <SkeletonText lines={lines} />

      {showFooter && (
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-9 w-20" />
        </div>
      )}
    </div>
  );
}

/**
 * Skeleton table row
 */
interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  className?: string;
}

function SkeletonTable({ rows = 5, columns = 4, className }: SkeletonTableProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              className="h-4 flex-1"
              style={{
                width: colIndex === 0 ? '30%' : '100%',
              }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton for data value display (Bloomberg style)
 */
interface SkeletonDataValueProps {
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

function SkeletonDataValue({ size = 'md', showLabel = true, className }: SkeletonDataValueProps) {
  const sizes = {
    sm: { value: 'h-6 w-20', label: 'h-3 w-12' },
    md: { value: 'h-8 w-28', label: 'h-4 w-16' },
    lg: { value: 'h-10 w-36', label: 'h-4 w-20' },
  };

  return (
    <div className={cn('space-y-1', className)}>
      {showLabel && <Skeleton className={sizes[size].label} />}
      <Skeleton className={sizes[size].value} />
    </div>
  );
}

/**
 * Skeleton for 7 Questions decision view
 */
function SkeletonDecisionView({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-24" />
      </div>

      {/* Q1-Q7 Cards */}
      {Array.from({ length: 7 }).map((_, i) => (
        <SkeletonCard key={i} showHeader={false} lines={2 + (i % 2)} />
      ))}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4">
        <Skeleton className="h-12 flex-1" />
        <Skeleton className="h-12 w-32" />
        <Skeleton className="h-12 w-32" />
      </div>
    </div>
  );
}

/**
 * Skeleton for chart
 */
function SkeletonChart({ className }: { className?: string }) {
  return (
    <div className={cn('bg-card rounded-lg border border-border p-6', className)}>
      <Skeleton className="h-5 w-32 mb-4" />
      <div className="relative h-48">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-12 flex flex-col justify-between py-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-3 w-8" />
          ))}
        </div>

        {/* Chart area */}
        <div className="ml-14 h-full flex items-end gap-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={i}
              className="flex-1"
              style={{ height: `${30 + ((i * 37 + 13) % 60)}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Page-specific skeletons ──────────────────────────────

/**
 * Dashboard page skeleton: 4 stat cards + urgent list + chokepoint
 */
function SkeletonDashboard({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Stat cards row */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg border border-border p-5 space-y-3">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-8" variant="circular" />
            </div>
            <Skeleton className="h-8 w-28" />
            <Skeleton className="h-3 w-24" />
          </div>
        ))}
      </div>

      {/* Two-column: urgent list + chokepoint */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-card rounded-lg border border-border p-5 space-y-3">
          <Skeleton className="h-5 w-32" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-2">
              <Skeleton className="h-6 w-6" variant="circular" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
        <SkeletonChart />
      </div>
    </div>
  );
}

/**
 * Decisions list page skeleton: filter bar + card grid
 */
function SkeletonDecisionsList({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-28" />
        <div className="ml-auto">
          <Skeleton className="h-8 w-20" />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg border border-border p-4 space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
      </div>

      {/* Decision cards grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} showHeader lines={2} showFooter />
        ))}
      </div>
    </div>
  );
}

/**
 * Signals list page skeleton: filter bar + signal cards
 */
function SkeletonSignalsList({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <Skeleton className="h-8 w-28" />
        <Skeleton className="h-8 w-28" />
        <div className="ml-auto">
          <Skeleton className="h-8 w-20" />
        </div>
      </div>

      {/* Signal cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <SkeletonCard key={i} showHeader lines={2} />
        ))}
      </div>
    </div>
  );
}

/**
 * Human review page skeleton: alert + stat cards + escalation cards
 */
function SkeletonHumanReview({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {/* Alert banner */}
      <Skeleton className="h-14 w-full rounded-lg" />

      {/* Stats row */}
      <div className="grid gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg border border-border p-4 space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-7 w-12" />
          </div>
        ))}
      </div>

      {/* Escalation cards */}
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonCard key={i} showHeader lines={2} showFooter />
        ))}
      </div>
    </div>
  );
}

export {
  Skeleton,
  AnimatedSkeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonTable,
  SkeletonDataValue,
  SkeletonDecisionView,
  SkeletonChart,
  SkeletonDashboard,
  SkeletonDecisionsList,
  SkeletonSignalsList,
  SkeletonHumanReview,
};
