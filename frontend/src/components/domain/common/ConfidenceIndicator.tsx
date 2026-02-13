import { cn } from '@/lib/utils';
import { formatPercentage } from '@/lib/formatters';
import type { ConfidenceLevel } from '@/types/decision';
import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';

interface ConfidenceConfig {
  icon: typeof ShieldCheck;
  color: string;
  bgColor: string;
  label: string;
}

const confidenceConfig: Record<ConfidenceLevel, ConfidenceConfig> = {
  HIGH: {
    icon: ShieldCheck,
    color: 'text-confidence-high',
    bgColor: 'bg-confidence-high/10',
    label: 'High Confidence',
  },
  MEDIUM: {
    icon: ShieldAlert,
    color: 'text-confidence-medium',
    bgColor: 'bg-confidence-medium/10',
    label: 'Medium Confidence',
  },
  LOW: {
    icon: ShieldQuestion,
    color: 'text-confidence-low',
    bgColor: 'bg-confidence-low/10',
    label: 'Low Confidence',
  },
};

interface ConfidenceIndicatorProps {
  level: ConfidenceLevel;
  score?: number; // 0-1
  showScore?: boolean;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'badge' | 'bar' | 'ring';
  className?: string;
}

export function ConfidenceIndicator({
  level,
  score,
  showScore = true,
  showLabel = false,
  size = 'md',
  variant = 'badge',
  className,
}: ConfidenceIndicatorProps) {
  const config = confidenceConfig[level];
  const Icon = config.icon;

  const sizeClasses = {
    sm: {
      container: 'gap-1.5 text-xs',
      icon: 'h-3.5 w-3.5',
      bar: 'h-1.5',
      ring: 'h-8 w-8',
    },
    md: {
      container: 'gap-2 text-sm',
      icon: 'h-4 w-4',
      bar: 'h-2',
      ring: 'h-12 w-12',
    },
    lg: {
      container: 'gap-2.5 text-base',
      icon: 'h-5 w-5',
      bar: 'h-2.5',
      ring: 'h-16 w-16',
    },
  };

  const sizes = sizeClasses[size];

  if (variant === 'bar') {
    const percentage = score !== undefined ? score * 100 : getDefaultScore(level) * 100;

    return (
      <div className={cn('space-y-1', className)}>
        <div className="flex items-center justify-between">
          {showLabel && <span className={cn('font-medium', config.color)}>{config.label}</span>}
          {showScore && score !== undefined && (
            <span className={cn('font-mono font-tabular', config.color)}>
              {formatPercentage(score)}
            </span>
          )}
        </div>
        <div className={cn('w-full rounded-full bg-muted', sizes.bar)}>
          <div
            className={cn('rounded-full transition-all duration-500', sizes.bar)}
            style={{
              width: `${percentage}%`,
              backgroundColor: `var(--color-confidence-${level.toLowerCase()})`,
            }}
          />
        </div>
      </div>
    );
  }

  if (variant === 'ring') {
    const percentage = score !== undefined ? score * 100 : getDefaultScore(level) * 100;
    const circumference = 2 * Math.PI * 45; // radius = 45
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div
        className={cn('relative inline-flex items-center justify-center', sizes.ring, className)}
      >
        <svg className="transform -rotate-90" viewBox="0 0 100 100">
          <circle
            className="text-muted"
            strokeWidth="8"
            stroke="currentColor"
            fill="transparent"
            r="45"
            cx="50"
            cy="50"
          />
          <circle
            className={config.color}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            stroke="currentColor"
            fill="transparent"
            r="45"
            cx="50"
            cy="50"
          />
        </svg>
        <span className={cn('absolute font-mono font-bold font-tabular', config.color)}>
          {Math.round(percentage)}%
        </span>
      </div>
    );
  }

  // Default: badge variant
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-md px-2.5 py-1',
        config.bgColor,
        sizes.container,
        className,
      )}
    >
      <Icon className={cn(sizes.icon, config.color)} />
      {showLabel && <span className={cn('font-medium', config.color)}>{config.label}</span>}
      {showScore && score !== undefined && (
        <span className={cn('font-mono font-tabular', config.color)}>
          {formatPercentage(score)}
        </span>
      )}
    </div>
  );
}

/**
 * Get confidence level from score
 */
export function getConfidenceLevelFromScore(score: number): ConfidenceLevel {
  if (score >= 0.8) return 'HIGH';
  if (score >= 0.6) return 'MEDIUM';
  return 'LOW';
}

function getDefaultScore(level: ConfidenceLevel): number {
  switch (level) {
    case 'HIGH':
      return 0.85;
    case 'MEDIUM':
      return 0.7;
    case 'LOW':
      return 0.45;
  }
}
