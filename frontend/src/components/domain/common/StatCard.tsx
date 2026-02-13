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
  urgent = false,
  highlight = false,
  className,
}: StatCardProps) {
  const colors = ACCENT_COLORS[accentColor];

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
      <motion.div whileHover={{ y: -6, scale: 1.02 }} transition={springs.snappy}>
        <Card
          className={cn(
            'overflow-hidden bg-card/80 backdrop-blur-sm relative group border-border/40',
            'hover:shadow-xl hover:shadow-black/10 transition-all duration-300',
            urgent && 'ring-1 ring-error/40',
            highlight && 'ring-1 ring-accent/30',
            className,
          )}
        >
          {/* Full gradient overlay — stronger */}
          <div
            className={cn(
              'absolute inset-0 bg-gradient-to-br opacity-40 group-hover:opacity-60 transition-opacity duration-300',
              colors.overlayGradient,
            )}
          />
          {/* Top accent line — thicker */}
          <div className={cn('absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r', colors.gradient)}>
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          </div>
          <CardContent className="p-5 relative">
            <div className="flex items-center gap-4">
              <motion.div
                className={cn('flex h-12 w-12 items-center justify-center rounded-xl border', colors.iconBg)}
                whileHover={{ scale: 1.1, rotate: 5 }}
                transition={springs.bouncy}
                animate={urgent ? { scale: [1, 1.15, 1] } : {}}
                {...(urgent ? { transition: { duration: 1.5, repeat: Infinity } } : {})}
              >
                <Icon className={cn('h-6 w-6', colors.iconText)} />
              </motion.div>
              <div className="min-w-0">
                <motion.p
                  translate="no"
                  className={cn(
                    'notranslate text-3xl font-black font-mono tabular-nums tracking-tight',
                    urgent && 'text-error',
                  )}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  {renderedValue}
                </motion.p>
                <p className="text-xs text-muted-foreground font-medium mt-0.5">{label}</p>
              </div>
              {changeBadge && <div className="ml-auto shrink-0">{changeBadge}</div>}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );

    if (href) return <Link to={href}>{content}</Link>;
    if (onClick)
      return (
        <div
          role="button"
          tabIndex={0}
          onClick={onClick}
          onKeyDown={(e) => e.key === 'Enter' && onClick()}
          className="cursor-pointer"
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
          'group relative overflow-hidden bg-card border border-border rounded-xl p-4 transition-all shadow-card hover:shadow-card-hover',
          href && 'cursor-pointer',
          onClick && 'cursor-pointer',
          highlight && 'border-info/30',
          urgent && 'border-error/30',
          className,
        )}
      >
        {/* Top accent gradient line */}
        <div className={cn('absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r', colors.gradient)} />

        <div className="flex items-center justify-between">
          {/* Icon */}
          <motion.div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-xl border',
              colors.iconBg,
            )}
            whileHover={{ scale: 1.05, rotate: 3 }}
            transition={springs.bouncy}
            animate={urgent ? { scale: [1, 1.08, 1] } : {}}
            {...(urgent ? { transition: { duration: 2, repeat: Infinity } } : {})}
          >
            <Icon className={cn('h-5 w-5', colors.iconText)} />
          </motion.div>

          {/* Change badge */}
          {changeBadge}
        </div>

        <div className="mt-3">
          <div className="flex items-baseline gap-1.5">
            <motion.p
              translate="no"
              className={cn(
                'notranslate text-2xl font-bold font-mono text-foreground tabular-nums',
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
          <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider mt-1">
            {label}
          </p>
        </div>
      </div>
    </motion.div>
  );

  if (href) return <Link to={href}>{content}</Link>;
  if (onClick)
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => e.key === 'Enter' && onClick()}
        className="cursor-pointer"
      >
        {content}
      </div>
    );
  return content;
}
