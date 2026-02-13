/**
 * CausalChainDiagram - AI Risk Terminal Style
 *
 * Premium causal chain flowchart with terminal aesthetics
 * Features: HUD nodes, data flow animation, confidence indicators
 */

import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { formatPercentage } from '@/lib/formatters';
import { AlertTriangle, CheckCircle, Zap, ArrowRight, Activity, Radio } from 'lucide-react';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';
import type { CausalLink } from '@/types/decision';

interface CausalChainDiagramProps {
  causalChain: CausalLink[];
  rootCause: string;
  className?: string;
  animate?: boolean;
}

export function CausalChainDiagram({
  causalChain,
  rootCause,
  className,
  animate = true,
}: CausalChainDiagramProps) {
  const chartColors = useChartColors();

  const events = extractEventsFromChain(causalChain, rootCause);
  const avgConfidence =
    causalChain.length > 0
      ? causalChain.reduce((sum, c) => sum + c.confidence, 0) / causalChain.length
      : 0;

  return (
    <motion.div
      className={cn('space-y-4', className)}
      role="img"
      aria-label={`Causal chain diagram showing ${causalChain.length} linked events from root cause: ${rootCause}`}
      initial={animate ? { opacity: 0 } : undefined}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <span className="sr-only">
        {`Root cause: ${rootCause}. Chain: ${causalChain.length} events linked.`}
      </span>
      {/* Status Bar */}
      <motion.div
        className="flex items-center justify-between p-3 rounded-xl bg-muted/50 border border-border"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="flex items-center gap-2">
          <motion.div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: chartColors.cyan.primary }}
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className="text-xs font-mono text-info uppercase">
            Causal Analysis
          </span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-mono">
              <span className="text-muted-foreground">Events:</span>
              <span className="text-foreground font-bold ml-1">{events.length}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Radio className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-mono">
              <span className="text-muted-foreground">Avg Conf:</span>
              <span
                className={cn(
                  'font-bold ml-1',
                  avgConfidence >= 0.8
                    ? 'text-confidence-high'
                    : avgConfidence >= 0.6
                      ? 'text-confidence-medium'
                      : 'text-confidence-low',
                )}
              >
                {formatPercentage(avgConfidence)}
              </span>
            </span>
          </div>
        </div>
      </motion.div>

      {/* Horizontal Flow Diagram - Desktop */}
      <div className="hidden md:block overflow-x-auto pb-4">
        <motion.div
          className="flex items-stretch gap-0 min-w-fit"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          <AnimatePresence>
            {events.map((event, index) => (
              <motion.div key={index} className="flex items-center" variants={staggerItem}>
                <TerminalEventNode
                  event={event}
                  isFirst={index === 0}
                  isLast={index === events.length - 1}
                  index={index}
                  animate={animate}
                />

                {index < events.length - 1 && (
                  <TerminalArrowConnector
                    confidence={causalChain[index]?.confidence || 0.8}
                    relationship={causalChain[index]?.relationship || ''}
                    index={index}
                    animate={animate}
                  />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Vertical Flow Diagram - Mobile */}
      <div className="md:hidden space-y-0">
        <motion.div variants={staggerContainer} initial="hidden" animate="visible">
          {events.map((event, index) => (
            <motion.div key={index} className="relative" variants={staggerItem}>
              <TerminalEventNodeMobile
                event={event}
                isFirst={index === 0}
                isLast={index === events.length - 1}
                confidence={index > 0 ? causalChain[index - 1]?.confidence || 0.8 : null}
                index={index}
                animate={animate}
              />

              {index < events.length - 1 && (
                <TerminalVerticalConnector
                  confidence={causalChain[index]?.confidence || 0.8}
                  index={index}
                  animate={animate}
                />
              )}
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Legend */}
      <motion.div
        className="flex flex-wrap items-center justify-center gap-4 pt-3 border-t border-border text-xs font-mono"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {[
          { color: chartColors.green.primary, label: 'High (>80%)' },
          { color: chartColors.amber.primary, label: 'Medium (60-80%)' },
          { color: chartColors.red.primary, label: 'Low (<60%)' },
        ].map(({ color, label }) => (
          <motion.div key={label} variants={staggerItem} className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{
                backgroundColor: color,
                boxShadow: chartColors.isDark ? `0 0 10px ${color}50` : 'none',
              }}
            />
            <span className="text-muted-foreground">{label}</span>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}

function extractEventsFromChain(chain: CausalLink[], rootCause: string): EventData[] {
  if (chain.length === 0) {
    return [{ label: rootCause, type: 'root' }];
  }

  const events: EventData[] = [];
  events.push({ label: chain[0]?.from_event || rootCause, type: 'root' });

  chain.forEach((link, index) => {
    const type = index === chain.length - 1 ? 'impact' : 'intermediate';
    events.push({ label: link.to_event, type });
  });

  return events;
}

interface EventData {
  label: string;
  type: 'root' | 'intermediate' | 'impact';
}

interface TerminalEventNodeProps {
  event: EventData;
  isFirst: boolean;
  isLast: boolean;
  index: number;
  animate?: boolean;
}

function TerminalEventNode({
  event,
  isFirst: _isFirst,
  isLast: _isLast,
  index,
  animate = true,
}: TerminalEventNodeProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const nodeConfig = {
    root: {
      icon: AlertTriangle,
      color: chartColors.red.primary,
      glow: chartColors.red.glow,
      dim: chartColors.red.dim,
      label: 'ROOT CAUSE',
    },
    intermediate: {
      icon: Zap,
      color: chartColors.slate.primary,
      glow: 'transparent',
      dim: chartColors.slate.dim,
      label: 'EFFECT',
    },
    impact: {
      icon: CheckCircle,
      color: chartColors.cyan.primary,
      glow: chartColors.cyan.glow,
      dim: chartColors.cyan.dim,
      label: 'YOUR IMPACT',
    },
  };

  const config = nodeConfig[event.type];
  const Icon = config.icon;

  return (
    <motion.div
      className={cn(
        'relative flex flex-col items-center justify-center min-w-[160px] max-w-[200px] p-5 rounded-xl border-2 transition-all',
        'bg-card',
      )}
      style={{
        borderColor: config.color,
        boxShadow: event.type !== 'intermediate' && isDark ? `0 0 30px ${config.glow}` : 'none',
      }}
      initial={animate ? { scale: 0, opacity: 0 } : undefined}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: 0.2 + index * 0.15, ...springs.bouncy }}
      whileHover={{ scale: 1.05, y: -4 }}
    >
      {/* Corner decorations */}
      <div
        className="absolute top-0 left-0 w-2 h-2 border-l border-t"
        style={{ borderColor: config.color }}
      />
      <div
        className="absolute top-0 right-0 w-2 h-2 border-r border-t"
        style={{ borderColor: config.color }}
      />
      <div
        className="absolute bottom-0 left-0 w-2 h-2 border-l border-b"
        style={{ borderColor: config.color }}
      />
      <div
        className="absolute bottom-0 right-0 w-2 h-2 border-r border-b"
        style={{ borderColor: config.color }}
      />

      {/* Badge */}
      <motion.span
        className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded text-[8px] font-mono font-bold uppercase tracking-wider text-white"
        style={{
          background: `linear-gradient(135deg, ${config.color}, ${config.color}80)`,
          boxShadow: isDark ? `0 0 15px ${config.glow}` : 'none',
        }}
        initial={animate ? { scale: 0, y: 10 } : undefined}
        animate={{ scale: 1, y: 0 }}
        transition={{ delay: 0.4 + index * 0.15, ...springs.bouncy }}
      >
        {config.label}
      </motion.span>

      {/* Icon with glow */}
      <motion.div
        className="relative mb-3"
        initial={animate ? { rotate: -180, opacity: 0 } : undefined}
        animate={{ rotate: 0, opacity: 1 }}
        transition={{ delay: 0.3 + index * 0.15, ...springs.smooth }}
      >
        {event.type !== 'intermediate' && isDark && (
          <motion.div
            className="absolute inset-0 rounded-full blur-md"
            style={{ backgroundColor: config.color }}
            animate={{ scale: [1, 1.5, 1], opacity: [0.3, 0.1, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
        <Icon className="h-6 w-6 relative" style={{ color: config.color }} />
      </motion.div>

      {/* Label */}
      <motion.p
        className={cn(
          'text-sm font-mono font-semibold text-center leading-tight',
          event.type === 'intermediate' ? 'text-foreground' : '',
        )}
        style={{ color: event.type !== 'intermediate' ? config.color : undefined }}
        initial={animate ? { opacity: 0, y: 5 } : undefined}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 + index * 0.15 }}
      >
        {event.label}
      </motion.p>
    </motion.div>
  );
}

interface TerminalArrowConnectorProps {
  confidence: number;
  relationship: string;
  index: number;
  animate?: boolean;
}

function TerminalArrowConnector({
  confidence,
  relationship,
  index,
  animate = true,
}: TerminalArrowConnectorProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const config =
    confidence >= 0.8
      ? { color: chartColors.green.primary, glow: chartColors.green.glow }
      : confidence >= 0.6
        ? { color: chartColors.amber.primary, glow: chartColors.amber.glow }
        : { color: chartColors.red.primary, glow: chartColors.red.glow };

  return (
    <motion.div
      className="flex flex-col items-center mx-3"
      initial={animate ? { opacity: 0, scale: 0.5 } : undefined}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.5 + index * 0.15, ...springs.smooth }}
    >
      {/* Confidence Score */}
      <motion.div
        className="px-2 py-1 rounded text-[10px] font-mono font-bold mb-2 text-white"
        style={{
          background: `linear-gradient(135deg, ${config.color}, ${config.color}80)`,
          boxShadow: isDark ? `0 0 10px ${config.glow}` : 'none',
        }}
        initial={animate ? { opacity: 0, y: -10 } : undefined}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 + index * 0.15 }}
      >
        {formatPercentage(confidence)}
      </motion.div>

      {/* Arrow with data flow animation */}
      <div className="relative flex items-center">
        <motion.div
          className="h-0.5 w-12 rounded-full"
          style={{
            backgroundColor: config.color,
            boxShadow: isDark ? `0 0 10px ${config.glow}` : 'none',
          }}
          initial={animate ? { scaleX: 0 } : undefined}
          animate={{ scaleX: 1 }}
          transition={{ delay: 0.55 + index * 0.15, duration: 0.3 }}
        />

        {/* Animated data flow particles - dark mode only */}
        {isDark && (
          <>
            <motion.div
              className="absolute left-0 h-2 w-2 rounded-full"
              style={{ backgroundColor: config.color }}
              animate={{ x: [0, 48], opacity: [0, 1, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: index * 0.2 }}
            />
            <motion.div
              className="absolute left-0 h-1 w-1 rounded-full"
              style={{ backgroundColor: config.color }}
              animate={{ x: [0, 48], opacity: [0, 1, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: index * 0.2 + 0.5 }}
            />
          </>
        )}

        <motion.div
          initial={animate ? { opacity: 0, x: -5 } : undefined}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.7 + index * 0.15, ...springs.snappy }}
        >
          <ArrowRight className="h-5 w-5" style={{ color: config.color }} />
        </motion.div>
      </div>

      {/* Relationship Label */}
      {relationship && (
        <motion.span
          className="text-[9px] font-mono text-muted-foreground mt-2 max-w-[100px] text-center leading-tight"
          initial={animate ? { opacity: 0 } : undefined}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.75 + index * 0.15 }}
        >
          {relationship}
        </motion.span>
      )}
    </motion.div>
  );
}

interface TerminalEventNodeMobileProps {
  event: EventData;
  isFirst: boolean;
  isLast: boolean;
  confidence: number | null;
  index: number;
  animate?: boolean;
}

function TerminalEventNodeMobile({
  event,
  isFirst: _isFirst,
  isLast: _isLast,
  confidence,
  index,
  animate = true,
}: TerminalEventNodeMobileProps) {
  const chartColors = useChartColors();

  const nodeConfig = {
    root: { color: chartColors.red.primary, label: 'ROOT' },
    intermediate: { color: chartColors.slate.primary, label: 'EFFECT' },
    impact: { color: chartColors.cyan.primary, label: 'IMPACT' },
  };

  const config = nodeConfig[event.type];

  const confidenceColor = confidence
    ? confidence >= 0.8
      ? chartColors.green.primary
      : confidence >= 0.6
        ? chartColors.amber.primary
        : chartColors.red.primary
    : chartColors.slate.primary;

  return (
    <motion.div
      className="flex items-start gap-4"
      initial={animate ? { opacity: 0, x: -20 } : undefined}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2 + index * 0.1, ...springs.smooth }}
    >
      {/* Timeline dot */}
      <div className="flex flex-col items-center pt-4">
        <motion.div
          className="h-5 w-5 rounded-full border-2 flex items-center justify-center"
          style={{ borderColor: config.color }}
          initial={animate ? { scale: 0 } : undefined}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3 + index * 0.1, ...springs.bouncy }}
        >
          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: config.color }} />
        </motion.div>
      </div>

      {/* Content Card */}
      <motion.div
        className="flex-1 p-4 rounded-xl border-2 mb-3 bg-card"
        style={{ borderColor: config.color }}
        whileHover={{ scale: 1.02, x: 4 }}
        transition={springs.snappy}
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span
            className="text-[9px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded"
            style={{ backgroundColor: `${config.color}20`, color: config.color }}
          >
            {config.label}
          </span>
          {confidence !== null && (
            <span
              className="text-[9px] font-mono font-bold px-2 py-0.5 rounded"
              style={{ backgroundColor: `${confidenceColor}20`, color: confidenceColor }}
            >
              {formatPercentage(confidence)}
            </span>
          )}
        </div>
        <p className="text-sm font-mono font-semibold text-foreground">{event.label}</p>
      </motion.div>
    </motion.div>
  );
}

interface TerminalVerticalConnectorProps {
  confidence: number;
  index: number;
  animate?: boolean;
}

function TerminalVerticalConnector({
  confidence,
  index,
  animate = true,
}: TerminalVerticalConnectorProps) {
  const chartColors = useChartColors();

  const config =
    confidence >= 0.8
      ? { color: chartColors.green.primary }
      : confidence >= 0.6
        ? { color: chartColors.amber.primary }
        : { color: chartColors.red.primary };

  return (
    <motion.div
      className="flex items-center gap-4 py-1"
      initial={animate ? { opacity: 0 } : undefined}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.4 + index * 0.1 }}
    >
      <div className="flex flex-col items-center">
        <motion.div
          className="w-0.5 h-8 rounded-full"
          style={{ backgroundColor: config.color }}
          initial={animate ? { scaleY: 0 } : undefined}
          animate={{ scaleY: 1 }}
          transition={{ delay: 0.45 + index * 0.1, duration: 0.2 }}
        />
      </div>
      <div className="flex-1" />
    </motion.div>
  );
}

export default CausalChainDiagram;
