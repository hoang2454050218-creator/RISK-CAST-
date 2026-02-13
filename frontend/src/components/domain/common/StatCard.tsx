/**
 * StatCard — Unified stat/metric card used across all RISKCAST pages.
 *
 * Replaces 5 local reimplementations in:
 *   - dashboard/page.tsx
 *   - customers/page.tsx
 *   - human-review/page.tsx
 *   - audit/page.tsx
 *   - reality/page.tsx
 */

import { motion } from 'framer-motion';
import { Link } from 'react-router';
import { TrendingUp, TrendingDown, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';
import { AnimatedNumber, AnimatedCurrency } from '@/components/ui/animated-number';
import { formatCurrency } from '@/lib/formatters';
import { Card, CardContent } from '@/components/ui/card';

// ─── Color Maps ────────────────────────────────────────────────
// Maps semantic color names to Tailwind utility classes.
// All colors are design-token-aligned — no hardcoded hex values.

// Semantic token-based accent colors.
// Uses CSS variable-backed tokens (error, warning, success, info, accent)
// so light/dark mode is handled automatically — no `dark:` prefixes needed.
const ACCENT_COLORS = {
  red: {
    gradient: 'from-error to-error/0',
    overlayGradient: 'from-error/20 to-error/10',
    iconBg: 'bg-error/10 border-error/20',
    iconText: 'text-error',
  },
  amber: {
    gradient: 'from-warning to-warning/0',
    overlayGradient: 'from-warning/20 to-warning/10',
    iconBg: 'bg-warning/10 border-warning/20',
    iconText: 'text-warning',
  },
  orange: {
    gradient: 'from-severity-high to-severity-high/0',
    overlayGradient: 'from-severity-high/20 to-severity-high/10',
    iconBg: 'bg-severity-high/10 border-severity-high/20',
    iconText: 'text-severity-high',
  },
  blue: {
    gradient: 'from-info to-info/0',
    overlayGradient: 'from-info/20 to-info/10',
    iconBg: 'bg-info/10 border-info/20',
    iconText: 'text-info',
  },
  emerald: {
    gradient: 'from-success to-success/0',
    overlayGradient: 'from-success/20 to-success/10',
    iconBg: 'bg-success/10 border-success/20',
    iconText: 'text-success',
  },
  purple: {
    gradient: 'from-action-reroute to-action-reroute/0',
    overlayGradient: 'from-action-reroute/20 to-action-reroute/10',
    iconBg: 'bg-action-reroute/10 border-action-reroute/20',
    iconText: 'text-action-reroute',
  },
  accent: {
    gradient: 'from-accent to-accent/0',
    overlayGradient: 'from-accent/20 to-accent/10',
    iconBg: 'bg-accent/10 border-accent/20',
    iconText: 'text-accent',
  },
  /** @deprecated Use accent instead. Kept for backward compatibility. */
  cyan: {
    gradient: 'from-accent to-accent/0',
    overlayGradient: 'from-accent/20 to-accent/10',
    iconBg: 'bg-accent/10 border-accent/20',
    iconText: 'text-accent',
  },
} as const;

type AccentColor = keyof typeof ACCENT_COLORS;

// ─── Props ─────────────────────────────────────────────────────

/** Props for the unified StatCard component. */
export interface StatCardProps {
  /** Lucide icon component displayed in the card. */
  icon: LucideIcon;

  /** Primary label describing the metric. */
  label: string;

  /** The metric value — number or pre-formatted string. */
  value: number | string;

  /** Semantic accent color. Controls gradient, icon tint, and glow. */
  accentColor?: AccentColor;

  /** Format the numeric value as USD currency. */
  isCurrency?: boolean;

  /** Optional text displayed next to the value (e.g. "< 2h SLA"). */
  sublabel?: string;

  /** Numeric change amount — shows a trend badge when provided. */
  change?: number;

  /** Trend direction for the change badge. Required when `change` is set. */
  trend?: 'up' | 'down' | 'neutral';

  /** Navigate to a route on click. Wraps the card in a `<Link>`. */
  href?: string;

  /** Optional click handler (mutually exclusive with `href`). */
  onClick?: () => void;

  /**
   * Visual variant controlling layout and density.
   * - `'default'`: Terminal-style — top accent line, vertical layout (dashboard, human-review).
   * - `'overlay'`: Gradient overlay background, horizontal layout (customers, audit, reality).
   */
  variant?: 'default' | 'overlay';

  /**
   * Visual weight tier for information hierarchy.
   * - `'hero'`: Largest — 2x height, gradient bg glow, bigger font. Use for THE most important metric.
   * - `'primary'`: Default weight — current look.
   * - `'secondary'`: Subdued — smaller value, lighter colors. Use for supporting context.
   */
  tier?: 'hero' | 'primary' | 'secondary';

  /** Applies urgent styling: red glow border and pulsing icon. */
  urgent?: boolean;

  /** Applies highlight border (blue accent, softer than urgent). */
  highlight?: boolean;

  /** Additional classes merged onto the root element. */
  className?: string;
}

// ─── Component ─────────────────────────────────────────────────

export function StatCard({
  icon: Icon,
  label,
  value,
  accentColor = 'blue',
  isCurrency = false,
  sublabel,
  change,
  trend,
  href,
  onClick,
  variant = 'default',
  tier = 'primary',
  urgent = false,
  highlight = false,
  className,
}: StatCardProps) {
  const colors = ACCENT_COLORS[accentColor];
  const isHero = tier === 'hero';
  const isSecondary = tier === 'secondary';

  // ── Value rendering ───────────────────────────────
  const renderedValue =
    typeof value === 'string' ? (
      value
    ) : isCurrency ? (
      <AnimatedCurrency value={value} compact duration={1.2} />
    ) : (
      <AnimatedNumber value={value} duration={1} />
    );

  // ── Change badge (dashboard-style) ────────────────
  const changeBadge =
    change !== undefined && trend ? (
      <motion.div
        className={cn(
          'flex items-center gap-1 text-[10px] font-bold font-mono px-2 py-0.5 rounded',
          trend === 'up' && 'text-error bg-error/10',
          trend === 'down' && 'text-success bg-success/10',
          trend === 'neutral' && 'text-muted-foreground bg-muted',
        )}
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.3 }}
      >
        {trend === 'up' ? (
          <TrendingUp className="h-3 w-3" />
        ) : trend === 'down' ? (
          <TrendingDown className="h-3 w-3" />
        ) : null}
        <span>
          {typeof change === 'number' && change > 0 ? '+' : ''}
          {isCurrency ? formatCurrency(change, { compact: true }) : change}
        </span>
      </motion.div>
    ) : null;

  // ── Overlay variant — Premium glass card ─
  if (variant === 'overlay') {
    const content = (
      <motion.div whileHover={{ y: isHero ? -4 : -6, scale: isHero ? 1.005 : 1.02 }} transition={springs.snappy}>
        <Card
          className={cn(
            'overflow-hidden bg-card/80 backdrop-blur-sm relative group border-border/40',
            'shadow-level-1 hover:shadow-level-3 transition-all duration-200',
            isHero && 'shadow-level-2 border-border/60',
            isSecondary && 'shadow-none border-border/30',
            urgent && 'ring-1 ring-error/30 glow-danger-soft',
            highlight && 'ring-1 ring-accent/20 glow-accent-soft',
            className,
          )}
        >
          {/* Full gradient overlay — stronger for hero */}
          <div
            className={cn(
              'absolute inset-0 bg-gradient-to-br transition-opacity duration-300',
              isHero ? 'opacity-50 group-hover:opacity-70' : isSecondary ? 'opacity-20 group-hover:opacity-30' : 'opacity-40 group-hover:opacity-60',
              colors.overlayGradient,
            )}
          />
          {/* Top accent line — thicker for hero */}
          <div className={cn('absolute inset-x-0 top-0 bg-gradient-to-r', isHero ? 'h-2' : isSecondary ? 'h-1' : 'h-1.5', colors.gradient)}>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          </div>
          <CardContent className={cn('relative', isHero ? 'p-6' : isSecondary ? 'p-4' : 'p-5')}>
            <div className="flex items-center gap-4">
              <motion.div
                className={cn(
                  'flex items-center justify-center rounded-xl border',
                  isHero ? 'h-14 w-14' : isSecondary ? 'h-10 w-10' : 'h-12 w-12',
                  colors.iconBg,
                )}
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={springs.bouncy}
                animate={urgent ? { scale: [1, 1.15, 1] } : {}}
                {...(urgent ? { transition: { duration: 1.5, repeat: Infinity } } : {})}
              >
                <Icon className={cn(isHero ? 'h-7 w-7' : isSecondary ? 'h-5 w-5' : 'h-6 w-6', colors.iconText)} />
              </motion.div>
              <div className="min-w-0 flex-1">
                {isHero && (
                  <p className="text-[9px] font-mono text-muted-foreground/50 uppercase tracking-[0.15em] mb-1">{label}</p>
                )}
                <motion.p
                  translate="no"
                  className={cn(
                    'notranslate font-black font-mono tabular-nums tracking-tight',
                    isHero ? 'text-4xl' : isSecondary ? 'text-2xl' : 'text-3xl',
                    urgent && 'text-error',
                  )}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  {renderedValue}
                </motion.p>
                {!isHero && <p className="text-xs text-muted-foreground font-medium mt-0.5">{label}</p>}
                {isHero && sublabel && (
                  <p className="text-[10px] font-mono text-muted-foreground/60 mt-1">{sublabel}</p>
                )}
              </div>
              {changeBadge && <div className="ml-auto shrink-0">{changeBadge}</div>}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );

    if (href) return <Link to={href} className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background">{content}</Link>;
    if (onClick)
      return (
        <div
          role="button"
          tabIndex={0}
          onClick={onClick}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
          className="cursor-pointer rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {content}
        </div>
      );
    return content;
  }

  // ── Default variant (dashboard / human-review) ────
  const content = (
    <motion.div whileHover={{ y: -2 }} transition={springs.snappy}>
      <div
        className={cn(
          'group relative overflow-hidden bg-card border border-border rounded-xl',
          isHero ? 'p-6' : isSecondary ? 'p-3' : 'p-4',
          'shadow-level-1 hover:shadow-level-2 transition-[box-shadow,border-color,transform] duration-200',
          isHero && 'shadow-level-2',
          href && 'cursor-pointer',
          onClick && 'cursor-pointer',
          highlight && 'border-info/25 glow-accent-soft',
          urgent && 'border-error/25 glow-danger-soft',
          className,
        )}
      >
        {/* Top accent gradient line — fades at edges for premium feel */}
        <div
          className={cn('absolute inset-x-0 top-0 h-[2px]')}
          style={{
            background: `linear-gradient(90deg, transparent 0%, var(--color-${accentColor === 'red' ? 'error' : accentColor === 'emerald' ? 'success' : accentColor === 'amber' ? 'warning' : 'accent'}) 15%, var(--color-${accentColor === 'red' ? 'error' : accentColor === 'emerald' ? 'success' : accentColor === 'amber' ? 'warning' : 'accent'}) 85%, transparent 100%)`,
            opacity: 0.6,
          }}
        />

        <div className="flex items-center justify-between">
          {/* Icon — circular container with subtle semantic background */}
          <motion.div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-full border',
              colors.iconBg,
            )}
            whileHover={{ scale: 1.05, rotate: 3 }}
            transition={springs.bouncy}
            animate={urgent ? { scale: [1, 1.08, 1] } : {}}
            {...(urgent ? { transition: { duration: 2, repeat: Infinity } } : {})}
          >
            <Icon className={cn('h-5 w-5', colors.iconText)} />
          </motion.div>

          {/* Change badge — enter with slight delay for visual hierarchy */}
          {changeBadge}
        </div>

        <div className="mt-3">
          <div className="flex items-baseline gap-1.5">
            <motion.p
              translate="no"
              className={cn(
                'notranslate font-bold font-mono text-foreground tabular-nums tracking-tight',
                isHero ? 'text-4xl font-black' : isSecondary ? 'text-xl' : 'text-2xl',
                urgent && typeof value !== 'string' && 'text-error',
              )}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {renderedValue}
            </motion.p>
            {sublabel && (
              <span className="text-[10px] font-mono text-muted-foreground uppercase">
                {sublabel}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider mt-1.5">
            {label}
          </p>
        </div>
      </div>
    </motion.div>
  );

  if (href) return <Link to={href} className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background">{content}</Link>;
  if (onClick)
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onClick()}
        className="cursor-pointer rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {content}
      </div>
    );
  return content;
}
