import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Clock, AlertTriangle, AlertCircle } from 'lucide-react';

interface CountdownTimerProps {
  /** Target deadline */
  deadline: Date | string;
  /** Label text */
  label?: string;
  /** Display size */
  size?: 'sm' | 'md' | 'lg';
  /** Show icon */
  showIcon?: boolean;
  /** Callback when timer reaches zero */
  onExpire?: () => void;
  /** Additional CSS classes */
  className?: string;
}

interface TimeLeft {
  totalSeconds: number;
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  isExpired: boolean;
}

export function CountdownTimer({
  deadline,
  label = 'Decision deadline',
  size = 'md',
  showIcon = true,
  onExpire,
  className,
}: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(() =>
    calculateTimeLeft(typeof deadline === 'string' ? new Date(deadline) : deadline),
  );

  useEffect(() => {
    const targetDate = typeof deadline === 'string' ? new Date(deadline) : deadline;

    const timer = setInterval(() => {
      const newTimeLeft = calculateTimeLeft(targetDate);
      setTimeLeft(newTimeLeft);

      if (newTimeLeft.isExpired && onExpire) {
        onExpire();
        clearInterval(timer);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [deadline, onExpire]);

  const sizeClasses = {
    sm: {
      container: 'gap-1.5',
      icon: 'h-3.5 w-3.5',
      time: 'text-sm',
      label: 'text-xs',
      unit: 'text-xs',
    },
    md: {
      container: 'gap-2',
      icon: 'h-4 w-4',
      time: 'text-lg',
      label: 'text-xs',
      unit: 'text-xs',
    },
    lg: {
      container: 'gap-2.5',
      icon: 'h-5 w-5',
      time: 'text-2xl',
      label: 'text-sm',
      unit: 'text-sm',
    },
  };

  const sizes = sizeClasses[size];

  // Determine urgency state
  const hoursLeft = timeLeft.totalSeconds / 3600;
  const urgencyState = timeLeft.isExpired
    ? 'expired'
    : hoursLeft < 1
      ? 'critical'
      : hoursLeft < 6
        ? 'urgent'
        : 'normal';

  const stateColors = {
    expired: 'text-muted-foreground',
    critical: 'text-urgency-immediate',
    urgent: 'text-urgency-urgent',
    normal: 'text-foreground',
  };

  const stateBgColors = {
    expired: 'bg-muted',
    critical: 'bg-urgency-immediate/10',
    urgent: 'bg-urgency-urgent/10',
    normal: 'bg-muted/50',
  };

  const Icon =
    urgencyState === 'critical' ? AlertCircle : urgencyState === 'urgent' ? AlertTriangle : Clock;

  // Generate accessible time description
  const getAriaLabel = () => {
    if (timeLeft.isExpired) return 'Countdown expired';
    const parts = [];
    if (timeLeft.days > 0) parts.push(`${timeLeft.days} days`);
    if (timeLeft.hours > 0) parts.push(`${timeLeft.hours} hours`);
    if (timeLeft.minutes > 0) parts.push(`${timeLeft.minutes} minutes`);
    if (timeLeft.seconds > 0) parts.push(`${timeLeft.seconds} seconds`);
    return `${label}: ${parts.join(', ')} remaining`;
  };

  if (timeLeft.isExpired) {
    return (
      <div
        className={cn(
          'inline-flex items-center rounded-lg px-3 py-2',
          stateBgColors.expired,
          sizes.container,
          className,
        )}
        role="timer"
        aria-live="polite"
        aria-label="Countdown expired"
      >
        <Clock className={cn(sizes.icon, stateColors.expired)} aria-hidden="true" />
        <span className={cn('font-medium', stateColors.expired)}>Expired</span>
      </div>
    );
  }

  return (
    <div className={cn('space-y-1', className)}>
      {label && (
        <p
          id={`countdown-label-${size}`}
          className={cn('font-medium uppercase tracking-wide text-muted-foreground', sizes.label)}
        >
          {label}
        </p>
      )}

      <div
        className={cn(
          'inline-flex items-center rounded-lg px-3 py-2',
          stateBgColors[urgencyState],
          sizes.container,
          urgencyState === 'critical' && 'urgency-pulse', // Use custom animation
        )}
        role="timer"
        aria-live={urgencyState === 'critical' ? 'assertive' : 'polite'}
        aria-label={getAriaLabel()}
        aria-atomic="true"
      >
        {showIcon && (
          <Icon className={cn(sizes.icon, stateColors[urgencyState])} aria-hidden="true" />
        )}

        <div
          className={cn(
            'font-mono font-semibold font-tabular',
            sizes.time,
            stateColors[urgencyState],
          )}
          aria-hidden="true" // Visual display is duplicate of aria-label
        >
          {timeLeft.days > 0 && (
            <>
              <span>{timeLeft.days}</span>
              <span className={cn('font-normal', sizes.unit)}>d </span>
            </>
          )}
          <span>{String(timeLeft.hours).padStart(2, '0')}</span>
          <span className={cn('font-normal', sizes.unit)}>h </span>
          <span>{String(timeLeft.minutes).padStart(2, '0')}</span>
          <span className={cn('font-normal', sizes.unit)}>m </span>
          <span>{String(timeLeft.seconds).padStart(2, '0')}</span>
          <span className={cn('font-normal', sizes.unit)}>s</span>
        </div>
      </div>

      {/* Screen reader only announcement for critical time */}
      {urgencyState === 'critical' && (
        <span className="sr-only" aria-live="assertive">
          Warning: Less than 1 hour remaining to make a decision
        </span>
      )}
    </div>
  );
}

function calculateTimeLeft(deadline: Date): TimeLeft {
  const now = new Date();
  const diffMs = deadline.getTime() - now.getTime();

  if (diffMs <= 0) {
    return {
      totalSeconds: 0,
      days: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
      isExpired: true,
    };
  }

  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return {
    totalSeconds,
    days,
    hours,
    minutes,
    seconds,
    isExpired: false,
  };
}

/**
 * Compact countdown for use in cards/lists
 */
interface CompactCountdownProps {
  deadline: Date | string;
  className?: string;
}

export function CompactCountdown({ deadline, className }: CompactCountdownProps) {
  const [timeLeft, setTimeLeft] = useState<TimeLeft>(() =>
    calculateTimeLeft(typeof deadline === 'string' ? new Date(deadline) : deadline),
  );

  useEffect(() => {
    const targetDate = typeof deadline === 'string' ? new Date(deadline) : deadline;
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft(targetDate));
    }, 1000);
    return () => clearInterval(timer);
  }, [deadline]);

  if (timeLeft.isExpired) {
    return <span className={cn('text-muted-foreground', className)}>Expired</span>;
  }

  const hoursLeft = timeLeft.totalSeconds / 3600;
  const color =
    hoursLeft < 1
      ? 'text-urgency-immediate'
      : hoursLeft < 6
        ? 'text-urgency-urgent'
        : 'text-foreground';

  return (
    <span className={cn('font-mono font-tabular', color, className)}>
      {timeLeft.days > 0 && `${timeLeft.days}d `}
      {String(timeLeft.hours).padStart(2, '0')}:{String(timeLeft.minutes).padStart(2, '0')}:
      {String(timeLeft.seconds).padStart(2, '0')}
    </span>
  );
}
