import * as React from 'react';
import { motion, useTransform, useMotionValue, animate } from 'framer-motion';
import { cn } from '@/lib/utils';

// ============================================
// Animated Number Component
// Bloomberg-style counting animation
// ============================================

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  delay?: number;
  className?: string;
  formatOptions?: Intl.NumberFormatOptions;
  locale?: string;
  prefix?: string;
  suffix?: string;
  showSign?: boolean;
  highlightChange?: boolean;
  onAnimationComplete?: () => void;
}

/**
 * Animated number with smooth counting effect
 * Ideal for financial data displays
 */
export function AnimatedNumber({
  value: rawValue,
  duration = 0.8,
  delay = 0,
  className,
  formatOptions = {},
  locale = 'en-US',
  prefix = '',
  suffix = '',
  showSign = false,
  highlightChange = false,
  onAnimationComplete,
}: AnimatedNumberProps) {
  // Guard against NaN / undefined — display dash instead of broken number
  const value = rawValue == null || isNaN(rawValue) ? 0 : rawValue;
  const isFallback = rawValue == null || isNaN(rawValue);

  const [displayValue, setDisplayValue] = React.useState(value);
  const [isAnimating, setIsAnimating] = React.useState(false);
  const [changeDirection, setChangeDirection] = React.useState<'up' | 'down' | null>(null);
  const prevValue = React.useRef(value);

  React.useEffect(() => {
    if (prevValue.current !== value) {
      setChangeDirection(value > prevValue.current ? 'up' : 'down');
      setIsAnimating(true);

      const controls = animate(prevValue.current, value, {
        duration,
        delay,
        ease: [0.16, 1, 0.3, 1], // ease-out-expo
        onUpdate: (latest) => setDisplayValue(latest),
        onComplete: () => {
          setIsAnimating(false);
          setTimeout(() => setChangeDirection(null), 500);
          onAnimationComplete?.();
        },
      });

      prevValue.current = value;

      return () => controls.stop();
    }
  }, [value, duration, delay, onAnimationComplete]);

  const formatter = React.useMemo(() => {
    return new Intl.NumberFormat(locale, formatOptions);
  }, [locale, formatOptions]);

  const formattedValue = isFallback ? '—' : formatter.format(displayValue);
  const sign = !isFallback && showSign && value > 0 ? '+' : '';

  return (
    <span
      aria-live="polite"
      aria-atomic="true"
      className={cn(
        'font-mono font-tabular inline-flex items-baseline transition-colors duration-300',
        highlightChange && changeDirection === 'up' && 'text-success',
        highlightChange && changeDirection === 'down' && 'text-error',
        isAnimating && 'data-pulse',
        className,
      )}
    >
      {prefix}
      {sign}
      {formattedValue}
      {suffix}
    </span>
  );
}

// ============================================
// Animated Currency Component
// ============================================

interface AnimatedCurrencyProps extends Omit<AnimatedNumberProps, 'formatOptions' | 'prefix'> {
  currency?: string;
  compact?: boolean;
}

/**
 * Animated currency display with proper formatting
 */
export function AnimatedCurrency({
  value,
  currency = 'USD',
  compact = false,
  locale = 'en-US',
  ...props
}: AnimatedCurrencyProps) {
  const formatOptions: Intl.NumberFormatOptions = {
    style: 'currency',
    currency,
    notation: compact ? 'compact' : 'standard',
    minimumFractionDigits: compact ? 0 : 0,
    maximumFractionDigits: compact ? 1 : 0,
  };

  return <AnimatedNumber value={value} locale={locale} formatOptions={formatOptions} {...props} />;
}

// ============================================
// Animated Percentage Component
// ============================================

interface AnimatedPercentageProps extends Omit<AnimatedNumberProps, 'formatOptions' | 'suffix'> {
  decimals?: number;
}

/**
 * Animated percentage display
 */
export function AnimatedPercentage({
  value,
  decimals = 0,
  locale = 'en-US',
  ...props
}: AnimatedPercentageProps) {
  const formatOptions: Intl.NumberFormatOptions = {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  };

  // Value should be in decimal form (0.5 = 50%)
  const decimalValue = value > 1 ? value / 100 : value;

  return (
    <AnimatedNumber value={decimalValue} locale={locale} formatOptions={formatOptions} {...props} />
  );
}

// ============================================
// Animated Counter Component
// ============================================

interface AnimatedCounterProps {
  value: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showPlus?: boolean;
}

/**
 * Simple animated counter with size variants
 */
export function AnimatedCounter({
  value,
  className,
  size = 'md',
  showPlus = false,
}: AnimatedCounterProps) {
  const sizeClasses = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-4xl',
    xl: 'text-6xl',
  };

  return (
    <AnimatedNumber
      value={value}
      showSign={showPlus}
      className={cn('font-bold', sizeClasses[size], className)}
    />
  );
}

// ============================================
// Slot Machine Number (digit by digit)
// ============================================

interface SlotMachineNumberProps {
  value: number;
  className?: string;
  digitClassName?: string;
}

/**
 * Slot machine style number animation
 * Each digit rolls individually
 */
export function SlotMachineNumber({ value, className, digitClassName }: SlotMachineNumberProps) {
  const digits = value.toString().split('');

  return (
    <span className={cn('inline-flex font-mono font-tabular', className)}>
      {digits.map((digit, index) => (
        <SlotDigit key={index} digit={digit} className={digitClassName} />
      ))}
    </span>
  );
}

interface SlotDigitProps {
  digit: string;
  className?: string;
}

function SlotDigit({ digit, className }: SlotDigitProps) {
  const y = useMotionValue(0);
  const numericDigit = parseInt(digit, 10);

  React.useEffect(() => {
    if (!isNaN(numericDigit)) {
      animate(y, -numericDigit * 100, {
        type: 'spring',
        stiffness: 300,
        damping: 30,
      });
    }
  }, [numericDigit, y]);

  if (isNaN(numericDigit)) {
    return <span className={className}>{digit}</span>;
  }

  return (
    <span className={cn('relative inline-block h-[1em] overflow-hidden', className)}>
      <motion.span
        className="absolute flex flex-col"
        style={{ y: useTransform(y, (val) => `${val}%`) }}
      >
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
          <span key={num} className="h-[1em] flex items-center justify-center">
            {num}
          </span>
        ))}
      </motion.span>
    </span>
  );
}

// ============================================
// Data Change Indicator
// ============================================

interface DataChangeIndicatorProps {
  value: number;
  previousValue: number;
  format?: 'number' | 'currency' | 'percentage';
  className?: string;
  showIcon?: boolean;
}

/**
 * Shows change between values with animation
 */
export function DataChangeIndicator({
  value,
  previousValue,
  format = 'number',
  className,
  showIcon = true,
}: DataChangeIndicatorProps) {
  const change = value - previousValue;
  const percentChange = previousValue !== 0 ? (change / previousValue) * 100 : 0;

  const isPositive = change >= 0;

  const formatValue = (val: number) => {
    switch (format) {
      case 'currency':
        return new Intl.NumberFormat(undefined, {
          style: 'currency',
          currency: 'USD',
          maximumFractionDigits: 0,
        }).format(Math.abs(val));
      case 'percentage':
        return `${Math.abs(val).toFixed(1)}%`;
      default:
        return new Intl.NumberFormat(undefined).format(Math.abs(val));
    }
  };

  return (
    <motion.span
      initial={{ opacity: 0, y: isPositive ? 10 : -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'inline-flex items-center gap-1 text-sm font-medium',
        isPositive ? 'text-success' : 'text-error',
        className,
      )}
    >
      {showIcon && (
        <motion.svg
          initial={{ rotate: isPositive ? 180 : 0 }}
          animate={{ rotate: isPositive ? 0 : 180 }}
          className="h-3 w-3"
          viewBox="0 0 12 12"
          fill="currentColor"
        >
          <path d="M6 2L10 8H2L6 2Z" />
        </motion.svg>
      )}
      <span>
        {isPositive ? '+' : '-'}
        {formatValue(change)}
      </span>
      <span className="text-muted-foreground">
        ({isPositive ? '+' : ''}
        {percentChange.toFixed(1)}%)
      </span>
    </motion.span>
  );
}

// ============================================
// Live Data Value (with pulse on update)
// ============================================

interface LiveDataValueProps {
  value: number;
  label?: string;
  format?: 'number' | 'currency' | 'percentage';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Live data value that pulses on update
 * Bloomberg terminal style
 */
export function LiveDataValue({
  value,
  label,
  format = 'number',
  size = 'md',
  className,
}: LiveDataValueProps) {
  const [hasUpdated, setHasUpdated] = React.useState(false);
  const prevValue = React.useRef(value);

  React.useEffect(() => {
    if (prevValue.current !== value) {
      setHasUpdated(true);
      const timer = setTimeout(() => setHasUpdated(false), 1000);
      prevValue.current = value;
      return () => clearTimeout(timer);
    }
  }, [value]);

  const sizeClasses = {
    sm: { value: 'text-lg', label: 'text-xs' },
    md: { value: 'text-2xl', label: 'text-sm' },
    lg: { value: 'text-4xl', label: 'text-base' },
  };

  const Component =
    format === 'currency'
      ? AnimatedCurrency
      : format === 'percentage'
        ? AnimatedPercentage
        : AnimatedNumber;

  return (
    <div className={cn('space-y-1', className)}>
      {label && <div className={cn('text-muted-foreground', sizeClasses[size].label)}>{label}</div>}
      <motion.div
        animate={
          hasUpdated
            ? {
                backgroundColor: ['var(--color-accent-light)', 'transparent'],
              }
            : {}
        }
        transition={{ duration: 0.5 }}
        className={cn('font-bold rounded px-1 -mx-1', sizeClasses[size].value)}
      >
        <Component value={value} highlightChange />
      </motion.div>
    </div>
  );
}
