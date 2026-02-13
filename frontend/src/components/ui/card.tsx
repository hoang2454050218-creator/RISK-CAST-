import * as React from 'react';
import { motion, type HTMLMotionProps, type Variants } from 'framer-motion';
import { cn } from '@/lib/utils';
import { springs, staggerItem } from '@/lib/animations';

// Card motion variants — works in both light & dark via CSS variable shadows
const cardVariants: Variants = {
  rest: {
    scale: 1,
    y: 0,
  },
  hover: {
    scale: 1.008,
    y: -3,
    transition: springs.smooth,
  },
  tap: {
    scale: 0.995,
    transition: springs.stiff,
  },
};

const cardVariantsSubtle: Variants = {
  rest: {
    scale: 1,
  },
  hover: {
    scale: 1.005,
    transition: springs.smooth,
  },
};

interface CardProps extends Omit<HTMLMotionProps<'div'>, 'children'> {
  children?: React.ReactNode;
  variant?: 'default' | 'premium' | 'glass' | 'outline' | 'ghost';
  hoverEffect?: 'lift' | 'glow' | 'scale' | 'none';
  urgency?: 'immediate' | 'urgent' | 'soon' | 'watch';
  isInteractive?: boolean;
  enableAnimation?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      hoverEffect = 'lift',
      urgency,
      isInteractive = false,
      enableAnimation = true,
      children,
      ...props
    },
    ref,
  ) => {
    const variantClasses = {
      default: cn(
        'bg-card border border-border shadow-level-1 backdrop-blur-sm',
        'hover:shadow-level-2 hover:border-[var(--light-card-border-hover,var(--color-border))]',
        'transition-[box-shadow,border-color,transform] duration-200 ease-out',
      ),
      premium: 'card-premium bg-card shadow-level-2 hover:shadow-level-3 transition-shadow',
      glass: 'card-glass shadow-level-2',
      outline: 'bg-transparent border-2 border-border hover:border-accent/30 transition-colors',
      ghost: 'bg-transparent border-0 shadow-none',
    };

    const urgencyClasses = {
      immediate: 'urgency-card-immediate',
      urgent: 'urgency-card-urgent',
      soon: 'urgency-card-soon',
      watch: 'urgency-card-watch',
    };

    const hoverVariants =
      hoverEffect === 'none'
        ? undefined
        : hoverEffect === 'scale'
          ? cardVariantsSubtle
          : cardVariants;

    const handleKeyDown = isInteractive
      ? (e: React.KeyboardEvent<HTMLDivElement>) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            e.currentTarget.click();
          }
        }
      : undefined;

    return (
      <motion.div
        ref={ref}
        role={isInteractive ? 'button' : undefined}
        tabIndex={isInteractive ? 0 : undefined}
        onKeyDown={handleKeyDown}
        className={cn(
          'rounded-xl text-card-foreground',
          variantClasses[variant],
          urgency && urgencyClasses[urgency],
          isInteractive && 'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          className,
        )}
        initial={enableAnimation ? 'rest' : undefined}
        whileHover={isInteractive && hoverEffect !== 'none' ? 'hover' : undefined}
        whileTap={isInteractive ? 'tap' : undefined}
        variants={hoverVariants}
        {...props}
      >
        {children}
      </motion.div>
    );
  },
);
Card.displayName = 'Card';

// Animated card that fades in
const AnimatedCard = React.forwardRef<HTMLDivElement, CardProps & { delay?: number }>(
  ({ delay = 0, ...props }, ref) => {
    return (
      <Card
        ref={ref}
        initial="hidden"
        animate="visible"
        variants={{
          hidden: { opacity: 0, y: 20, scale: 0.98 },
          visible: {
            opacity: 1,
            y: 0,
            scale: 1,
            transition: {
              ...springs.smooth,
              delay,
            },
          },
        }}
        {...props}
      />
    );
  },
);
AnimatedCard.displayName = 'AnimatedCard';

// Card that works with stagger container
const StaggerCard = React.forwardRef<HTMLDivElement, CardProps>((props, ref) => {
  return <Card ref={ref} variants={staggerItem} {...props} />;
});
StaggerCard.displayName = 'StaggerCard';

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />
  ),
);
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  ),
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
));
CardDescription.displayName = 'CardDescription';

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  ),
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('flex items-center p-6 pt-0', className)} {...props} />
  ),
);
CardFooter.displayName = 'CardFooter';

// Urgency card with glow effect
interface UrgencyCardProps extends CardProps {
  urgency: 'immediate' | 'urgent' | 'soon' | 'watch';
  showGlow?: boolean;
}

const UrgencyCard = React.forwardRef<HTMLDivElement, UrgencyCardProps>(
  ({ urgency, showGlow = true, className, ...props }, ref) => {
    const glowClasses = {
      immediate: showGlow ? 'glow-danger-soft breathe-glow' : '',
      urgent: showGlow ? 'glow-warning-soft' : '',
      soon: '',
      watch: '',
    };

    return (
      <Card
        ref={ref}
        urgency={urgency}
        className={cn(glowClasses[urgency], className)}
        {...props}
      />
    );
  },
);
UrgencyCard.displayName = 'UrgencyCard';

// Data card for Bloomberg-style display
interface DataCardProps extends CardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
}

const DataCard = React.forwardRef<HTMLDivElement, DataCardProps>(
  ({ label, value, change, changeLabel, icon, className, ...props }, ref) => {
    const isPositive = change !== undefined && change >= 0;

    return (
      <Card ref={ref} className={cn('p-4', className)} isInteractive hoverEffect="scale" {...props}>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="text-2xl font-bold font-mono data-value">{value}</p>
            {change !== undefined && (
              <p className={cn('text-sm font-medium', isPositive ? 'text-success' : 'text-error')}>
                {isPositive ? '+' : ''}
                {change}%
                {changeLabel && <span className="text-muted-foreground ml-1">{changeLabel}</span>}
              </p>
            )}
          </div>
          {icon && <div className="p-2 rounded-lg bg-muted">{icon}</div>}
        </div>
      </Card>
    );
  },
);
DataCard.displayName = 'DataCard';

export {
  Card,
  AnimatedCard,
  StaggerCard,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  UrgencyCard,
  DataCard,
};
