# RISKCAST Dual-Theme System

## Overview

RISKCAST implements a cohesive dual-theme system where both Light and Dark modes feel like the same product with different visual "skins":

- **Dark Mode**: "AI Risk Terminal" - Bloomberg Terminal-inspired, data-dense, analytical
- **Light Mode**: "Enterprise Professional" - Clean, accessible, corporate-friendly

## Architecture

### Theme Provider

Located at: `frontend/src/components/ui/theme-provider.tsx`

```typescript
import { useTheme } from '@/components/ui/theme-provider';

function MyComponent() {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  
  // theme: 'light' | 'dark' | 'system'
  // resolvedTheme: 'light' | 'dark' (actual applied theme)
  // setTheme: (theme) => void
  // toggleTheme: () => void
}
```

### CSS Variables

All theme colors are defined in `frontend/src/index.css` using Tailwind v4's `@theme` directive:

```css
/* Light Mode (default) */
@theme {
  --color-background: #FAFBFC;
  --color-foreground: #0F172A;
  --color-card: #FFFFFF;
  --color-muted: #F1F5F9;
  --color-border: #E2E8F0;
  /* ... more variables */
}

/* Dark Mode */
html.dark, [data-theme="dark"] {
  --color-background: #0A0F1A;
  --color-foreground: #E2E8F0;
  --color-card: #0F172A;
  --color-muted: #151D2E;
  --color-border: #1E293B;
  /* ... more variables */
}
```

## Semantic Color Tokens

### Background Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--color-background` | #FAFBFC | #0A0F1A | Page background |
| `--color-card` | #FFFFFF | #0F172A | Card/elevated surfaces |
| `--color-muted` | #F1F5F9 | #151D2E | Subtle backgrounds |

### Text Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--color-foreground` | #0F172A | #E2E8F0 | Primary text |
| `--color-muted-foreground` | #64748B | #94A3B8 | Secondary text |

### Border Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--color-border` | #E2E8F0 | #1E293B | Default borders |
| `--color-border-subtle` | #F1F5F9 | #151D2E | Subtle borders |

### Accent Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--color-accent` | #3B82F6 | #00F5FF | Brand accent (Blue/Cyan) |
| `--color-accent-glow` | none | rgba(0,245,255,0.4) | Terminal glow effect |

### Semantic Status Colors

These colors maintain consistent meaning across themes:

| Token | Color | Usage |
|-------|-------|-------|
| `--color-urgency-immediate` | #DC2626/#EF4444 | Critical urgency |
| `--color-urgency-urgent` | #F97316/#FB923C | High urgency |
| `--color-urgency-soon` | #EAB308/#FACC15 | Medium urgency |
| `--color-urgency-watch` | #6B7280/#9CA3AF | Low urgency |
| `--color-severity-critical` | #DC2626/#EF4444 | Critical severity |
| `--color-severity-high` | #F97316/#FB923C | High severity |
| `--color-severity-medium` | #EAB308/#FACC15 | Medium severity |
| `--color-severity-low` | #22C55E/#00FF94 | Low severity |
| `--color-success` | #22C55E/#00FF94 | Success states |
| `--color-error` | #EF4444/#F87171 | Error states |
| `--color-warning` | #F59E0B/#FBBF24 | Warning states |
| `--color-info` | #3B82F6/#00F5FF | Info states |

### Chart Colors

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| `--chart-1` | #2563EB | #00F5FF |
| `--chart-2` | #16A34A | #00FF94 |
| `--chart-3` | #9333EA | #A78BFA |
| `--chart-4` | #D97706 | #FACC15 |
| `--chart-5` | #DC2626 | #EF4444 |
| `--chart-grid` | rgba(0,0,0,0.06) | rgba(100,116,139,0.15) |
| `--chart-axis` | #64748B | #64748B |

## Tailwind Usage

### Using Theme-Aware Classes

```tsx
// ❌ DON'T: Hardcoded colors
<div className="bg-slate-900 text-white border-slate-700">

// ✅ DO: Theme-aware tokens
<div className="bg-card text-foreground border-border">
```

### Common Mappings

| Hardcoded | Theme-Aware |
|-----------|-------------|
| `bg-slate-900` | `bg-card` or `bg-background` |
| `bg-slate-800` | `bg-muted` |
| `bg-white` | `bg-card` |
| `text-white` | `text-foreground` |
| `text-slate-400` | `text-muted-foreground` |
| `border-slate-700` | `border-border` |

### Terminal Effects (Dark-Only)

```tsx
// Terminal glow only appears in dark mode
<div className="shadow-glow-cyan dark:shadow-glow-cyan">
  {/* Glow effect will only show in dark mode */}
</div>

// Using CSS variables for conditional effects
.terminal-glow {
  box-shadow: var(--terminal-glow); // 'none' in light, glow in dark
}
```

## Components

### Theme Toggle (TopBar)

The theme toggle in TopBar supports three modes:
- Light
- Dark  
- System (follows OS preference)

```tsx
import { useTheme } from '@/components/ui/theme-provider';

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  
  return (
    <select value={theme} onChange={e => setTheme(e.target.value)}>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
      <option value="system">System</option>
    </select>
  );
}
```

### Badge Variants

The Badge component uses semantic tokens for all variants:

```tsx
// Urgency badges
<Badge variant="immediate" />  // Uses --color-urgency-immediate
<Badge variant="urgent" />     // Uses --color-urgency-urgent
<Badge variant="soon" />       // Uses --color-urgency-soon
<Badge variant="watch" />      // Uses --color-urgency-watch

// Severity badges
<Badge variant="critical" />   // Uses --color-severity-critical
<Badge variant="high" />       // Uses --color-severity-high
<Badge variant="medium" />     // Uses --color-severity-medium
<Badge variant="low" />        // Uses --color-severity-low

// Action badges
<Badge variant="reroute" />    // Uses --color-action-reroute
<Badge variant="delay" />      // Uses --color-action-delay
<Badge variant="insure" />     // Uses --color-action-insure
```

### Charts

Charts use the `getChartColors()` helper for runtime theme-aware colors:

```tsx
import { getChartColors } from '@/lib/chart-theme';

function MyChart() {
  const chartColors = useMemo(() => getChartColors(), []);
  
  return (
    <LineChart>
      <XAxis stroke={chartColors.chartAxis} />
      <CartesianGrid stroke={chartColors.chartGrid} />
      <Line stroke={chartColors.chart1} />
    </LineChart>
  );
}
```

## File Changes Summary

### Core Theme Files
- `frontend/src/index.css` - CSS variables for both themes
- `frontend/src/components/ui/theme-provider.tsx` - React context provider
- `frontend/src/lib/chart-theme.ts` - Chart-specific theme utilities

### Layout Components
- `frontend/src/components/domain/layout/TopBar.tsx` - Theme toggle, dropdowns
- `frontend/src/components/domain/layout/Sidebar.tsx` - Already migrated

### UI Components
- `frontend/src/components/ui/badge.tsx` - Semantic variant colors
- `frontend/src/components/ui/language-switcher.tsx` - Theme-aware styling

### Domain Components
- `frontend/src/components/domain/signals/SignalCard.tsx`
- `frontend/src/components/domain/signals/EvidenceList.tsx`
- `frontend/src/components/domain/decisions/DecisionCard.tsx`

### Chart Components
- `frontend/src/components/charts/ExposureChart.tsx`
- `frontend/src/components/charts/ConfidenceGauge.tsx`
- `frontend/src/components/charts/CostEscalationChart.tsx`
- `frontend/src/components/charts/TimelineVisualization.tsx`
- `frontend/src/components/charts/ScenarioVisualization.tsx`
- `frontend/src/components/charts/CausalChainDiagram.tsx`

### Page Components
- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/app/signals/page.tsx`
- `frontend/src/app/signals/[id]/page.tsx`
- `frontend/src/app/decisions/page.tsx`
- `frontend/src/app/customers/page.tsx`
- `frontend/src/app/customers/[id]/page.tsx`
- `frontend/src/app/human-review/page.tsx`
- `frontend/src/app/human-review/[id]/page.tsx`
- `frontend/src/app/analytics/page.tsx`
- `frontend/src/app/audit/page.tsx`
- `frontend/src/app/reality/page.tsx`
- `frontend/src/app/settings/page.tsx`

## Testing Checklist

### Visual Verification

For each page, verify in both Light and Dark mode:

- [ ] Background colors render correctly
- [ ] Text is readable with proper contrast
- [ ] Borders are visible but not harsh
- [ ] Status badges show correct colors
- [ ] Charts render with appropriate colors
- [ ] Hover/focus states work properly
- [ ] No visual glitches during theme transition

### Functional Verification

- [ ] Theme toggle works in TopBar
- [ ] Theme persists across page refresh (localStorage)
- [ ] System preference is respected when set to "System"
- [ ] Theme changes are instant with smooth transition

### Accessibility

- [ ] WCAG AAA contrast ratios maintained in both modes
- [ ] Focus indicators visible in both modes
- [ ] Reduced motion preference respected

## Best Practices

### DO

1. Use semantic color tokens (`bg-card`, `text-foreground`, etc.)
2. Use CSS variables for inline styles in charts
3. Test changes in BOTH light and dark modes
4. Keep urgency/severity colors consistent (they carry meaning)

### DON'T

1. Use hardcoded hex colors (`#0F172A`, etc.)
2. Use `dark:` Tailwind prefix (use CSS variables instead)
3. Forget to test light mode (it's easy to overlook)
4. Apply terminal glow effects in light mode

## Troubleshooting

### Theme not changing?
Check that `ThemeProvider` wraps your app in `main.tsx`.

### Colors look wrong in one mode?
Ensure you're using semantic tokens, not hardcoded colors.

### Charts not updating with theme?
Use `getChartColors()` hook with `useMemo` and ensure it's called on render.

### Glow effects showing in light mode?
Use `var(--terminal-glow)` which is set to `none` in light mode.
