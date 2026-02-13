/**
 * ScenarioVisualization - AI Risk Terminal Style
 *
 * Premium scenario comparison with terminal aesthetics
 * Features: Data-dense cards, probability matrix, expected value calculator
 */

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { formatCurrency, formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Activity,
  Target,
  Zap,
} from 'lucide-react';

export interface Scenario {
  id: string;
  name: string;
  type: 'best' | 'base' | 'worst';
  probability: number;
  cost_usd: number;
  delay_days: number;
  description: string;
  key_assumptions: string[];
}

interface ScenarioVisualizationProps {
  scenarios: Scenario[];
  currentChoice?: 'best' | 'base' | 'worst';
  className?: string;
  animate?: boolean;
}

export function ScenarioVisualization({
  scenarios,
  currentChoice = 'base',
  className,
  animate = true,
}: ScenarioVisualizationProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const orderedScenarios = ['best', 'base', 'worst'].map(
    (type) =>
      scenarios.find((s) => s.type === type) || createDefaultScenario(type as Scenario['type']),
  );

  const expectedValue = calculateExpectedValue(orderedScenarios);
  const totalProbability = orderedScenarios.reduce((sum, s) => sum + s.probability, 0);

  return (
    <motion.div
      className={cn('space-y-6', className)}
      role="img"
      aria-label={`Scenario comparison showing ${scenarios.length} possible outcomes`}
      initial={animate ? { opacity: 0 } : undefined}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <span className="sr-only">
        {`Scenario analysis: ${scenarios.length} scenarios compared. Current selection: ${currentChoice}.`}
      </span>
      {/* Summary Stats Bar */}
      <motion.div
        className="grid grid-cols-3 gap-3 p-3 rounded-xl bg-muted/50 border border-border"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="text-center">
          <p className="text-[9px] font-mono text-muted-foreground uppercase">Expected Cost</p>
          <p
            className="text-lg font-mono font-bold text-info"
            style={{ textShadow: isDark ? `0 0 10px ${chartColors.cyan.glow}` : 'none' }}
          >
            {formatCurrency(expectedValue, { compact: true })}
          </p>
        </div>
        <div className="text-center border-x border-border">
          <p className="text-[9px] font-mono text-muted-foreground uppercase">Scenarios</p>
          <p className="text-lg font-mono font-bold text-foreground">{orderedScenarios.length}</p>
        </div>
        <div className="text-center">
          <p className="text-[9px] font-mono text-muted-foreground uppercase">Coverage</p>
          <p className="text-lg font-mono font-bold text-success">
            {formatPercentage(totalProbability)}
          </p>
        </div>
      </motion.div>

      {/* Scenario Cards */}
      <motion.div
        className="grid gap-4 md:grid-cols-3"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {orderedScenarios.map((scenario, index) => (
          <motion.div key={scenario.id} variants={staggerItem}>
            <TerminalScenarioCard
              scenario={scenario}
              isSelected={scenario.type === currentChoice}
              index={index}
              animate={animate}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Probability Distribution Bar */}
      <motion.div
        className="space-y-3 p-4 rounded-xl bg-muted/50 border border-border"
        initial={animate ? { opacity: 0, y: 20 } : undefined}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, ...springs.smooth }}
      >
        <div className="flex items-center justify-between">
          <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
            Probability Distribution
          </p>
          <div className="flex items-center gap-1">
            <Activity className="h-3 w-3 text-muted-foreground/70" />
            <span className="text-[9px] font-mono text-muted-foreground/70">Weighted Analysis</span>
          </div>
        </div>

        <ProbabilityBar scenarios={orderedScenarios} animate={animate} />

        <div className="flex justify-between text-[10px] font-mono px-1">
          <span className="flex items-center gap-1 text-success">
            <CheckCircle className="h-3 w-3" /> Best
          </span>
          <span className="flex items-center gap-1 text-warning">
            <Minus className="h-3 w-3" /> Base
          </span>
          <span className="flex items-center gap-1 text-severity-critical">
            <AlertTriangle className="h-3 w-3" /> Worst
          </span>
        </div>
      </motion.div>

      {/* Expected Value Calculator */}
      <motion.div
        className="rounded-xl bg-muted/40 border p-5 space-y-3"
        style={{
          borderColor: isDark ? `${chartColors.cyan.primary}4D` : chartColors.cyan.dim,
          boxShadow: isDark ? `0 0 30px ${chartColors.cyan.dim}` : 'none',
        }}
        initial={animate ? { opacity: 0, scale: 0.95 } : undefined}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.8, ...springs.smooth }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <motion.div
              className="p-2 rounded-lg border"
              style={{
                backgroundColor: chartColors.cyan.dim,
                borderColor: `${chartColors.cyan.primary}4D`,
              }}
              animate={
                isDark
                  ? {
                      boxShadow: [
                        `0 0 10px ${chartColors.cyan.dim}`,
                        `0 0 20px ${chartColors.cyan.glow}`,
                        `0 0 10px ${chartColors.cyan.dim}`,
                      ],
                    }
                  : undefined
              }
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Target className="h-4 w-4 text-info" />
            </motion.div>
            <div>
              <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                Expected Value
              </p>
              <p className="text-[9px] font-mono text-muted-foreground/70">
                E[X] = Σ P(x) × Cost(x)
              </p>
            </div>
          </div>
          <motion.p
            className="font-mono text-3xl font-black text-info"
            style={{ textShadow: isDark ? `0 0 30px ${chartColors.cyan.glow}` : 'none' }}
            initial={animate ? { scale: 0 } : undefined}
            animate={{ scale: 1 }}
            transition={{ delay: 1, ...springs.bouncy }}
          >
            {formatCurrency(expectedValue, { compact: true })}
          </motion.p>
        </div>

        <div className="pt-3 border-t border-border">
          <div className="flex flex-wrap gap-2 text-[10px] font-mono text-muted-foreground">
            {orderedScenarios.map((s, i) => (
              <span key={s.id}>
                <span
                  className={cn(
                    s.type === 'best'
                      ? 'text-success'
                      : s.type === 'base'
                        ? 'text-warning'
                        : 'text-severity-critical',
                  )}
                >
                  {formatPercentage(s.probability)}
                </span>
                <span className="text-muted-foreground/70"> × </span>
                <span className="text-foreground/80">
                  {formatCurrency(s.cost_usd, { compact: true })}
                </span>
                {i < orderedScenarios.length - 1 && (
                  <span className="text-muted-foreground/70 mx-1">+</span>
                )}
              </span>
            ))}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ─── Probability distribution bar ─── */

function ProbabilityBar({ scenarios, animate }: { scenarios: Scenario[]; animate: boolean }) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  return (
    <div className="h-6 rounded-lg overflow-hidden flex bg-card border border-border">
      {scenarios.map((scenario, index) => {
        const colors = {
          best: {
            bg: `linear-gradient(90deg, ${chartColors.green.tertiary}, ${chartColors.green.primary})`,
            glow: chartColors.green.glow,
          },
          base: {
            bg: `linear-gradient(90deg, ${chartColors.amber.tertiary}, ${chartColors.amber.primary})`,
            glow: chartColors.amber.glow,
          },
          worst: {
            bg: `linear-gradient(90deg, ${chartColors.red.tertiary}, ${chartColors.red.primary})`,
            glow: chartColors.red.glow,
          },
        };
        const color = colors[scenario.type];

        return (
          <motion.div
            key={scenario.id}
            className="h-full relative flex items-center justify-center text-[10px] font-mono font-bold text-white"
            style={{
              background: color.bg,
              boxShadow: isDark ? `inset 0 0 10px ${color.glow}` : 'none',
            }}
            initial={animate ? { width: 0 } : undefined}
            animate={{ width: `${scenario.probability * 100}%` }}
            transition={{ delay: 0.7 + index * 0.1, duration: 0.5, ease: 'easeOut' }}
            title={`${scenario.name}: ${formatPercentage(scenario.probability)}`}
          >
            {scenario.probability >= 0.15 && (
              <span className="drop-shadow-lg">{formatPercentage(scenario.probability)}</span>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

/* ─── Scenario card ─── */

interface TerminalScenarioCardProps {
  scenario: Scenario;
  isSelected?: boolean;
  index: number;
  animate?: boolean;
}

function TerminalScenarioCard({
  scenario,
  isSelected,
  index,
  animate = true,
}: TerminalScenarioCardProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const cfg = {
    best: {
      icon: TrendingDown,
      color: chartColors.green.primary,
      glow: chartColors.green.glow,
      dim: chartColors.green.dim,
      label: 'BEST CASE',
    },
    base: {
      icon: Minus,
      color: chartColors.amber.primary,
      glow: chartColors.amber.glow,
      dim: chartColors.amber.dim,
      label: 'BASE CASE',
    },
    worst: {
      icon: TrendingUp,
      color: chartColors.red.primary,
      glow: chartColors.red.glow,
      dim: chartColors.red.dim,
      label: 'WORST CASE',
    },
  };

  const c = cfg[scenario.type];
  const Icon = c.icon;

  return (
    <motion.div
      className={cn(
        'relative rounded-xl border-2 p-5 space-y-4 transition-all overflow-hidden',
        'bg-card',
        isSelected ? 'border-current' : 'border-border hover:border-border/80',
      )}
      style={{
        borderColor: isSelected ? c.color : undefined,
        boxShadow: isSelected && isDark ? `0 0 30px ${c.glow}` : 'none',
      }}
      initial={animate ? { opacity: 0, y: 30 } : undefined}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 + index * 0.1, ...springs.smooth }}
      whileHover={{ y: -4, scale: 1.02 }}
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${c.color}, transparent)` }}
      />

      {/* Corner decorations */}
      <div
        className="absolute top-0 left-0 w-2 h-2 border-l border-t"
        style={{ borderColor: c.color, opacity: 0.5 }}
      />
      <div
        className="absolute top-0 right-0 w-2 h-2 border-r border-t"
        style={{ borderColor: c.color, opacity: 0.5 }}
      />
      <div
        className="absolute bottom-0 left-0 w-2 h-2 border-l border-b"
        style={{ borderColor: c.color, opacity: 0.5 }}
      />
      <div
        className="absolute bottom-0 right-0 w-2 h-2 border-r border-b"
        style={{ borderColor: c.color, opacity: 0.5 }}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <motion.div
            className="p-2 rounded-lg border"
            style={{
              background: c.dim,
              borderColor: `${c.color}50`,
            }}
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={springs.bouncy}
          >
            <Icon className="h-4 w-4" style={{ color: c.color }} />
          </motion.div>
          <span
            className="text-[10px] font-mono font-bold uppercase tracking-wider"
            style={{ color: c.color }}
          >
            {c.label}
          </span>
        </div>
        <motion.span
          className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold text-white"
          style={{
            background: `linear-gradient(135deg, ${c.color}, ${c.color}80)`,
            boxShadow: isDark ? `0 0 15px ${c.glow}` : 'none',
          }}
          whileHover={{ scale: 1.05 }}
        >
          {formatPercentage(scenario.probability)}
        </motion.span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          className="p-3 rounded-lg bg-muted/50 border border-border"
          whileHover={{ scale: 1.02 }}
          transition={springs.snappy}
        >
          <div className="flex items-center gap-1 mb-1">
            <DollarSign className="h-3 w-3 text-muted-foreground" />
            <p className="text-[9px] font-mono text-muted-foreground uppercase">Cost</p>
          </div>
          <p className="font-mono text-xl font-bold" style={{ color: c.color }}>
            {formatCurrency(scenario.cost_usd, { compact: true })}
          </p>
        </motion.div>

        <motion.div
          className="p-3 rounded-lg bg-muted/50 border border-border"
          whileHover={{ scale: 1.02 }}
          transition={springs.snappy}
        >
          <div className="flex items-center gap-1 mb-1">
            <Clock className="h-3 w-3 text-muted-foreground" />
            <p className="text-[9px] font-mono text-muted-foreground uppercase">Delay</p>
          </div>
          <p className="font-mono text-xl font-bold text-foreground">{scenario.delay_days}d</p>
        </motion.div>
      </div>

      {/* Description */}
      <p className="text-xs text-muted-foreground leading-relaxed font-mono">
        {scenario.description}
      </p>

      {/* Key Assumptions */}
      {scenario.key_assumptions.length > 0 && (
        <div className="pt-3 border-t border-border space-y-2">
          <p className="text-[9px] font-mono font-bold uppercase tracking-wider text-muted-foreground/70">
            Key Assumptions
          </p>
          <ul className="space-y-1">
            {scenario.key_assumptions.slice(0, 2).map((assumption, i) => (
              <motion.li
                key={i}
                className="flex items-start gap-2 text-[10px] text-muted-foreground font-mono"
                initial={animate ? { opacity: 0, x: -10 } : undefined}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + index * 0.1 + i * 0.1 }}
              >
                <Zap className="h-3 w-3 flex-shrink-0 mt-0.5" style={{ color: c.color }} />
                <span>{assumption}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}

function calculateExpectedValue(scenarios: Scenario[]): number {
  return scenarios.reduce((sum, s) => sum + s.probability * s.cost_usd, 0);
}

function createDefaultScenario(type: Scenario['type']): Scenario {
  const defaults = {
    best: {
      id: 'default-best',
      name: 'Best Case',
      type: 'best' as const,
      probability: 0.15,
      cost_usd: 5000,
      delay_days: 0,
      description: 'Disruption resolves quickly, minimal impact',
      key_assumptions: ['Situation de-escalates', 'Routes reopen'],
    },
    base: {
      id: 'default-base',
      name: 'Base Case',
      type: 'base' as const,
      probability: 0.6,
      cost_usd: 25000,
      delay_days: 7,
      description: 'Expected outcome based on current intelligence',
      key_assumptions: ['Current trends continue', 'No major surprises'],
    },
    worst: {
      id: 'default-worst',
      name: 'Worst Case',
      type: 'worst' as const,
      probability: 0.25,
      cost_usd: 75000,
      delay_days: 21,
      description: 'Situation deteriorates significantly',
      key_assumptions: ['Escalation occurs', 'Extended disruption'],
    },
  };

  return defaults[type];
}

export function createScenariosFromDecision(baseExposure: number, baseDelay: number): Scenario[] {
  return [
    {
      id: 'best',
      name: 'Best Case',
      type: 'best',
      probability: 0.15,
      cost_usd: baseExposure * 0.3,
      delay_days: Math.max(0, baseDelay - 5),
      description: 'Disruption resolves faster than expected',
      key_assumptions: ['Quick de-escalation', 'Routes reopen early'],
    },
    {
      id: 'base',
      name: 'Base Case',
      type: 'base',
      probability: 0.6,
      cost_usd: baseExposure,
      delay_days: baseDelay,
      description: 'Expected outcome based on current analysis',
      key_assumptions: ['Current intelligence is accurate', 'No major changes'],
    },
    {
      id: 'worst',
      name: 'Worst Case',
      type: 'worst',
      probability: 0.25,
      cost_usd: baseExposure * 2.5,
      delay_days: baseDelay + 14,
      description: 'Situation worsens significantly',
      key_assumptions: ['Escalation occurs', 'Extended disruption'],
    },
  ];
}

export default ScenarioVisualization;
