/**
 * ConfidenceGauge - AI Risk Terminal Style
 *
 * Premium circular gauge with terminal aesthetics
 * Features: Glowing rings, animated entry, data-dense display, HUD elements
 */

import { motion, useSpring, useTransform, AnimatePresence } from 'framer-motion';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';
import { Shield, TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';
import type { ConfidenceLevel, ConfidenceFactor } from '@/types/decision';

interface ConfidenceGaugeProps {
  score: number;
  level: ConfidenceLevel;
  factors?: ConfidenceFactor[];
  size?: 'sm' | 'md' | 'lg';
  showFactors?: boolean;
  className?: string;
  animate?: boolean;
}

function buildLevelConfig(c: ReturnType<typeof useChartColors>) {
  return {
    HIGH: {
      stroke: c.green.primary,
      glow: c.green.glow,
      bg: 'from-confidence-high/20 to-confidence-high/5',
      text: 'text-confidence-high',
      gradient: c.green.gradient,
      ring: 'ring-confidence-high/30',
      shadow: 'shadow-confidence-high/50',
      label: 'HIGH CONFIDENCE',
      pulseColor: c.isDark
        ? 'color-mix(in srgb, var(--color-confidence-high) 30%, transparent)'
        : 'color-mix(in srgb, var(--color-confidence-high) 12%, transparent)',
    },
    MEDIUM: {
      stroke: c.amber.primary,
      glow: c.amber.glow,
      bg: 'from-confidence-medium/20 to-confidence-medium/5',
      text: 'text-confidence-medium',
      gradient: c.amber.gradient,
      ring: 'ring-confidence-medium/30',
      shadow: 'shadow-confidence-medium/50',
      label: 'MEDIUM CONFIDENCE',
      pulseColor: c.isDark
        ? 'color-mix(in srgb, var(--color-confidence-medium) 30%, transparent)'
        : 'color-mix(in srgb, var(--color-confidence-medium) 12%, transparent)',
    },
    LOW: {
      stroke: c.red.primary,
      glow: c.red.glow,
      bg: 'from-confidence-low/20 to-confidence-low/5',
      text: 'text-confidence-low',
      gradient: c.red.gradient,
      ring: 'ring-confidence-low/30',
      shadow: 'shadow-confidence-low/50',
      label: 'LOW CONFIDENCE',
      pulseColor: c.isDark
        ? 'color-mix(in srgb, var(--color-confidence-low) 30%, transparent)'
        : 'color-mix(in srgb, var(--color-confidence-low) 12%, transparent)',
    },
  };
}

export function ConfidenceGauge({
  score,
  level,
  factors = [],
  size = 'md',
  showFactors = false,
  className,
  animate = true,
}: ConfidenceGaugeProps) {
  const chartColors = useChartColors();
  const levelConfig = buildLevelConfig(chartColors);
  const config = levelConfig[level];
  const targetPercentage = Math.round(score * 100);

  const springValue = useSpring(0, { stiffness: 40, damping: 15 });
  const displayPercentage = useTransform(springValue, (v) => Math.round(v));
  const [currentPercentage, setCurrentPercentage] = useState(0);

  useEffect(() => {
    springValue.set(targetPercentage);
  }, [targetPercentage, springValue]);

  useEffect(() => {
    return displayPercentage.on('change', (v) => setCurrentPercentage(v));
  }, [displayPercentage]);

  const sizeMap = {
    sm: {
      width: 120,
      strokeWidth: 8,
      fontSize: 'text-2xl',
      iconSize: 'h-4 w-4',
      labelSize: 'text-[8px]',
      innerRing: 6,
    },
    md: {
      width: 160,
      strokeWidth: 10,
      fontSize: 'text-4xl',
      iconSize: 'h-5 w-5',
      labelSize: 'text-[9px]',
      innerRing: 8,
    },
    lg: {
      width: 200,
      strokeWidth: 12,
      fontSize: 'text-5xl',
      iconSize: 'h-6 w-6',
      labelSize: 'text-[10px]',
      innerRing: 10,
    },
  };

  const { width, strokeWidth, fontSize, iconSize, labelSize, innerRing } = sizeMap[size];
  const radius = (width - strokeWidth) / 2;
  const innerRadius = radius - strokeWidth - innerRing;
  const circumference = 2 * Math.PI * radius;
  const innerCircumference = 2 * Math.PI * innerRadius;

  const strokeDashoffset = useTransform(springValue, [0, 100], [circumference, 0]);
  const innerStrokeDashoffset = useTransform(
    springValue,
    [0, 100],
    [innerCircumference, innerCircumference * 0.3],
  );

  return (
    <motion.div
      className={cn('flex flex-col items-center gap-5', className)}
      role="img"
      aria-label={`Confidence gauge showing ${Math.round(score * 100)}% confidence, rated ${level}`}
      initial={animate ? { opacity: 0, scale: 0.9 } : undefined}
      animate={{ opacity: 1, scale: 1 }}
      transition={springs.smooth}
    >
      <span className="sr-only">
        {`Confidence score: ${Math.round(score * 100)} out of 100. Level: ${level}. ${factors.filter((f) => f.contribution === 'POSITIVE').length} positive factors, ${factors.filter((f) => f.contribution === 'NEGATIVE').length} negative factors.`}
      </span>
      {/* Gauge */}
      <div className="relative" style={{ width, height: width }}>
        {/* Outer glow pulse - dark mode only */}
        {chartColors.isDark && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              backgroundColor: config.pulseColor,
              filter: 'blur(30px)',
            }}
            animate={{
              opacity: [0.3, 0.6, 0.3],
              scale: [0.9, 1.05, 0.9],
            }}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          />
        )}

        {/* Background grid pattern */}
        <div
          className="absolute inset-4 rounded-full opacity-20"
          style={{
            background: `radial-gradient(circle at center, transparent 30%, ${chartColors.chartAxis} 31%, transparent 32%)`,
            backgroundSize: '8px 8px',
          }}
        />

        {/* HUD corner marks */}
        {[0, 90, 180, 270].map((angle) => (
          <motion.div
            key={angle}
            className="absolute w-2 h-0.5"
            style={{
              backgroundColor: config.stroke,
              opacity: 0.5,
              left: '50%',
              top: '50%',
              transform: `rotate(${angle}deg) translateX(${radius + 5}px) translateY(-50%)`,
              transformOrigin: 'left center',
              boxShadow: chartColors.isDark ? `0 0 8px ${config.glow}` : 'none',
            }}
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ duration: 2, repeat: Infinity, delay: angle / 360 }}
          />
        ))}

        <svg width={width} height={width} className="transform -rotate-90 relative z-10">
          <defs>
            {/* Main gradient */}
            <linearGradient
              id={`gauge-terminal-gradient-${level}-${size}`}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="100%"
            >
              {config.gradient.map((color, i) => (
                <stop key={i} offset={`${i * 50}%`} stopColor={color} />
              ))}
            </linearGradient>

            {/* Glow filter - only defined in dark mode */}
            {chartColors.isDark && (
              <>
                <filter id={`gauge-terminal-glow-${level}-${size}`}>
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id={`gauge-inner-glow-${level}-${size}`}>
                  <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </>
            )}
          </defs>

          {/* Background track */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={chartColors.chartAxis}
            strokeWidth={strokeWidth}
            opacity={0.3}
          />

          {/* Inner track */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={innerRadius}
            fill="none"
            stroke={chartColors.chartAxis}
            strokeWidth={innerRing / 2}
            opacity={0.2}
          />

          {/* Inner progress ring */}
          <motion.circle
            cx={width / 2}
            cy={width / 2}
            r={innerRadius}
            fill="none"
            stroke={config.stroke}
            strokeWidth={innerRing / 2}
            strokeLinecap="round"
            strokeDasharray={innerCircumference}
            style={{ strokeDashoffset: innerStrokeDashoffset, opacity: 0.4 }}
            filter={chartColors.isDark ? `url(#gauge-inner-glow-${level}-${size})` : undefined}
          />

          {/* Outer glow ring - dark mode only */}
          {chartColors.isDark && (
            <motion.circle
              cx={width / 2}
              cy={width / 2}
              r={radius}
              fill="none"
              stroke={config.stroke}
              strokeWidth={strokeWidth + 8}
              strokeLinecap="round"
              strokeDasharray={circumference}
              style={{ strokeDashoffset, filter: 'blur(12px)', opacity: 0.4 }}
              initial={animate ? { strokeDashoffset: circumference } : undefined}
            />
          )}

          {/* Main progress ring */}
          <motion.circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={`url(#gauge-terminal-gradient-${level}-${size})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            style={{ strokeDashoffset }}
            filter={chartColors.isDark ? `url(#gauge-terminal-glow-${level}-${size})` : undefined}
            initial={animate ? { strokeDashoffset: circumference } : undefined}
          />

          {/* Tick marks */}
          {[...Array(20)].map((_, i) => {
            const angle = (i / 20) * 360;
            const x1 = width / 2 + (radius + 2) * Math.cos(((angle - 90) * Math.PI) / 180);
            const y1 = width / 2 + (radius + 2) * Math.sin(((angle - 90) * Math.PI) / 180);
            const x2 = width / 2 + (radius + 6) * Math.cos(((angle - 90) * Math.PI) / 180);
            const y2 = width / 2 + (radius + 6) * Math.sin(((angle - 90) * Math.PI) / 180);
            return (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={chartColors.chartAxis}
                strokeWidth={i % 5 === 0 ? 2 : 1}
                opacity={i % 5 === 0 ? 0.5 : 0.2}
              />
            );
          })}
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
          <motion.div
            className={cn(
              'p-2 rounded-full mb-1 border',
              `bg-gradient-to-br ${config.bg}`,
              'border-current/20',
            )}
            initial={animate ? { scale: 0, rotate: -180 } : undefined}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.5, ...springs.bouncy }}
          >
            <Shield className={cn(iconSize, config.text)} />
          </motion.div>

          <motion.span
            className={cn('font-mono font-black tabular-nums', fontSize, config.text)}
            style={{ textShadow: chartColors.isDark ? `0 0 30px ${config.glow}` : 'none' }}
            initial={animate ? { scale: 0 } : undefined}
            animate={{ scale: 1 }}
            transition={{ delay: 0.3, ...springs.bouncy }}
          >
            {currentPercentage}%
          </motion.span>

          <motion.span
            className={cn('uppercase tracking-[0.2em] font-bold font-mono', labelSize, config.text)}
            initial={animate ? { opacity: 0, y: 5 } : undefined}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, ...springs.smooth }}
          >
            {level}
          </motion.span>
        </div>

        {/* Animated scanner line - dark mode only */}
        <AnimatePresence>
          {animate && chartColors.isDark && (
            <motion.div
              className="absolute inset-0 rounded-full overflow-hidden pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="absolute w-full h-0.5"
                style={{
                  background: `linear-gradient(90deg, transparent, ${config.stroke}, transparent)`,
                  top: '50%',
                  left: 0,
                }}
                animate={{
                  rotate: [0, 360],
                }}
                transition={{
                  duration: 4,
                  repeat: Infinity,
                  ease: 'linear',
                  delay: 1,
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Factors breakdown */}
      {showFactors && factors.length > 0 && (
        <motion.div
          className="w-full space-y-3"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider">
              Contributing Factors
            </p>
            <div className="flex items-center gap-1">
              <Activity className="h-3 w-3 text-muted-foreground/70" />
              <span className="text-[9px] font-mono text-muted-foreground/70">
                {factors.length} factors
              </span>
            </div>
          </div>
          {factors.slice(0, 5).map((factor, index) => (
            <motion.div key={index} variants={staggerItem}>
              <TerminalFactorBar factor={factor} index={index} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

interface FactorBarProps {
  factor: ConfidenceFactor;
  index: number;
}

function TerminalFactorBar({ factor, index }: FactorBarProps) {
  const chartColors = useChartColors();

  const isPositive = factor.contribution === 'POSITIVE';
  const isNegative = factor.contribution === 'NEGATIVE';

  const config = isPositive
    ? {
        icon: TrendingUp,
        color: chartColors.green.primary,
        bar: 'from-confidence-high to-confidence-high',
        glow: chartColors.green.glow,
      }
    : isNegative
      ? {
          icon: TrendingDown,
          color: chartColors.red.primary,
          bar: 'from-confidence-low to-confidence-low',
          glow: chartColors.red.glow,
        }
      : {
          icon: Minus,
          color: chartColors.slate.primary,
          bar: 'from-muted-foreground to-muted-foreground/70',
          glow: 'transparent',
        };

  const Icon = config.icon;
  const weightPercentage = Math.abs(factor.weight) * 100;

  return (
    <motion.div
      className="p-3 rounded-xl bg-muted/40 border border-border hover:border-border transition-colors"
      whileHover={{ scale: 1.01 }}
      transition={springs.snappy}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-3.5 w-3.5" style={{ color: config.color }} />
          <span className="text-xs font-mono font-medium text-foreground truncate max-w-[180px]">
            {factor.factor}
          </span>
        </div>
        <motion.span
          className="font-mono text-xs font-bold tabular-nums"
          style={{
            color: config.color,
            textShadow: chartColors.isDark ? `0 0 10px ${config.glow}` : 'none',
          }}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          {isPositive ? '+' : isNegative ? '-' : ''}
          {formatPercentage(Math.abs(factor.weight))}
        </motion.span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full bg-gradient-to-r', config.bar)}
          style={{ boxShadow: chartColors.isDark ? `0 0 10px ${config.glow}` : 'none' }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(weightPercentage * 3, 100)}%` }}
          transition={{ delay: 0.2 + index * 0.1, duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </motion.div>
  );
}

// Compact version for inline use
interface MiniConfidenceGaugeProps {
  score: number;
  level: ConfidenceLevel;
  className?: string;
}

export function MiniConfidenceGauge({ score, level, className }: MiniConfidenceGaugeProps) {
  const chartColors = useChartColors();
  const levelConfig = buildLevelConfig(chartColors);
  const config = levelConfig[level];
  const percentage = Math.round(score * 100);

  return (
    <motion.div
      className={cn('flex items-center gap-2', className)}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={springs.smooth}
    >
      <div className="relative h-10 w-10">
        {/* Glow effect - dark mode only */}
        {chartColors.isDark && (
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{ backgroundColor: config.glow, filter: 'blur(6px)', opacity: 0.4 }}
          />
        )}

        <svg className="h-10 w-10 -rotate-90 relative z-10">
          <circle
            cx="20"
            cy="20"
            r="14"
            fill="none"
            stroke={chartColors.chartAxis}
            strokeWidth="4"
            opacity={0.3}
          />
          <motion.circle
            cx="20"
            cy="20"
            r="14"
            fill="none"
            stroke={config.stroke}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={87.96}
            initial={{ strokeDashoffset: 87.96 }}
            animate={{ strokeDashoffset: 87.96 * (1 - score) }}
            transition={{ duration: 1, ease: 'easeOut' }}
            style={{ filter: chartColors.isDark ? `drop-shadow(0 0 4px ${config.glow})` : 'none' }}
          />
        </svg>
      </div>
      <div className="text-left">
        <p
          className={cn('font-mono text-sm font-bold', config.text)}
          style={{ textShadow: chartColors.isDark ? `0 0 10px ${config.glow}` : 'none' }}
        >
          {percentage}%
        </p>
        <p className="text-[8px] text-muted-foreground uppercase font-mono tracking-wider">
          {level}
        </p>
      </div>
    </motion.div>
  );
}

export default ConfidenceGauge;
