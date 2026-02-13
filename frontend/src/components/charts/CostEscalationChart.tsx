/**
 * CostEscalationChart - AI Risk Terminal Style
 *
 * Premium cost escalation visualization with terminal aesthetics
 * Features: Animated line, danger indicators, HUD elements, real-time feel
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';
import {
  AlertTriangle,
  Clock,
  Flame,
  DollarSign,
  Skull,
  Radio,
  Target,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CostEscalationPoint } from '@/types/decision';

interface CostEscalationChartProps {
  data: CostEscalationPoint[];
  currentTime?: Date;
  pointOfNoReturn?: string;
  className?: string;
  animate?: boolean;
}

export function CostEscalationChart({
  data,
  currentTime = new Date(),
  pointOfNoReturn,
  className,
  animate = true,
}: CostEscalationChartProps) {
  const [isAnimated, setIsAnimated] = useState(!animate);
  const [scanPosition, setScanPosition] = useState(0);
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  useEffect(() => {
    if (animate) {
      const timer = setTimeout(() => setIsAnimated(true), 500);
      return () => clearTimeout(timer);
    }
  }, [animate]);

  // Scan line animation - dark mode only
  useEffect(() => {
    if (!isDark) return;
    const interval = setInterval(() => {
      setScanPosition((p) => (p + 1) % 100);
    }, 50);
    return () => clearInterval(interval);
  }, [isDark]);

  const chartData = data.map((point, index) => ({
    timestamp: new Date(point.timestamp).getTime(),
    cost: isAnimated ? point.cost_usd : 0,
    description: point.description,
    label: formatDate(point.timestamp, { includeTime: true }),
    progress: index / (data.length - 1),
    index,
  }));

  const currentTimestamp = currentTime.getTime();
  const pointOfNoReturnTimestamp = pointOfNoReturn ? new Date(pointOfNoReturn).getTime() : null;

  const minCost = Math.min(...data.map((d) => d.cost_usd));
  const maxCost = Math.max(...data.map((d) => d.cost_usd));
  const yDomain = [Math.floor(minCost * 0.8), Math.ceil(maxCost * 1.15)];

  const costIncrease = maxCost - minCost;
  const percentIncrease = ((costIncrease / minCost) * 100).toFixed(0);
  const currentCostIndex = data.findIndex(
    (d) => new Date(d.timestamp).getTime() > currentTimestamp,
  );
  const currentCost = currentCostIndex > 0 ? data[currentCostIndex - 1].cost_usd : data[0].cost_usd;
  const finalCost = data[data.length - 1].cost_usd;

  // Time until point of no return
  const timeUntilPONR = pointOfNoReturnTimestamp
    ? Math.max(0, Math.floor((pointOfNoReturnTimestamp - currentTimestamp) / (1000 * 60 * 60)))
    : null;

  return (
    <motion.div
      role="img"
      aria-label="Cost escalation chart showing projected costs over time"
      initial={animate ? { opacity: 0, y: 20 } : undefined}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      <span className="sr-only">
        {`Cost escalation over ${data.length} time points. Maximum projected cost: ${formatCurrency(Math.max(...data.map((d) => d.cost_usd)))}.`}
      </span>
      <Card
        className={cn('overflow-hidden border border-border bg-card relative shadow-sm', className)}
      >
        {/* Top accent line - animated danger gradient */}
        <motion.div
          className="h-px bg-gradient-to-r from-severity-high via-severity-critical to-severity-critical"
          animate={{
            backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
          }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          style={{ backgroundSize: '200% 200%' }}
        />

        {/* Corner decorations */}
        <div className="absolute top-0 left-0 w-3 h-3 border-l border-t border-border" />
        <div className="absolute top-0 right-0 w-3 h-3 border-r border-t border-border" />
        <div className="absolute bottom-0 left-0 w-3 h-3 border-l border-b border-border" />
        <div className="absolute bottom-0 right-0 w-3 h-3 border-r border-b border-border" />

        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <motion.div
                className="p-2.5 rounded-xl bg-gradient-to-br from-severity-critical/20 to-severity-critical/10 border border-severity-critical/30 relative overflow-hidden"
                whileHover={{ scale: 1.05 }}
                transition={springs.bouncy}
              >
                <Flame className="h-5 w-5 text-severity-critical" />
                <motion.div
                  className="absolute inset-0 bg-severity-critical/20"
                  animate={{ opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              </motion.div>
              <div>
                <CardTitle className="text-sm font-mono font-bold uppercase tracking-wider text-severity-critical flex items-center gap-2">
                  Cost Escalation
                  <motion.span
                    className="text-[9px] font-normal px-1.5 py-0.5 rounded bg-severity-critical/10 text-severity-critical border border-severity-critical/30"
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    LIVE
                  </motion.span>
                </CardTitle>
                <p className="text-xs text-muted-foreground font-mono">
                  {data.length} escalation points tracked
                </p>
              </div>
            </div>

            {/* Stats Panel */}
            <motion.div
              className="flex items-center gap-4"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              <motion.div variants={staggerItem} className="text-right">
                <div className="flex items-center gap-1 text-[9px] text-muted-foreground mb-0.5 font-mono uppercase">
                  <DollarSign className="h-3 w-3" />
                  <span>Current</span>
                </div>
                <p className="font-mono text-lg font-bold text-severity-high">
                  {formatCurrency(currentCost, { compact: true })}
                </p>
              </motion.div>

              <motion.div variants={staggerItem} className="text-right">
                <div className="flex items-center gap-1 text-[9px] text-muted-foreground mb-0.5 font-mono uppercase">
                  <Target className="h-3 w-3" />
                  <span>Final</span>
                </div>
                <p className="font-mono text-lg font-bold text-severity-critical">
                  {formatCurrency(finalCost, { compact: true })}
                </p>
              </motion.div>

              <motion.div
                variants={staggerItem}
                className="px-3 py-2 rounded-xl bg-severity-critical/10 border border-severity-critical/30"
              >
                <div className="flex items-center gap-1 text-[9px] mb-0.5 text-severity-critical font-mono uppercase">
                  <AlertTriangle className="h-3 w-3" />
                  <span>Increase</span>
                </div>
                <p
                  className="font-mono text-lg font-bold text-severity-critical"
                  style={{ textShadow: isDark ? '0 0 20px rgba(255, 59, 59, 0.5)' : 'none' }}
                >
                  +{percentIncrease}%
                </p>
              </motion.div>
            </motion.div>
          </div>

          {/* Time Warning Bar */}
          {timeUntilPONR !== null && (
            <motion.div
              className="mt-4 p-3 rounded-xl bg-severity-critical/5 border border-severity-critical/20 flex items-center justify-between"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  <Skull className="h-5 w-5 text-severity-critical" />
                </motion.div>
                <div>
                  <p className="text-xs font-mono text-severity-critical font-bold uppercase">
                    Point of No Return
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground">
                    {formatDate(new Date(pointOfNoReturnTimestamp!), { includeTime: true })}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p
                  className="text-2xl font-mono font-black text-severity-critical"
                  style={{ textShadow: isDark ? '0 0 20px rgba(255, 59, 59, 0.5)' : 'none' }}
                >
                  {timeUntilPONR}h
                </p>
                <p className="text-[9px] font-mono text-muted-foreground uppercase">remaining</p>
              </div>
            </motion.div>
          )}
        </CardHeader>

        <CardContent className="pb-4">
          <motion.div
            className="h-72 relative"
            initial={animate ? { opacity: 0 } : undefined}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            {/* Scan line effect - dark mode only */}
            {isDark && (
              <div
                className="absolute inset-0 pointer-events-none z-20 overflow-hidden"
                style={{ opacity: 0.1 }}
              >
                <div
                  className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-accent to-transparent"
                  style={{ top: `${scanPosition}%` }}
                />
              </div>
            )}

            <ResponsiveContainer width="100%" height="100%" debounce={1}>
              <ComposedChart data={chartData} margin={{ top: 20, right: 30, bottom: 30, left: 20 }}>
                <defs>
                  {/* Area gradient */}
                  <linearGradient id="costAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="0%"
                      stopColor={chartColors.red.primary}
                      stopOpacity={isDark ? 0.4 : 0.25}
                    />
                    <stop
                      offset="30%"
                      stopColor={chartColors.red.primary}
                      stopOpacity={isDark ? 0.2 : 0.12}
                    />
                    <stop offset="70%" stopColor={chartColors.red.primary} stopOpacity={0.05} />
                    <stop offset="100%" stopColor={chartColors.red.primary} stopOpacity={0} />
                  </linearGradient>

                  {/* Line gradient */}
                  <linearGradient id="costLineGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={chartColors.amber.primary} />
                    <stop offset="30%" stopColor={chartColors.red.secondary} />
                    <stop offset="70%" stopColor={chartColors.red.primary} />
                    <stop offset="100%" stopColor={chartColors.red.tertiary} />
                  </linearGradient>

                  {/* Glow filters - dark mode only */}
                  {isDark && (
                    <>
                      <filter id="costLineGlow" x="-50%" y="-50%" width="200%" height="200%">
                        <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                        <feMerge>
                          <feMergeNode in="coloredBlur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                      <filter id="dotGlow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                          <feMergeNode in="coloredBlur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </>
                  )}
                </defs>

                <CartesianGrid
                  strokeDasharray="2 6"
                  stroke={chartColors.chartGrid}
                  vertical={false}
                />

                <XAxis
                  dataKey="timestamp"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => formatDate(new Date(value), { includeTime: false })}
                  stroke={chartColors.mutedForeground}
                  fontSize={10}
                  fontFamily="JetBrains Mono, monospace"
                  tickLine={false}
                  axisLine={{ stroke: chartColors.chartAxis }}
                />

                <YAxis
                  domain={yDomain}
                  tickFormatter={(value) => formatCurrency(value, { compact: true })}
                  stroke={chartColors.mutedForeground}
                  fontSize={10}
                  fontFamily="JetBrains Mono, monospace"
                  tickLine={false}
                  axisLine={false}
                  width={70}
                />

                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <motion.div
                        className="rounded-xl border border-border bg-card p-4 shadow-2xl"
                        initial={{ opacity: 0, scale: 0.9, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        transition={springs.snappy}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                          <p className="text-xs text-foreground/80 font-mono">{d.label}</p>
                        </div>
                        <p
                          className="font-mono text-2xl font-bold text-severity-critical"
                          style={{
                            textShadow: isDark ? '0 0 20px rgba(255, 59, 59, 0.5)' : 'none',
                          }}
                        >
                          {formatCurrency(d.cost)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-2 max-w-[200px] font-mono">
                          {d.description}
                        </p>
                        <div className="mt-3 pt-3 border-t border-border">
                          <div className="flex justify-between">
                            <span className="text-[10px] text-muted-foreground/70 font-mono">
                              Step
                            </span>
                            <span className="text-[10px] text-foreground/80 font-mono">
                              {d.index + 1} of {data.length}
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  }}
                />

                {/* Current time reference line */}
                <ReferenceLine
                  x={currentTimestamp}
                  stroke={chartColors.chart1}
                  strokeDasharray="8 4"
                  strokeWidth={2}
                />

                {/* Point of no return reference line */}
                {pointOfNoReturnTimestamp && (
                  <ReferenceLine
                    x={pointOfNoReturnTimestamp}
                    stroke={chartColors.red.primary}
                    strokeWidth={2}
                  />
                )}

                {/* Area under the line */}
                <Area
                  type="monotone"
                  dataKey="cost"
                  fill="url(#costAreaGradient)"
                  stroke="none"
                  animationBegin={animate ? 0 : undefined}
                  animationDuration={animate ? 2000 : 0}
                  animationEasing="ease-out"
                />

                {/* Main line with glow */}
                <Line
                  type="monotone"
                  dataKey="cost"
                  stroke="url(#costLineGradient)"
                  strokeWidth={3}
                  filter={isDark ? 'url(#costLineGlow)' : undefined}
                  dot={{
                    fill: chartColors.red.primary,
                    strokeWidth: 2,
                    stroke: chartColors.card,
                    r: 5,
                    filter: isDark ? 'url(#dotGlow)' : undefined,
                  }}
                  activeDot={{
                    fill: chartColors.red.primary,
                    strokeWidth: 3,
                    stroke: chartColors.foreground,
                    r: 8,
                    filter: isDark ? 'url(#dotGlow)' : undefined,
                  }}
                  animationBegin={animate ? 0 : undefined}
                  animationDuration={animate ? 2000 : 0}
                  animationEasing="ease-out"
                />
              </ComposedChart>
            </ResponsiveContainer>

            {/* Overlay labels */}
            <AnimatePresence>
              {isAnimated && (
                <>
                  {/* NOW label */}
                  <motion.div
                    className="absolute bg-accent backdrop-blur-sm text-accent-foreground px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold shadow-lg border border-accent/50"
                    style={{
                      left: `calc(${((currentTimestamp - chartData[0]?.timestamp) / (chartData[chartData.length - 1]?.timestamp - chartData[0]?.timestamp)) * 85 + 7}% - 20px)`,
                      top: '10px',
                    }}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1 }}
                  >
                    <span className="flex items-center gap-1">
                      <Radio className="h-3 w-3" />
                      NOW
                    </span>
                  </motion.div>

                  {/* PONR label */}
                  {pointOfNoReturnTimestamp && (
                    <motion.div
                      className="absolute bg-severity-critical backdrop-blur-sm text-destructive-foreground px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold shadow-lg flex items-center gap-1 border border-severity-critical/50"
                      style={{
                        left: `calc(${((pointOfNoReturnTimestamp - chartData[0]?.timestamp) / (chartData[chartData.length - 1]?.timestamp - chartData[0]?.timestamp)) * 85 + 7}% - 45px)`,
                        top: '10px',
                      }}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 1.2 }}
                    >
                      <Skull className="h-3 w-3" />
                      NO RETURN
                    </motion.div>
                  )}
                </>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Bottom legend */}
          <motion.div
            className="flex items-center justify-center gap-6 mt-4 pt-4 border-t border-border text-xs font-mono"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            <motion.div variants={staggerItem} className="flex items-center gap-2">
              <div
                className="h-1 w-8 rounded-full bg-gradient-to-r from-severity-high via-severity-critical to-severity-critical"
                style={{ boxShadow: isDark ? '0 0 10px rgba(255, 59, 59, 0.5)' : 'none' }}
              />
              <span className="text-muted-foreground">Cost trajectory</span>
            </motion.div>
            <motion.div variants={staggerItem} className="flex items-center gap-2">
              <div
                className="h-0.5 w-6 border-t-2 border-dashed"
                style={{ borderColor: chartColors.chart1 }}
              />
              <span className="text-muted-foreground">Current time</span>
            </motion.div>
            {pointOfNoReturn && (
              <motion.div variants={staggerItem} className="flex items-center gap-2">
                <div className="h-0.5 w-6" style={{ backgroundColor: chartColors.red.primary }} />
                <span className="text-muted-foreground">Point of no return</span>
              </motion.div>
            )}
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default CostEscalationChart;
