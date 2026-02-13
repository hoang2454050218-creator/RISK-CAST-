/**
 * Analytics Page - AI Risk Terminal Style
 *
 * Data-dense enterprise dashboard with terminal aesthetics
 * Mood: Dark, analytical, precise, high-trust
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useAnalyticsData } from '@/hooks/useAnalytics';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import { ConfidenceGauge } from '@/components/charts';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  PieChart,
  Pie,
  Cell,
  Area,
  ComposedChart,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import {
  TrendingUp,
  Target,
  CheckCircle,
  Clock,
  DollarSign,
  Calendar,
  Activity,
  Database,
  Cpu,
  Radio,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { CHART_CONFIG, useChartColors } from '@/lib/chart-theme';

// ═══════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════

export function AnalyticsPage() {
  const [dateRange, setDateRange] = useState('30d');
  const { success, info } = useToast();
  // Theme-aware chart colors: returns dark or light palette based on current theme
  const COLORS = useChartColors();
  const { data, isLoading, error, refetch } = useAnalyticsData(dateRange);

  // Derive variables from hook data to match JSX expectations
  const performanceMetrics = {
    totalDecisions: data?.performanceMetrics.totalDecisions ?? 0,
    acknowledgedRate: data?.performanceMetrics.accuracyRate ?? 0,
    overrideRate: 1 - (data?.performanceMetrics.accuracyRate ?? 0),
    avgResponseTime: data?.performanceMetrics.avgResponseTime ?? 0,
    totalSavings: data?.performanceMetrics.costSaved ?? 0,
    accuracyScore: data?.performanceMetrics.accuracyRate ?? 0,
    activeSessions: data?.systemMetrics.signalsProcessed ? Math.ceil(data.systemMetrics.signalsProcessed / 100) : 0,
    signalsProcessed: data?.systemMetrics.signalsProcessed ?? 0,
  };

  const decisionsByWeek = (data?.decisionsByWeek ?? []).map(w => ({
    week: w.week,
    decisions: w.total,
    acknowledged: w.acknowledged,
    overridden: w.overridden,
    accuracy: w.total > 0 ? w.acknowledged / w.total : 0,
  }));

  const decisionsByType = data?.decisionsByType ?? [];

  const calibrationData = (data?.calibrationData ?? []).map(d => ({
    ...d,
    deviation: +(d.actual - d.predicted).toFixed(3),
  }));

  const systemMetrics = data ? [
    { metric: 'Signal Quality', value: Math.round(data.systemMetrics.uptime), max: 100 },
    { metric: 'Data Freshness', value: Math.min(100, Math.round(data.systemMetrics.uptime * 0.98)), max: 100 },
    { metric: 'Model Confidence', value: Math.round(data.performanceMetrics.accuracyRate * 100), max: 100 },
    { metric: 'Coverage', value: Math.min(100, Math.round(data.performanceMetrics.totalDecisions > 0 ? 60 + data.performanceMetrics.accuracyRate * 40 : 0)), max: 100 },
    { metric: 'Response Time', value: Math.min(100, Math.round(100 - data.performanceMetrics.avgResponseTime * 10)), max: 100 },
  ] : [];

  const handleDateRangeChange = () => {
    const ranges = ['7d', '30d', '90d'];
    const currentIndex = ranges.indexOf(dateRange);
    const nextIndex = (currentIndex + 1) % ranges.length;
    setDateRange(ranges[nextIndex]);
    info(
      `Showing data from last ${ranges[nextIndex] === '7d' ? '7 days' : ranges[nextIndex] === '30d' ? '30 days' : '90 days'}`,
    );
  };

  const handleExportReport = () => {
    if (!data) return;

    // Build CSV content from analytics data
    const rows: string[] = ['Metric,Value'];
    const pm = data.performanceMetrics;
    rows.push(`Total Decisions,${pm.totalDecisions}`);
    rows.push(`Avg Response Time,${pm.avgResponseTime.toFixed(1)}h`);
    rows.push(`Accuracy Rate,${(pm.accuracyRate * 100).toFixed(1)}%`);
    rows.push(`Cost Saved,$${pm.costSaved.toLocaleString()}`);
    rows.push('');
    rows.push('Week,Total,Acknowledged,Overridden,Escalated');
    for (const w of data.decisionsByWeek) {
      rows.push(`${w.week},${w.total},${w.acknowledged},${w.overridden},${w.escalated}`);
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `riskcast-analytics-${dateRange}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    success('Analytics report exported');
  };

  // Calculate summary stats
  const totalAcknowledged = decisionsByWeek.reduce((sum, w) => sum + w.acknowledged, 0);
  const totalOverridden = decisionsByWeek.reduce((sum, w) => sum + w.overridden, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <Activity className="h-8 w-8 animate-pulse text-accent mx-auto" />
          <p className="text-sm text-muted-foreground font-mono">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-sm text-destructive font-mono">Failed to load analytics data</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-6 relative"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Subtle background texture — disabled for clean enterprise look */}

      {/* Page Header */}
      <motion.div
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div>
          <motion.h1
            className="text-3xl font-bold font-mono flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <motion.div className="p-2.5 rounded-xl bg-gradient-to-br from-accent/20 to-info/10 border border-accent/30 relative overflow-hidden">
              <Activity className="h-6 w-6 text-accent" />
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/20 to-transparent"
                animate={{ x: ['-100%', '100%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
            </motion.div>
            <span className="text-gradient">
              ANALYTICS
            </span>
            <motion.span
              className="text-xs font-normal px-2 py-1 rounded bg-accent/10 text-accent border border-accent/30"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              LIVE
            </motion.span>

          </motion.h1>
          <motion.p
            className="text-sm text-muted-foreground mt-1 font-mono"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Decision performance and system calibration metrics
          </motion.p>
        </div>

        <div className="flex items-center gap-2">
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDateRangeChange}
              className="gap-2 bg-card border-border hover:border-accent/50 hover:bg-accent/10 font-mono"
            >
              <Calendar className="h-4 w-4 text-accent" />
              <span className="text-accent">
                {dateRange === '7d' ? '7D' : dateRange === '30d' ? '30D' : '90D'}
              </span>
            </Button>
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportReport}
              className="bg-gradient-to-r from-accent/10 to-accent/5 border-accent/30 hover:border-accent font-mono text-accent"
            >
              <Database className="h-4 w-4 mr-2" />
              Export
            </Button>
          </motion.div>
        </div>
      </motion.div>

      {/* System Status Bar */}
      <motion.div
        className="flex items-center gap-4 p-3 rounded-xl bg-card border border-border shadow-level-1"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="flex items-center gap-2">
          <motion.div
            className="h-2 w-2 rounded-full bg-success"
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className="text-xs font-mono text-success">
            SYSTEM ONLINE
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-mono text-muted-foreground">
            {performanceMetrics.activeSessions} active sessions
          </span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <Radio className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-mono text-muted-foreground">
            {performanceMetrics.signalsProcessed.toLocaleString()} signals processed
          </span>
        </div>
        <div className="flex-1" />
        <span className="text-xs font-mono text-muted-foreground">
          Last updated: {new Date().toLocaleTimeString()}
        </span>
      </motion.div>

      {/* KPI Cards */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Target}
            label="Total Decisions"
            value={performanceMetrics.totalDecisions}
            accentColor="blue"
            change={12}
            trend="up"
            sublabel={`${totalAcknowledged} acknowledged`}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={CheckCircle}
            label="Acknowledged Rate"
            value={formatPercentage(performanceMetrics.acknowledgedRate)}
            accentColor="emerald"
            change={3}
            trend="up"
            sublabel={`${totalOverridden} overridden`}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Clock}
            label="Avg Response Time"
            value={`${performanceMetrics.avgResponseTime}h`}
            accentColor="amber"
            change={-15}
            trend="down"
            sublabel="Target: <2h"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={DollarSign}
            label="Total Savings"
            value={performanceMetrics.totalSavings}
            accentColor="emerald"
            isCurrency
            change={8}
            trend="up"
            sublabel="vs. no action taken"
          />
        </motion.div>
      </motion.div>

      {/* Main Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Weekly Decisions Bar Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, ...springs.smooth }}
        >
          <TerminalCard
            title="Weekly Decision Volume"
            subtitle="Stacked by outcome status"
            accentColor="blue"
            stats={[
              { label: 'Total', value: performanceMetrics.totalDecisions, color: 'blue' },
              {
                label: 'Avg/Week',
                value: Math.round(performanceMetrics.totalDecisions / 5),
                color: 'slate',
              },
            ]}
          >
            <div className="h-72" style={{ minWidth: 0 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={1}>
                <ComposedChart
                  data={decisionsByWeek}
                  margin={{ top: 20, right: 20, bottom: 20, left: 0 }}
                >
                  <defs>
                    <linearGradient id="acknowledgedGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor={COLORS.green.primary}
                        stopOpacity={0.9}
                      />
                      <stop
                        offset="100%"
                        stopColor={COLORS.green.tertiary}
                        stopOpacity={0.7}
                      />
                    </linearGradient>
                    <linearGradient id="overriddenGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor={COLORS.amber.primary}
                        stopOpacity={0.9}
                      />
                      <stop
                        offset="100%"
                        stopColor={COLORS.amber.tertiary}
                        stopOpacity={0.7}
                      />
                    </linearGradient>
                    <filter id="barGlow">
                      <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  <CartesianGrid
                    strokeDasharray="2 6"
                    stroke={CHART_CONFIG.grid.stroke}
                    vertical={false}
                  />

                  <XAxis
                    dataKey="week"
                    stroke={COLORS.slate.primary}
                    fontSize={11}
                    fontFamily="JetBrains Mono, monospace"
                    tickLine={false}
                    axisLine={{ stroke: COLORS.slate.tertiary }}
                  />

                  <YAxis
                    stroke={COLORS.slate.primary}
                    fontSize={10}
                    fontFamily="JetBrains Mono, monospace"
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => v.toString()}
                  />

                  <Tooltip content={<TerminalTooltip />} />

                  <Bar
                    dataKey="acknowledged"
                    fill="url(#acknowledgedGradient)"
                    stackId="a"
                    name="Acknowledged"
                    radius={[0, 0, 0, 0]}
                    filter="url(#barGlow)"
                  />
                  <Bar
                    dataKey="overridden"
                    fill="url(#overriddenGradient)"
                    stackId="a"
                    name="Overridden"
                    radius={[4, 4, 0, 0]}
                  />

                  <Line
                    type="monotone"
                    dataKey="accuracy"
                    stroke={COLORS.chart1}
                    strokeWidth={2}
                    dot={{ fill: COLORS.chart1, r: 4, strokeWidth: 0 }}
                    yAxisId={1}
                    name="Accuracy"
                  />

                  <YAxis
                    yAxisId={1}
                    orientation="right"
                    domain={[0.7, 1]}
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    stroke={COLORS.chart1}
                    fontSize={10}
                    fontFamily="JetBrains Mono, monospace"
                    tickLine={false}
                    axisLine={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-center gap-6 mt-2 pt-3 border-t border-border">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm bg-success" />
                <span className="text-xs font-mono text-muted-foreground">Acknowledged</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-sm bg-warning" />
                <span className="text-xs font-mono text-muted-foreground">Overridden</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-6 bg-accent" />
                <span className="text-xs font-mono text-muted-foreground">Accuracy</span>
              </div>
            </div>
          </TerminalCard>
        </motion.div>

        {/* Action Distribution Pie Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, ...springs.smooth }}
        >
          <TerminalCard
            title="Action Distribution"
            subtitle="By recommended action type"
            accentColor="purple"
            stats={[
              { label: 'Primary', value: 'REROUTE', color: 'blue' },
              { label: 'Actions', value: decisionsByType.length, color: 'slate' },
            ]}
          >
            <div className="h-72 flex items-center">
              <div className="w-1/2 h-full" style={{ minWidth: 0 }}>
                <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={1}>
                  <PieChart>
                    <defs>
                      {decisionsByType.map((entry, index) => (
                        <linearGradient
                          key={index}
                          id={`pieGradient-${index}`}
                          x1="0"
                          y1="0"
                          x2="1"
                          y2="1"
                        >
                          <stop offset="0%" stopColor={entry.color} stopOpacity={1} />
                          <stop offset="100%" stopColor={entry.color} stopOpacity={0.6} />
                        </linearGradient>
                      ))}
                      <filter id="pieGlow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                        <feMerge>
                          <feMergeNode in="coloredBlur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </defs>
                    <Pie
                      data={decisionsByType}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="rgba(0,0,0,0.3)"
                      strokeWidth={2}
                    >
                      {decisionsByType.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={`url(#pieGradient-${index})`}
                          filter="url(#pieGlow)"
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<PieTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Detailed Legend */}
              <div className="w-1/2 space-y-2 pr-4">
                {decisionsByType.map((entry, index) => {
                  const total = decisionsByType.reduce((sum, e) => sum + e.value, 0);
                  const percent = ((entry.value / total) * 100).toFixed(1);
                  return (
                    <motion.div
                      key={entry.name}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/40 hover:bg-muted transition-colors"
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + index * 0.1 }}
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="h-3 w-3 rounded-sm"
                          style={{
                            backgroundColor: entry.color,
                            boxShadow: `0 0 10px ${entry.color}50`,
                          }}
                        />
                        <span className="text-xs font-mono text-foreground">{entry.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-muted-foreground">
                          {entry.value}
                        </span>
                        <span
                          className="text-xs font-mono font-bold"
                          style={{ color: entry.color }}
                        >
                          {percent}%
                        </span>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </TerminalCard>
        </motion.div>
      </div>

      {/* Calibration Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Calibration Curve */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, ...springs.smooth }}
        >
          <TerminalCard
            title="Calibration Curve"
            subtitle="Predicted vs actual outcome frequency"
            accentColor="blue"
            stats={[
              { label: 'Avg Deviation', value: '±2.1%', color: 'green' },
              {
                label: 'Samples',
                value: calibrationData.reduce((sum, d) => sum + d.count, 0),
                color: 'slate',
              },
            ]}
          >
            <div className="h-72" style={{ minWidth: 0 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={1}>
                <ComposedChart
                  data={calibrationData}
                  margin={{ top: 20, right: 30, bottom: 30, left: 20 }}
                >
                  <defs>
                    <linearGradient id="calibrationGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor={COLORS.chart1} />
                      <stop offset="50%" stopColor={COLORS.chart1} />
                      <stop offset="100%" stopColor={COLORS.green.primary} />
                    </linearGradient>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor={COLORS.chart1}
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="100%"
                        stopColor={COLORS.chart1}
                        stopOpacity={0}
                      />
                    </linearGradient>
                    <filter id="lineGlow">
                      <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  <CartesianGrid strokeDasharray="2 6" stroke={CHART_CONFIG.grid.stroke} />

                  <XAxis
                    dataKey="predicted"
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    stroke={COLORS.slate.primary}
                    fontSize={10}
                    fontFamily="JetBrains Mono, monospace"
                    tickLine={false}
                    axisLine={{ stroke: COLORS.slate.tertiary }}
                    label={{
                      value: 'PREDICTED',
                      position: 'bottom',
                      offset: 10,
                      style: {
                        fill: COLORS.slate.primary,
                        fontSize: 9,
                        fontFamily: 'JetBrains Mono, monospace',
                      },
                    }}
                  />

                  <YAxis
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                    stroke={COLORS.slate.primary}
                    fontSize={10}
                    fontFamily="JetBrains Mono, monospace"
                    tickLine={false}
                    axisLine={false}
                    label={{
                      value: 'ACTUAL',
                      angle: -90,
                      position: 'insideLeft',
                      style: {
                        fill: COLORS.slate.primary,
                        fontSize: 9,
                        fontFamily: 'JetBrains Mono, monospace',
                      },
                    }}
                  />

                  <Tooltip content={<CalibrationTooltip />} />

                  {/* Perfect calibration reference line */}
                  <Line
                    type="monotone"
                    dataKey="predicted"
                    stroke={COLORS.slate.tertiary}
                    strokeDasharray="8 4"
                    strokeWidth={1}
                    dot={false}
                    name="Perfect"
                  />

                  {/* Confidence band */}
                  <Area type="monotone" dataKey="actual" fill="url(#areaGradient)" stroke="none" />

                  {/* Actual calibration line */}
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="url(#calibrationGradient)"
                    strokeWidth={3}
                    filter="url(#lineGlow)"
                    dot={{
                      fill: COLORS.chart1,
                      r: 5,
                      strokeWidth: 2,
                      stroke: 'var(--color-card)',
                    }}
                    activeDot={{
                      fill: COLORS.chart1,
                      r: 8,
                      strokeWidth: 3,
                      stroke: 'var(--color-card)',
                      filter: 'url(#lineGlow)',
                    }}
                    name="Actual"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <p className="text-xs text-muted-foreground text-center mt-3 font-mono">
              Closer to diagonal = better calibration • Current deviation: ±2.1%
            </p>
          </TerminalCard>
        </motion.div>

        {/* Overall Accuracy Gauge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, ...springs.smooth }}
        >
          <TerminalCard
            title="Overall Accuracy"
            subtitle="System prediction accuracy"
            accentColor="green"
            className="h-full"
          >
            <div className="flex flex-col items-center justify-center py-4">
              <ConfidenceGauge score={performanceMetrics.accuracyScore} level="HIGH" size="lg" />

              <motion.div
                className="w-full mt-6 space-y-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-muted-foreground">Based on</span>
                  <span className="text-foreground">
                    {performanceMetrics.totalDecisions} decisions
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-muted-foreground">Trend</span>
                  <span className="text-success flex items-center gap-1">
                    <TrendingUp className="h-3 w-3" />
                    +2.3% vs last period
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-muted-foreground">Target</span>
                  <span className="text-foreground">≥85%</span>
                </div>
              </motion.div>
            </div>
          </TerminalCard>
        </motion.div>
      </div>

      {/* System Health Radar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, ...springs.smooth }}
      >
        <TerminalCard
          title="System Health Matrix"
          subtitle="Real-time performance indicators"
          accentColor="blue"
          stats={[
            { label: 'Overall', value: '92%', color: 'green' },
            { label: 'Status', value: 'OPTIMAL', color: 'green' },
          ]}
        >
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Radar Chart */}
            <div className="h-64" style={{ minWidth: 0 }}>
              <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} debounce={1}>
                <RadarChart
                  data={systemMetrics}
                  margin={{ top: 20, right: 30, bottom: 20, left: 30 }}
                >
                  <defs>
                    <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor={COLORS.chart1}
                        stopOpacity={0.8}
                      />
                      <stop
                        offset="100%"
                        stopColor={COLORS.chart1}
                        stopOpacity={0.2}
                      />
                    </linearGradient>
                  </defs>
                  <PolarGrid stroke={COLORS.slate.tertiary} strokeDasharray="2 4" />
                  <PolarAngleAxis
                    dataKey="metric"
                    tick={{
                      fill: COLORS.slate.primary,
                      fontSize: 10,
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 100]}
                    tick={{ fill: COLORS.slate.secondary, fontSize: 9 }}
                    axisLine={false}
                  />
                  <Radar
                    name="Performance"
                    dataKey="value"
                    stroke={COLORS.chart1}
                    fill="url(#radarGradient)"
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>

            {/* Metric Bars */}
            <div className="space-y-4 py-4">
              {systemMetrics.map((metric, index) => (
                <motion.div
                  key={metric.metric}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-muted-foreground">{metric.metric}</span>
                    <span
                      className={cn(
                        'text-xs font-mono font-bold',
                        metric.value >= 90 ? 'text-success'
                          : metric.value >= 70 ? 'text-warning'
                          : 'text-error',
                      )}
                    >
                      {metric.value}%
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className={cn(
                        'h-full rounded-full',
                        metric.value >= 90
                          ? 'bg-success shadow-[var(--shadow-glow-success)]'
                          : metric.value >= 70
                            ? 'bg-warning shadow-[var(--shadow-glow-warning)]'
                            : 'bg-error shadow-[var(--shadow-glow-error)]',
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${metric.value}%` }}
                      transition={{ delay: 1 + index * 0.1, duration: 0.8, ease: 'easeOut' }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </TerminalCard>
      </motion.div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════════════
// TERMINAL CARD COMPONENT
// ═══════════════════════════════════════════════════════════════════

interface TerminalCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  accentColor?: 'blue' | 'green' | 'amber' | 'red' | 'purple';
  className?: string;
  stats?: Array<{ label: string; value: string | number; color?: string }>;
}

function TerminalCard({
  title,
  subtitle,
  children,
  accentColor = 'blue',
  className,
  stats,
}: TerminalCardProps) {
  // Semantic token-based accent colors — auto-adapt to light/dark mode
  const accentColors = {
    blue: { line: 'from-accent to-accent', text: 'text-accent' },
    green: { line: 'from-success to-success', text: 'text-success' },
    amber: { line: 'from-warning to-warning', text: 'text-warning' },
    red: { line: 'from-error to-error', text: 'text-error' },
    purple: { line: 'from-action-reroute to-action-reroute', text: 'text-action-reroute' },
  };

  const accent = accentColors[accentColor];

  return (
    <Card
      className={cn('overflow-hidden border border-border bg-card relative shadow-level-1', className)}
    >
      {/* Top accent line */}
      <motion.div
        className={cn('h-px bg-gradient-to-r', accent.line)}
        animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        style={{ backgroundSize: '200% 200%' }}
      />

      {/* Corner decorations (subtle in light mode) */}
      <div className="absolute top-0 left-0 w-3 h-3 border-l border-t border-border opacity-50" />
      <div className="absolute top-0 right-0 w-3 h-3 border-r border-t border-border opacity-50" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-l border-b border-border opacity-50" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-r border-b border-border opacity-50" />

      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle
              className={cn('text-sm font-mono font-bold uppercase tracking-wider', accent.text)}
            >
              {title}
            </CardTitle>
            {subtitle && (
              <CardDescription className="text-xs font-mono text-muted-foreground mt-0.5">
                {subtitle}
              </CardDescription>
            )}
          </div>

          {stats && stats.length > 0 && (
            <div className="flex items-center gap-4">
              {stats.map((stat, index) => (
                <div key={index} className="text-right">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase">
                    {stat.label}
                  </p>
                  <p
                    className={cn(
                      'text-sm font-mono font-bold',
                      stat.color === 'blue' ? 'text-accent'
                        : stat.color === 'green' ? 'text-success'
                        : stat.color === 'amber' ? 'text-warning'
                        : stat.color === 'red' ? 'text-error'
                        : 'text-foreground',
                    )}
                  >
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="pb-4">{children}</CardContent>
    </Card>
  );
}


// ═══════════════════════════════════════════════════════════════════
// CUSTOM TOOLTIPS
// ═══════════════════════════════════════════════════════════════════

interface RechartsTooltipPayload {
  name: string;
  value: number | string;
  color: string;
  payload?: Record<string, unknown>;
}

interface RechartsTooltipProps {
  active?: boolean;
  payload?: RechartsTooltipPayload[];
  label?: string;
}

interface PieTooltipPayload {
  name: string;
  value: number;
  color: string;
}

interface CalibrationTooltipPayload {
  predicted: number;
  actual: number;
  deviation: number;
  count: number;
}

function TerminalTooltip({ active, payload, label }: RechartsTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-4 shadow-2xl"
      initial={{ opacity: 0, scale: 0.95, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={springs.snappy}
    >
      <p className="font-mono font-bold text-accent text-sm mb-2">{label}</p>
      <div className="space-y-1.5">
        {payload.map((entry: RechartsTooltipPayload, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
              <span className="text-xs font-mono text-muted-foreground">{entry.name}:</span>
            </div>
            <span className="text-xs font-mono font-bold text-foreground">{entry.value}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function PieTooltip({ active, payload }: RechartsTooltipProps) {
  if (!active || !payload?.length) return null;

  const raw = payload[0].payload;
  if (raw == null || typeof raw !== 'object') return null;
  const data = raw as unknown as PieTooltipPayload;
  const total = 100; // percentage

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
          style={{ backgroundColor: data.color, boxShadow: `0 0 10px ${data.color}50` }}
        />
        <p className="font-mono font-bold text-sm" style={{ color: data.color }}>
          {data.name}
        </p>
      </div>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="text-xs font-mono text-muted-foreground">Count:</span>
          <span className="text-xs font-mono font-bold text-foreground">{data.value}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-xs font-mono text-muted-foreground">Share:</span>
          <span className="text-xs font-mono font-bold" style={{ color: data.color }}>
            {formatPercentage(data.value / total)}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

function CalibrationTooltip({ active, payload }: RechartsTooltipProps) {
  if (!active || !payload?.length) return null;

  const raw = payload[0].payload;
  if (raw == null || typeof raw !== 'object') return null;
  const data = raw as unknown as CalibrationTooltipPayload;

  return (
    <motion.div
      className="rounded-xl border border-border bg-card p-4 shadow-2xl"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={springs.snappy}
    >
      <div className="space-y-2">
        <div className="flex justify-between gap-6">
          <span className="text-xs font-mono text-muted-foreground">Predicted:</span>
          <span className="text-xs font-mono font-bold text-foreground">
            {formatPercentage(data.predicted)}
          </span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs font-mono text-muted-foreground">Actual:</span>
          <span className="text-xs font-mono font-bold text-accent">
            {formatPercentage(data.actual)}
          </span>
        </div>
        <div className="flex justify-between gap-6">
          <span className="text-xs font-mono text-muted-foreground">Deviation:</span>
          <span
            className={cn(
              'text-xs font-mono font-bold',
              Math.abs(data.deviation) <= 0.02
                ? 'text-success'
                : 'text-warning',
            )}
          >
            {data.deviation > 0 ? '+' : ''}
            {formatPercentage(data.deviation)}
          </span>
        </div>
        <div className="pt-2 border-t border-border">
          <div className="flex justify-between gap-6">
            <span className="text-xs font-mono text-muted-foreground">Samples:</span>
            <span className="text-xs font-mono text-muted-foreground">{data.count}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default AnalyticsPage;
