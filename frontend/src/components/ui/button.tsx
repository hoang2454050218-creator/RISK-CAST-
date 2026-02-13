import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 relative overflow-hidden',
  {
    variants: {
      variant: {
        default:
          'bg-gradient-to-b from-primary to-primary/90 text-primary-foreground shadow-sm hover:shadow-md hover:from-primary/95 hover:to-primary/85',
        destructive:
          'bg-gradient-to-b from-destructive to-destructive/90 text-destructive-foreground shadow-sm hover:shadow-md hover:from-destructive/95 hover:to-destructive/85',
        outline:
          'border border-border bg-background/80 backdrop-blur-sm shadow-sm hover:bg-muted hover:text-foreground hover:border-accent/20',
        secondary: 'bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80',
        ghost: 'hover:bg-muted/80 hover:text-foreground',
        link: 'text-accent underline-offset-4 hover:underline',

        // Premium variants with gradients
        premium:
          'bg-gradient-to-r from-accent to-action-reroute text-accent-foreground shadow-md hover:shadow-lg hover:shadow-accent/25',
        'premium-outline': 'border-2 border-accent bg-transparent text-accent hover:bg-accent/10',

        // Action-specific variants
        reroute: 'bg-action-reroute text-white hover:bg-action-reroute/90 shadow-sm',
        delay: 'bg-action-delay text-white hover:bg-action-delay/90 shadow-sm',
        insure: 'bg-action-insure text-white hover:bg-action-insure/90 shadow-sm',
        monitor: 'bg-action-monitor text-white hover:bg-action-monitor/90 shadow-sm',

        // Urgency variants with glow
        urgent: 'bg-urgency-urgent text-white hover:bg-urgency-urgent/90 shadow-sm',
        immediate:
          'bg-urgency-immediate text-white hover:bg-urgency-immediate/90 shadow-md shadow-urgency-immediate/30',

        // Success/Error variants
        success: 'bg-success text-white hover:bg-success/90 shadow-sm',
        error: 'bg-error text-white hover:bg-error/90 shadow-sm',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 rounded-md px-3 text-xs',
        lg: 'h-12 rounded-md px-6 text-base',
        xl: 'h-14 rounded-lg px-8 text-lg',
        icon: 'h-10 w-10',
        'icon-sm': 'h-8 w-8',
        'icon-lg': 'h-12 w-12',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

// Motion variants for premium animations
const buttonMotion = {
  rest: { scale: 1 },
  hover: { scale: 1.02 },
  tap: { scale: 0.98 },
};

export interface ButtonProps
  extends Omit<HTMLMotionProps<'button'>, 'children'>, VariantProps<typeof buttonVariants> {
  children?: React.ReactNode;
  isLoading?: boolean;
  loadingText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  enableHoverAnimation?: boolean;
  enableRipple?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      isLoading = false,
      loadingText,
      leftIcon,
      rightIcon,
      enableHoverAnimation = true,
      enableRipple = true,
      children,
      disabled,
      onClick,
      ...props
    },
    ref,
  ) => {
    const [ripples, setRipples] = React.useState<Array<{ x: number; y: number; id: number }>>([]);

    const handleClick = React.useCallback(
      (e: React.MouseEvent<HTMLButtonElement>) => {
        if (enableRipple && !disabled && !isLoading) {
          const rect = e.currentTarget.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          const id = Date.now();

          setRipples((prev) => [...prev, { x, y, id }]);

          // Remove ripple after animation
          setTimeout(() => {
            setRipples((prev) => prev.filter((r) => r.id !== id));
          }, 600);
        }

        onClick?.(e);
      },
      [enableRipple, disabled, isLoading, onClick],
    );

    const isDisabled = disabled || isLoading;

    return (
      <motion.button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={isDisabled}
        aria-busy={isLoading || undefined}
        onClick={handleClick}
        initial="rest"
        whileHover={enableHoverAnimation && !isDisabled ? 'hover' : undefined}
        whileTap={enableHoverAnimation && !isDisabled ? 'tap' : undefined}
        variants={buttonMotion}
        transition={springs.snappy}
        {...props}
      >
        {/* Ripple effects */}
        {ripples.map((ripple) => (
          <motion.span
            key={ripple.id}
            className="absolute rounded-full bg-white/30 pointer-events-none"
            initial={{ width: 0, height: 0, opacity: 0.5 }}
            animate={{ width: 200, height: 200, opacity: 0 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            style={{
              left: ripple.x - 100,
              top: ripple.y - 100,
            }}
          />
        ))}

        {/* Shimmer effect for premium variants */}
        {(variant === 'premium' || variant === 'immediate') && (
          <motion.span
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
            initial={{ x: '-100%' }}
            animate={{ x: '100%' }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              repeatDelay: 3,
              ease: 'linear',
            }}
          />
        )}

        {/* Loading state */}
        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}

        {/* Left icon */}
        {!isLoading && leftIcon && leftIcon}

        {/* Button text */}
        <span className={cn(isLoading && loadingText ? '' : isLoading ? 'opacity-0' : '')}>
          {isLoading && loadingText ? loadingText : children}
        </span>

        {/* Right icon */}
        {!isLoading && rightIcon && rightIcon}
      </motion.button>
    );
  },
);
Button.displayName = 'Button';

// Animated icon button with scale effect
const IconButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size = 'icon', ...props }, ref) => {
    return <Button ref={ref} size={size} className={cn('rounded-full', className)} {...props} />;
  },
);
IconButton.displayName = 'IconButton';

// Button group with connected styling
interface ButtonGroupProps {
  children: React.ReactNode;
  className?: string;
}

function ButtonGroup({ children, className }: ButtonGroupProps) {
  return (
    <div className={cn('inline-flex rounded-md shadow-sm', className)}>
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child)) return child;

        const el = child as React.ReactElement<ButtonProps>;
        const isFirst = index === 0;
        const isLast = index === React.Children.count(children) - 1;

        return React.cloneElement(el, {
          className: cn(
            el.props.className,
            !isFirst && '-ml-px',
            !isFirst && !isLast && 'rounded-none',
            isFirst && 'rounded-r-none',
            isLast && 'rounded-l-none',
          ),
          enableHoverAnimation: false,
        });
      })}
    </div>
  );
}

export { Button, IconButton, ButtonGroup, buttonVariants };
