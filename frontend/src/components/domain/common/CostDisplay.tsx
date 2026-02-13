import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import type { ConfidenceInterval } from '@/types/decision';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * Calculate position of a value on the CI bar (0-100%)
 * Centers the point estimate at 50%
 */
function calculateCIPosition(value: number, pointEstimate: number): number {
  const range = pointEstimate * 0.5; // Assume range is ~50% of point estimate
  const minVal = pointEstimate - range;
  const maxVal = pointEstimate + range;
  const position = ((value - minVal) / (maxVal - minVal)) * 100;
  return Math.max(0, Math.min(100, position));
}

interface CostDisplayProps {
  /** Primary amount in USD */
  amount: number;
  /** 90% confidence interval */
  confidenceInterval?: ConfidenceInterval;
  /** Show change from previous value */
  delta?: number;
  /** Display size */
  size?: 'sm' | 'md' | 'lg' | 'xl';
  /** Label text above the amount */
  label?: string;
  /** Whether to show compact notation for large numbers */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function CostDisplay({
  amount,
  confidenceInterval,
  delta,
  size = 'md',
  label,
  compact = false,
  className,
}: CostDisplayProps) {
  const sizeClasses = {
    sm: {
      amount: 'text-lg',
      ci: 'text-xs',
      label: 'text-xs',
      delta: 'text-xs',
    },
    md: {
      amount: 'text-2xl',
      ci: 'text-sm',
      label: 'text-xs',
      delta: 'text-sm',
    },
    lg: {
      amount: 'text-3xl',
      ci: 'text-sm',
      label: 'text-sm',
      delta: 'text-sm',
    },
    xl: {
      amount: 'text-4xl',
      ci: 'text-base',
      label: 'text-sm',
      delta: 'text-base',
    },
  };

  const sizes = sizeClasses[size];

  // Determine delta state
  const deltaState =
    delta === undefined ? null : delta > 0 ? 'increase' : delta < 0 ? 'decrease' : 'unchanged';

  const deltaColors = {
    increase: 'text-severity-critical',
    decrease: 'text-severity-low',
    unchanged: 'text-muted-foreground',
  };

  const DeltaIcon =
    deltaState === 'increase' ? TrendingUp : deltaState === 'decrease' ? TrendingDown : Minus;

  return (
    <div className={cn('space-y-1', className)}>
      {/* Label */}
      {label && (
        <p className={cn('font-medium uppercase tracking-wide text-muted-foreground', sizes.label)}>
          {label}
        </p>
      )}

      {/* Main amount */}
      <p className={cn('font-mono font-semibold font-tabular text-primary', sizes.amount)}>
        {formatCurrency(amount, { compact })}
      </p>

      {/* Confidence interval - VISUAL + TEXT */}
      {confidenceInterval && (
        <div className="space-y-2">
          {/* Visual CI Bar */}
          <div
            className="relative h-2 w-full max-w-[240px] rounded-full bg-muted"
            aria-label={`Confidence interval: ${formatCurrency(confidenceInterval.lower)} to ${formatCurrency(confidenceInterval.upper)}`}
          >
            {/* CI Range Background */}
            <div
              className="absolute h-full rounded-full bg-gradient-to-r from-confidence-low/30 via-confidence-medium/50 to-confidence-low/30"
              style={{
                left: `${calculateCIPosition(confidenceInterval.lower, amount)}%`,
                right: `${100 - calculateCIPosition(confidenceInterval.upper, amount)}%`,
              }}
            />
            {/* Point Estimate Marker */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-4 w-1 rounded-full bg-primary shadow-sm"
              style={{
                left: '50%',
                transform: 'translate(-50%, -50%)',
              }}
            />
            {/* Lower Bound Marker */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-3 w-0.5 rounded-full bg-muted-foreground/50"
              style={{
                left: `${calculateCIPosition(confidenceInterval.lower, amount)}%`,
              }}
            />
            {/* Upper Bound Marker */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-3 w-0.5 rounded-full bg-muted-foreground/50"
              style={{
                left: `${calculateCIPosition(confidenceInterval.upper, amount)}%`,
              }}
            />
          </div>

          {/* CI Labels */}
          <div className="flex items-center justify-between max-w-[240px]">
            <span className={cn('font-mono font-tabular text-muted-foreground', sizes.ci)}>
              {formatCurrency(confidenceInterval.lower, { compact })}
            </span>
            <span className={cn('text-muted-foreground text-center', sizes.ci)}>
              {Math.round(confidenceInterval.confidence_level * 100)}% CI
            </span>
            <span className={cn('font-mono font-tabular text-muted-foreground', sizes.ci)}>
              {formatCurrency(confidenceInterval.upper, { compact })}
            </span>
          </div>
        </div>
      )}

      {/* Delta */}
      {deltaState && delta !== undefined && (
        <div
          className={cn(
            'flex items-center gap-1 font-medium',
            deltaColors[deltaState],
            sizes.delta,
          )}
        >
          <DeltaIcon className="h-3.5 w-3.5" />
          <span className="font-mono font-tabular">
            {delta > 0 ? '+' : ''}
            {formatCurrency(delta, { compact })}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Inline cost display for use within text
 */
interface InlineCostProps {
  amount: number;
  className?: string;
}

export function InlineCost({ amount, className }: InlineCostProps) {
  return (
    <span className={cn('font-mono font-semibold font-tabular', className)}>
      {formatCurrency(amount)}
    </span>
  );
}

/**
 * Cost comparison between two values
 */
interface CostComparisonProps {
  current: number;
  alternative: number;
  currentLabel?: string;
  alternativeLabel?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function CostComparison({
  current,
  alternative,
  currentLabel = 'Current',
  alternativeLabel = 'Alternative',
  size = 'md',
  className,
}: CostComparisonProps) {
  const savings = current - alternative;
  const isSavings = savings > 0;

  return (
    <div className={cn('space-y-3', className)}>
      <div className="grid grid-cols-2 gap-4">
        <CostDisplay amount={current} label={currentLabel} size={size} />
        <CostDisplay amount={alternative} label={alternativeLabel} size={size} />
      </div>

      <div
        className={cn(
          'flex items-center gap-2 rounded-lg px-3 py-2',
          isSavings ? 'bg-severity-low/10' : 'bg-severity-critical/10',
        )}
      >
        {isSavings ? (
          <TrendingDown className="h-4 w-4 text-severity-low" />
        ) : (
          <TrendingUp className="h-4 w-4 text-severity-critical" />
        )}
        <span
          className={cn('font-medium', isSavings ? 'text-severity-low' : 'text-severity-critical')}
        >
          {isSavings ? 'Save ' : 'Additional '}
          <span className="font-mono font-tabular">{formatCurrency(Math.abs(savings))}</span>
        </span>
      </div>
    </div>
  );
}
