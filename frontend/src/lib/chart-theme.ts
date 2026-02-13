/**
 * RiskCast Chart Theme - AI Risk Terminal Style
 *
 * Style: Data-dense Enterprise
 * Mood: Dark, analytical, precise, high-trust
 * Persona: "AI risk terminal for serious decisions"
 *
 * ═══════════════════════════════════════════════════════════════════
 * THEME SYSTEM DOCUMENTATION
 * ═══════════════════════════════════════════════════════════════════
 *
 * Colors are now provided via CSS variables for theme support (Light/Dark mode).
 *
 * CSS Variable Mapping:
 * - Background colors: var(--color-card), var(--color-background)
 * - Border colors: var(--color-border), var(--color-muted)
 * - Text colors: var(--color-foreground), var(--color-muted-foreground)
 * - Chart colors: var(--chart-1) through var(--chart-5)
 * - Chart grid: var(--chart-grid)
 * - Chart axis: var(--chart-axis)
 *
 * For Recharts components that require JavaScript color values (not CSS classes),
 * use the getChartColors() helper function to get computed CSS variable values.
 *
 * Tailwind class mapping for theme-aware styling:
 * - slate-900/950 backgrounds → bg-card or bg-background
 * - slate-800 borders → border-border
 * - slate-700 muted borders → border-muted
 * - slate-500/600 text → text-muted-foreground
 * - slate-300/400 text → text-foreground
 */

import { useMemo } from 'react';
import { useTheme } from '@/components/ui/theme-provider';

// ═══════════════════════════════════════════════════════════════════
// CSS VARIABLE REFERENCES
// ═══════════════════════════════════════════════════════════════════

/**
 * CSS variable names for use in style props and dynamic styling.
 * Use these with var() in CSS or getComputedStyle for JS values.
 */
export const CSS_VARS = {
  // Semantic colors
  background: 'var(--color-background)',
  foreground: 'var(--color-foreground)',
  card: 'var(--color-card)',
  cardForeground: 'var(--color-card-foreground)',
  border: 'var(--color-border)',
  muted: 'var(--color-muted)',
  mutedForeground: 'var(--color-muted-foreground)',

  // Chart-specific colors (consistent across themes)
  chart1: 'var(--chart-1)', // Primary accent/blue
  chart2: 'var(--chart-2)', // Success green
  chart3: 'var(--chart-3)', // Warning amber
  chart4: 'var(--chart-4)', // Danger red
  chart5: 'var(--chart-5)', // Purple accent

  // Chart structural elements
  chartGrid: 'var(--chart-grid)',
  chartAxis: 'var(--chart-axis)',
} as const;

/**
 * Get computed CSS variable values for use in Recharts and other JS contexts.
 * Call this in useEffect or component body to get actual color values.
 *
 * @example
 * const colors = getChartColors();
 * <Line stroke={colors.chart1} />
 */
/** Shape returned by getChartColors / useChartColors */
export interface ChartColorValues {
  background: string;
  foreground: string;
  card: string;
  cardForeground: string;
  border: string;
  muted: string;
  mutedForeground: string;
  chart1: string;
  chart2: string;
  chart3: string;
  chart4: string;
  chart5: string;
  chart6: string;
  chartGrid: string;
  chartAxis: string;
  chartTooltipBg: string;
  chartTooltipBorder: string;
  severityCritical: string;
  severityHigh: string;
  severityMedium: string;
  severityLow: string;
  confidenceHigh: string;
  confidenceMedium: string;
  confidenceLow: string;
}

function readVar(styles: CSSStyleDeclaration, name: string, fallback: string): string {
  return styles.getPropertyValue(name).trim() || fallback;
}

export function getChartColors(): ChartColorValues {
  if (typeof window === 'undefined') {
    // SSR fallback — dark theme defaults
    return {
      background: '#0A0F1A',
      foreground: '#E2E8F0',
      card: '#0F172A',
      cardForeground: '#E2E8F0',
      border: '#1E293B',
      muted: '#1E293B',
      mutedForeground: '#64748B',
      chart1: '#3B82F6',
      chart2: '#38BDF8',
      chart3: '#22C55E',
      chart4: '#FFB020',
      chart5: '#FF4444',
      chart6: '#A78BFA',
      chartGrid: 'rgba(255, 255, 255, 0.06)',
      chartAxis: '#64748B',
      chartTooltipBg: '#1a2332',
      chartTooltipBorder: 'rgba(59, 130, 246, 0.2)',
      severityCritical: '#FF4444',
      severityHigh: '#FFB020',
      severityMedium: '#38BDF8',
      severityLow: '#22C55E',
      confidenceHigh: '#22C55E',
      confidenceMedium: '#FFB020',
      confidenceLow: '#FF4444',
    };
  }

  const styles = getComputedStyle(document.documentElement);

  return {
    background: readVar(styles, '--color-background', '#0A0F1A'),
    foreground: readVar(styles, '--color-foreground', '#E2E8F0'),
    card: readVar(styles, '--color-card', '#0F172A'),
    cardForeground: readVar(styles, '--color-card-foreground', '#E2E8F0'),
    border: readVar(styles, '--color-border', '#1E293B'),
    muted: readVar(styles, '--color-muted', '#1E293B'),
    mutedForeground: readVar(styles, '--color-muted-foreground', '#64748B'),
    chart1: readVar(styles, '--chart-1', '#3B82F6'),
    chart2: readVar(styles, '--chart-2', '#38BDF8'),
    chart3: readVar(styles, '--chart-3', '#22C55E'),
    chart4: readVar(styles, '--chart-4', '#FFB020'),
    chart5: readVar(styles, '--chart-5', '#FF4444'),
    chart6: readVar(styles, '--chart-6', '#A78BFA'),
    chartGrid: readVar(styles, '--chart-grid', 'rgba(255, 255, 255, 0.06)'),
    chartAxis: readVar(styles, '--chart-axis', '#64748B'),
    chartTooltipBg: readVar(styles, '--chart-tooltip-bg', '#1a2332'),
    chartTooltipBorder: readVar(styles, '--chart-tooltip-border', 'rgba(59, 130, 246, 0.2)'),
    severityCritical: readVar(styles, '--color-severity-critical', '#FF4444'),
    severityHigh: readVar(styles, '--color-severity-high', '#FFB020'),
    severityMedium: readVar(styles, '--color-severity-medium', '#38BDF8'),
    severityLow: readVar(styles, '--color-severity-low', '#22C55E'),
    confidenceHigh: readVar(styles, '--color-confidence-high', '#22C55E'),
    confidenceMedium: readVar(styles, '--color-confidence-medium', '#FFB020'),
    confidenceLow: readVar(styles, '--color-confidence-low', '#FF4444'),
  };
}

// ═══════════════════════════════════════════════════════════════════
// LIGHT MODE PALETTE
// ═══════════════════════════════════════════════════════════════════
// Professional, saturated colors for white/light backgrounds.
// Structure mirrors TERMINAL_COLORS so the two palettes are interchangeable.

export const LIGHT_PALETTE = {
  cyan: {
    primary: '#2563EB',
    secondary: '#3B82F6',
    tertiary: '#1D4ED8',
    glow: 'transparent',
    dim: 'rgba(37, 99, 235, 0.08)',
    gradient: ['#2563EB', '#3B82F6', '#1D4ED8'],
  },
  green: {
    primary: '#16A34A',
    secondary: '#22C55E',
    tertiary: '#15803D',
    glow: 'transparent',
    dim: 'rgba(22, 163, 74, 0.08)',
    gradient: ['#16A34A', '#22C55E', '#15803D'],
  },
  amber: {
    primary: '#D97706',
    secondary: '#F59E0B',
    tertiary: '#B45309',
    glow: 'transparent',
    dim: 'rgba(217, 119, 6, 0.08)',
    gradient: ['#D97706', '#F59E0B', '#B45309'],
  },
  red: {
    primary: '#DC2626',
    secondary: '#EF4444',
    tertiary: '#B91C1C',
    glow: 'transparent',
    dim: 'rgba(220, 38, 38, 0.08)',
    gradient: ['#DC2626', '#EF4444', '#B91C1C'],
  },
  orange: {
    primary: '#EA580C',
    secondary: '#F97316',
    tertiary: '#C2410C',
    glow: 'transparent',
    dim: 'rgba(234, 88, 12, 0.08)',
    gradient: ['#EA580C', '#F97316', '#C2410C'],
  },
  slate: {
    primary: '#64748B',
    secondary: '#475569',
    tertiary: '#334155',
    dim: 'rgba(100, 116, 139, 0.1)',
  },
  actions: {
    REROUTE: '#2563EB',
    DELAY: '#7C3AED',
    INSURE: '#16A34A',
    MONITOR: '#64748B',
    DO_NOTHING: '#94A3B8',
  },
  background: {
    card: 'rgba(255, 255, 255, 0.95)',
    tooltip: 'rgba(255, 255, 255, 0.98)',
    grid: 'rgba(0, 0, 0, 0.04)',
  },
} as const;

// ═══════════════════════════════════════════════════════════════════
// THEME DETECTION & REACTIVE HOOK
// ═══════════════════════════════════════════════════════════════════

/**
 * Check if the current theme is dark mode (non-React contexts).
 * In React components prefer useChartColors().isDark.
 */
export function isDarkMode(): boolean {
  if (typeof window === 'undefined') return true;
  return document.documentElement.classList.contains('dark');
}

/**
 * React hook: theme-reactive chart colors.
 * Combines CSS variable values with the full theme-appropriate color palette.
 * Re-computes automatically when the user toggles theme.
 *
 * @example
 * const colors = useChartColors();
 * <Line stroke={colors.cyan.primary} />
 * {colors.isDark && <filter id="glow" ... />}
 */
export function useChartColors() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  return useMemo(() => {
    const base = getChartColors();
    const palette = isDark ? TERMINAL_COLORS : LIGHT_PALETTE;

    return {
      ...base,
      isDark,
      /** Ordered palette array for multi-series charts */
      palette: [base.chart1, base.chart2, base.chart3, base.chart4, base.chart5, base.chart6],
      /** Severity scale */
      severity: {
        critical: base.severityCritical,
        high: base.severityHigh,
        medium: base.severityMedium,
        low: base.severityLow,
      },
      /** Confidence scale */
      confidence: {
        high: base.confidenceHigh,
        medium: base.confidenceMedium,
        low: base.confidenceLow,
      },
      /** Tooltip config */
      tooltip: {
        bg: base.chartTooltipBg,
        border: base.chartTooltipBorder,
      },
      /** Extended palette objects */
      cyan: palette.cyan,
      green: palette.green,
      amber: palette.amber,
      red: palette.red,
      orange: palette.orange,
      slate: palette.slate,
      actions: palette.actions,
    };
  }, [isDark]);
}

// ═══════════════════════════════════════════════════════════════════
// TERMINAL COLOR PALETTE (DARK MODE)
// ═══════════════════════════════════════════════════════════════════
// Neon terminal colours – used as the dark-mode palette.
// For theme-aware colours use useChartColors() in React components.

export const TERMINAL_COLORS = {
  // Primary terminal colors (maps to --chart-1) - accent/blue
  cyan: {
    primary: '#3B82F6',
    secondary: '#2563EB',
    tertiary: '#1D4ED8',
    glow: 'rgba(59, 130, 246, 0.5)',
    dim: 'rgba(59, 130, 246, 0.1)',
    gradient: ['#3B82F6', '#2563EB', '#1D4ED8'],
  },

  // Success / Positive (maps to --chart-2) — teal-green, not neon
  green: {
    primary: '#34d9bc',
    secondary: '#22c55e',
    tertiary: '#16a34a',
    glow: 'rgba(52, 217, 188, 0.35)',
    dim: 'rgba(52, 217, 188, 0.1)',
    gradient: ['#34d9bc', '#22c55e', '#16a34a'],
  },

  // Warning / Caution (maps to --chart-3) — softer warm amber
  amber: {
    primary: '#fbbf4e',
    secondary: '#f59e0b',
    tertiary: '#d97706',
    glow: 'rgba(251, 191, 78, 0.35)',
    dim: 'rgba(251, 191, 78, 0.1)',
    gradient: ['#fbbf4e', '#f59e0b', '#d97706'],
  },

  // Danger / Critical (maps to --chart-4) — softer rose-red
  red: {
    primary: '#f87171',
    secondary: '#ef4444',
    tertiary: '#dc2626',
    glow: 'rgba(248, 113, 113, 0.35)',
    dim: 'rgba(248, 113, 113, 0.1)',
    gradient: ['#f87171', '#ef4444', '#dc2626'],
  },

  // High severity / Orange (between red and amber) — toned down
  orange: {
    primary: '#fb923c',
    secondary: '#f97316',
    tertiary: '#ea580c',
    glow: 'rgba(251, 146, 60, 0.30)',
    dim: 'rgba(251, 146, 60, 0.1)',
    gradient: ['#fb923c', '#f97316', '#ea580c'],
  },

  // Neutral / Secondary (maps to --color-muted-foreground)
  slate: {
    primary: '#64748B',
    secondary: '#475569',
    tertiary: '#334155',
    dim: 'rgba(100, 116, 139, 0.2)',
  },

  // Action type colors — harmonized with desaturated palette
  actions: {
    REROUTE: '#6b8aff',
    DELAY: '#a78bfa',
    INSURE: '#34d9bc',
    MONITOR: '#64748B',
    DO_NOTHING: '#475569',
  },

  // Background (use CSS vars: bg-card, bg-background in JSX)
  background: {
    card: 'rgba(15, 23, 42, 0.8)',
    tooltip: 'rgba(2, 6, 23, 0.95)',
    grid: 'rgba(100, 116, 139, 0.08)',
  },
} as const;

// ═══════════════════════════════════════════════════════════════════
// CHART CONFIGURATION
// ═══════════════════════════════════════════════════════════════════
// NOTE: For theme-aware grid/axis colors, use getChartColors() at runtime
// or apply CSS classes to wrapper elements.

export const CHART_CONFIG = {
  // Grid styling - use getChartColors().chartGrid for dynamic theming
  grid: {
    stroke: 'rgba(100, 116, 139, 0.15)', // Fallback, prefer var(--chart-grid)
    strokeDasharray: '2 4',
  },

  // Axis styling - use getChartColors().chartAxis for dynamic theming
  axis: {
    stroke: '#334155', // Fallback, prefer var(--chart-axis)
    fontSize: 10,
    fontFamily: 'JetBrains Mono, Monaco, Consolas, monospace',
    tickLine: false,
  },

  // Animation
  animation: {
    duration: 1500,
    easing: 'ease-out',
  },

  // Tooltip - use CSS classes: bg-card border-border in JSX
  tooltip: {
    background: 'rgba(2, 6, 23, 0.95)', // Fallback
    border: '1px solid rgba(100, 116, 139, 0.3)',
    borderRadius: '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
  },
} as const;

/**
 * Get theme-aware chart configuration.
 * Call this in components to get colors that respect the current theme.
 */
export function getThemeAwareChartConfig() {
  const colors = getChartColors();
  return {
    grid: {
      stroke: colors.chartGrid,
      strokeDasharray: '2 4',
    },
    axis: {
      stroke: colors.chartAxis,
      fontSize: 10,
      fontFamily: 'JetBrains Mono, Monaco, Consolas, monospace',
      tickLine: false,
    },
  };
}

// ═══════════════════════════════════════════════════════════════════
// SVG FILTER DEFINITIONS (for glow effects)
// ═══════════════════════════════════════════════════════════════════

export const SVG_FILTERS = {
  accentGlow: `
    <filter id="accentGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feFlood flood-color="#3B82F6" flood-opacity="0.5"/>
      <feComposite in2="coloredBlur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  `,
  greenGlow: `
    <filter id="greenGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feFlood flood-color="#34d9bc" flood-opacity="0.4"/>
      <feComposite in2="coloredBlur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  `,
  redGlow: `
    <filter id="redGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feFlood flood-color="#f87171" flood-opacity="0.4"/>
      <feComposite in2="coloredBlur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  `,
} as const;

// ═══════════════════════════════════════════════════════════════════
// DATA DENSITY HELPERS
// ═══════════════════════════════════════════════════════════════════

export function formatCompact(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function formatPrecise(value: number, decimals = 2): string {
  return value.toFixed(decimals);
}

export function getColorByValue(
  value: number,
  thresholds: { critical: number; warning: number; caution: number },
): keyof typeof TERMINAL_COLORS {
  if (value >= thresholds.critical) return 'red';
  if (value >= thresholds.warning) return 'amber';
  if (value >= thresholds.caution) return 'amber';
  return 'green';
}

// ═══════════════════════════════════════════════════════════════════
// CHART STAT CARD VARIANTS
// ═══════════════════════════════════════════════════════════════════
// These use Tailwind classes which automatically adapt to the theme.
// The color classes (cyan, emerald, amber, red) remain consistent
// across themes for chart accent colors.

export const STAT_VARIANTS = {
  primary: {
    background: 'bg-gradient-to-br from-accent/10 to-accent/5',
    border: 'border-accent/20',
    text: 'text-blue-600 dark:text-blue-400',
    glow: 'shadow-accent/20',
  },
  success: {
    background: 'bg-gradient-to-br from-emerald-500/10 to-emerald-500/5',
    border: 'border-emerald-500/20',
    text: 'text-emerald-600 dark:text-emerald-400',
    glow: 'shadow-emerald-500/20',
  },
  warning: {
    background: 'bg-gradient-to-br from-amber-500/10 to-amber-500/5',
    border: 'border-amber-500/20',
    text: 'text-amber-600 dark:text-amber-400',
    glow: 'shadow-amber-500/20',
  },
  danger: {
    background: 'bg-gradient-to-br from-red-500/10 to-red-500/5',
    border: 'border-red-500/20',
    text: 'text-red-600 dark:text-red-400',
    glow: 'shadow-red-500/20',
  },
  neutral: {
    // Use theme-aware muted colors for neutral variant
    background: 'bg-gradient-to-br from-muted/50 to-muted/25',
    border: 'border-border',
    text: 'text-muted-foreground',
    glow: 'shadow-muted/20',
  },
} as const;

// ═══════════════════════════════════════════════════════════════════
// REUSABLE GRADIENT DEFINITIONS (as SVG strings)
// ═══════════════════════════════════════════════════════════════════

export function createGradientString(id: string, colors: string[]): string {
  const stops = colors
    .map(
      (color, i) => `<stop offset="${(i / (colors.length - 1)) * 100}%" stop-color="${color}" />`,
    )
    .join('');

  return `
    <linearGradient id="${id}-line" x1="0" y1="0" x2="1" y2="0">
      ${stops}
    </linearGradient>
    <linearGradient id="${id}-area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${colors[0]}" stop-opacity="0.4" />
      <stop offset="50%" stop-color="${colors[0]}" stop-opacity="0.15" />
      <stop offset="100%" stop-color="${colors[0]}" stop-opacity="0" />
    </linearGradient>
  `;
}

// ═══════════════════════════════════════════════════════════════════
// TERMINAL DECORATIONS
// ═══════════════════════════════════════════════════════════════════
// These decorations use theme-aware opacity values that work in both modes.

export const TERMINAL_DECORATIONS = {
  // Scan line effect class - uses neutral opacity that works in both themes
  scanLines:
    'before:absolute before:inset-0 before:pointer-events-none before:bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.03)_2px,rgba(0,0,0,0.03)_4px)] dark:before:bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.03)_2px,rgba(0,0,0,0.03)_4px)]',

  // Grid background - theme-aware opacity
  gridPattern:
    'bg-[radial-gradient(var(--color-muted-foreground)/0.1_1px,transparent_1px)] bg-[size:20px_20px]',

  // Corner accents - consistent cyan accent across themes
  cornerAccent:
    'before:absolute before:top-0 before:left-0 before:w-4 before:h-4 before:border-l-2 before:border-t-2 before:border-accent/50 after:absolute after:bottom-0 after:right-0 after:w-4 after:h-4 after:border-r-2 after:border-b-2 after:border-accent/50',
} as const;

export default TERMINAL_COLORS;
