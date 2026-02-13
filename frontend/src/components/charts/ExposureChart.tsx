/**
 * ExposureChart - AI Risk Terminal Style
 *
 * Data-dense enterprise visualization for shipment exposure
 * Features: Terminal aesthetics, gradient bars, glow effects, detailed stats
 */

import { motion } from 'framer-motion';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatCurrency } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';
import { DollarSign, Package, AlertTriangle, TrendingUp, Zap } from 'lucide-react';
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { ShipmentExposure } from '@/types/decision';

interface ExposureChartProps {
  data: ShipmentExposure[];
  className?: string;
  animate?: boolean;
}

function getExposureCategory(amount: number): 'critical' | 'high' | 'medium' | 'low' {
  if (amount > 75000) return 'critical';
  if (amount > 50000) return 'high';
  if (amount > 25000) return 'medium';
  return 'low';
}

function buildExposureColors(c: ReturnType<typeof useChartColors>) {
  return {
    critical: {
      main: c.red.primary,
      gradient: [c.red.primary, c.red.tertiary],
      glow: c.red.glow,
      label: 'CRITICAL',
    },
    high: {
      main: c.orange.primary,
      gradient: [c.orange.primary, c.orange.tertiary],
      glow: c.orange.glow,
      label: 'HIGH',
    },
    medium: {
      main: c.amber.primary,
      gradient: [c.amber.primary, c.amber.tertiary],
      glow: c.amber.glow,
      label: 'MEDIUM',
    },
    low: {
      main: c.green.primary,
      gradient: [c.green.primary, c.green.tertiary],
      glow: c.green.glow,
      label: 'LOW',
    },
  };
}

export function ExposureChart({ data, className, animate = true }: ExposureChartProps) {
  // Theme-reactive colors
  const chartColors = useChartColors();
  const exposureColors = useMemo(() => buildExposureColors(chartColors), [chartColors]);

  const chartData = [...data]
    .sort((a, b) => b.exposure_usd - a.exposure_usd)
    .slice(0, 8) // Show top 8 for readability
    .map((shipment) => {
      const category = getExposureCategory(shipment.exposure_usd);
      return {
        id: shipment.shipment_id,
        exposure: shipment.exposure_usd,
        cargoValue: shipment.cargo_value_usd,
        route: shipment.route,
        color: exposureColors[category].main,
        category,
        exposureRatio: shipment.exposure_usd / shipment.cargo_value_usd,
      };
    });

  const totalExposure = data.reduce((sum, s) => sum + s.exposure_usd, 0);
  const avgExposure = totalExposure / data.length || 0;
  const criticalCount = data.filter((s) => s.exposure_usd > 75000).length;
  const maxExposure = Math.max(...data.map((s) => s.exposure_usd));

  return (
    <motion.div
      role="img"
      aria-label={`Exposure breakdown chart across ${data.length} shipments`}
      initial={animate ? { opacity: 0, y: 20 } : undefined}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      <span className="sr-only">
        {`Exposure breakdown: ${data.length} shipments. Total exposure: ${formatCurrency(data.reduce((sum, d) => sum + d.exposure_usd, 0))}.`}
      </span>
      <Card
        className={cn('overflow-hidden border border-border bg-card relative shadow-sm', className)}
      >
        {/* Top accent line with animation */}
        <motion.div
          className="h-px bg-gradient-to-r from-red-500 via-orange-500 to-amber-500"
          animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
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
                className="p-2.5 rounded-xl bg-gradient-to-br from-red-500/20 to-orange-500/10 border border-red-500/30 relative overflow-hidden"
                whileHover={{ scale: 1.05 }}
                transition={springs.bouncy}
              >
                <DollarSign className="h-5 w-5 text-severity-critical" />
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-red-400/20 to-transparent"
                  animate={{ x: ['-100%', '100%'] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                />
              </motion.div>
              <div>
                <CardTitle className="text-sm font-mono font-bold uppercase tracking-wider text-severity-critical">
                  Exposure Analysis
                </CardTitle>
                <p className="text-xs text-muted-foreground font-mono">
                  {data.length} shipments at risk
                </p>
              </div>
            </div>

            <motion.div
              className="text-right"
              initial={animate ? { scale: 0 } : undefined}
              animate={{ scale: 1 }}
              transition={{ delay: 0.3, ...springs.bouncy }}
            >
              <p className="text-[10px] font-mono text-muted-foreground uppercase">
                Total Exposure
              </p>
              <p
                className="font-mono text-2xl font-bold text-severity-critical"
                style={{
                  textShadow: chartColors.isDark ? '0 0 20px rgba(255, 59, 59, 0.5)' : 'none',
                }}
              >
                {formatCurrency(totalExposure, { compact: true })}
              </p>
            </motion.div>
          </div>

          {/* Stats Grid */}
          <motion.div
            className="grid grid-cols-4 gap-2 mt-4"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            <motion.div
              variants={staggerItem}
              className="p-2.5 rounded-lg bg-muted/50 border border-border text-center"
            >
              <div className="flex items-center justify-center gap-1 mb-1">
                <Package className="h-3 w-3 text-muted-foreground" />
                <span className="text-[9px] text-muted-foreground uppercase font-mono">Count</span>
              </div>
              <p className="font-mono font-bold text-lg text-foreground">{data.length}</p>
            </motion.div>

            <motion.div
              variants={staggerItem}
              className="p-2.5 rounded-lg bg-muted/50 border border-border text-center"
            >
              <div className="flex items-center justify-center gap-1 mb-1">
                <TrendingUp className="h-3 w-3 text-muted-foreground" />
                <span className="text-[9px] text-muted-foreground uppercase font-mono">
                  Average
                </span>
              </div>
              <p className="font-mono font-bold text-lg text-severity-high">
                {formatCurrency(avgExposure, { compact: true })}
              </p>
            </motion.div>

            <motion.div
              variants={staggerItem}
              className="p-2.5 rounded-lg bg-muted/50 border border-border text-center"
            >
              <div className="flex items-center justify-center gap-1 mb-1">
                <Zap className="h-3 w-3 text-muted-foreground" />
                <span className="text-[9px] text-muted-foreground uppercase font-mono">Max</span>
              </div>
              <p className="font-mono font-bold text-lg text-severity-medium">
                {formatCurrency(maxExposure, { compact: true })}
              </p>
            </motion.div>

            <motion.div
              variants={staggerItem}
              className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-center"
            >
              <div className="flex items-center justify-center gap-1 mb-1">
                <AlertTriangle className="h-3 w-3 text-severity-critical" />
                <span className="text-[9px] text-severity-critical uppercase font-mono">
                  Critical
                </span>
              </div>
              <p className="font-mono font-bold text-lg text-severity-critical">
                {criticalCount}
              </p>
            </motion.div>
          </motion.div>
        </CardHeader>

        <CardContent className="pb-4">
          <motion.div
            className="h-64"
            initial={animate ? { opacity: 0 } : undefined}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.5 }}
          >
            <ResponsiveContainer width="100%" height="100%" debounce={1}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 20, bottom: 5, left: 70 }}
              >
                <defs>
                  {Object.entries(exposureColors).map(([key, { gradient }]) => (
                    <linearGradient
                      key={key}
                      id={`exposure-terminal-${key}`}
                      x1="0"
                      y1="0"
                      x2="1"
                      y2="0"
                    >
                      <stop offset="0%" stopColor={gradient[0]} stopOpacity={1} />
                      <stop offset="100%" stopColor={gradient[1]} stopOpacity={0.8} />
                    </linearGradient>
                  ))}
                  {chartColors.isDark && (
                    <filter id="exposureGlow">
                      <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  )}
                </defs>

                <CartesianGrid
                  strokeDasharray="2 6"
                  stroke={chartColors.chartGrid}
                  horizontal={false}
                />

                {/* Average reference line */}
                <ReferenceLine
                  x={avgExposure}
                  stroke={chartColors.chart1}
                  strokeDasharray="4 4"
                  strokeWidth={1}
                />

                <XAxis
                  type="number"
                  tickFormatter={(value) => formatCurrency(value, { compact: true })}
                  stroke={chartColors.mutedForeground}
                  fontSize={10}
                  fontFamily="JetBrains Mono, monospace"
                  tickLine={false}
                  axisLine={{ stroke: chartColors.chartAxis }}
                />

                <YAxis
                  type="category"
                  dataKey="id"
                  stroke={chartColors.mutedForeground}
                  fontSize={9}
                  fontFamily="JetBrains Mono, monospace"
                  tickLine={false}
                  axisLine={false}
                  width={65}
                />

                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    const cat = exposureColors[d.category as keyof typeof exposureColors];
                    return (
                      <motion.div
                        className="rounded-xl border border-border bg-card p-4 shadow-2xl"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={springs.snappy}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div
                            className="h-3 w-3 rounded-sm"
                            style={{
                              backgroundColor: cat.main,
                              boxShadow: chartColors.isDark ? `0 0 10px ${cat.glow}` : 'none',
                            }}
                          />
                          <p className="font-mono font-bold text-sm text-foreground">{d.id}</p>
                          <span
                            className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                            style={{ backgroundColor: `${cat.main}20`, color: cat.main }}
                          >
                            {cat.label}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground font-mono mb-3">{d.route}</p>
                        <div className="space-y-1.5">
                          <div className="flex justify-between gap-6">
                            <span className="text-xs text-muted-foreground font-mono">
                              Exposure:
                            </span>
                            <span
                              className="font-mono text-sm font-bold"
                              style={{ color: cat.main }}
                            >
                              {formatCurrency(d.exposure)}
                            </span>
                          </div>
                          <div className="flex justify-between gap-6">
                            <span className="text-xs text-muted-foreground font-mono">
                              Cargo Value:
                            </span>
                            <span className="font-mono text-sm text-foreground">
                              {formatCurrency(d.cargoValue)}
                            </span>
                          </div>
                          <div className="flex justify-between gap-6">
                            <span className="text-xs text-muted-foreground font-mono">
                              Exposure Ratio:
                            </span>
                            <span className="font-mono text-sm text-info">
                              {(d.exposureRatio * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    );
                  }}
                />

                <Bar
                  dataKey="exposure"
                  radius={[0, 6, 6, 0]}
                  animationBegin={animate ? 0 : undefined}
                  animationDuration={animate ? 1500 : 0}
                  animationEasing="ease-out"
                >
                  {chartData.map((entry) => (
                    <Cell
                      key={`cell-${entry.id}`}
                      fill={`url(#exposure-terminal-${entry.category})`}
                      style={{ filter: chartColors.isDark ? 'url(#exposureGlow)' : undefined }}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Legend */}
          <motion.div
            className="flex flex-wrap items-center justify-center gap-4 mt-4 pt-3 border-t border-border text-xs"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {[
              { label: '>$75K', category: 'critical' as const },
              { label: '$50K-$75K', category: 'high' as const },
              { label: '$25K-$50K', category: 'medium' as const },
              { label: '<$25K', category: 'low' as const },
            ].map(({ label, category }) => (
              <motion.div
                key={category}
                variants={staggerItem}
                className="flex items-center gap-1.5"
              >
                <div
                  className="h-2.5 w-2.5 rounded-sm"
                  style={{
                    background: `linear-gradient(135deg, ${exposureColors[category].gradient.join(', ')})`,
                    boxShadow: chartColors.isDark
                      ? `0 0 8px ${exposureColors[category].glow}`
                      : 'none',
                  }}
                />
                <span className="font-mono text-muted-foreground">{label}</span>
              </motion.div>
            ))}
            <div className="flex items-center gap-1.5">
              <div
                className="h-0.5 w-4 border-t border-dashed"
                style={{ borderColor: chartColors.chart1 }}
              />
              <span className="font-mono text-muted-foreground">Avg</span>
            </div>
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default ExposureChart;
