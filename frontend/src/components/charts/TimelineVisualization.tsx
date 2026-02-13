/**
 * TimelineVisualization - AI Risk Terminal Style
 *
 * Premium horizontal timeline with terminal aesthetics
 * Features: HUD elements, scan effects, glowing markers, data-dense display
 */

import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/formatters';
import { Clock, AlertTriangle, Target, Skull, ChevronRight, Radio } from 'lucide-react';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { useChartColors } from '@/lib/chart-theme';

interface TimelineMilestone {
  id: string;
  label: string;
  timestamp: Date;
  type: 'now' | 'deadline' | 'impact' | 'point_of_no_return' | 'event';
  description?: string;
}

interface TimelineVisualizationProps {
  milestones: TimelineMilestone[];
  className?: string;
  animate?: boolean;
}

export function TimelineVisualization({
  milestones,
  className,
  animate = true,
}: TimelineVisualizationProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const sortedMilestones = [...milestones].sort(
    (a, b) => a.timestamp.getTime() - b.timestamp.getTime(),
  );

  const now = new Date();
  const minTime = Math.min(now.getTime(), ...sortedMilestones.map((m) => m.timestamp.getTime()));
  const maxTime = Math.max(...sortedMilestones.map((m) => m.timestamp.getTime()));
  const totalRange = maxTime - minTime;

  const getPosition = (timestamp: Date) => {
    if (totalRange === 0) return 50;
    return ((timestamp.getTime() - minTime) / totalRange) * 100;
  };

  const nowPosition = getPosition(now);

  // Calculate time remaining to critical points
  const deadlineMilestone = sortedMilestones.find((m) => m.type === 'deadline');
  const ponrMilestone = sortedMilestones.find((m) => m.type === 'point_of_no_return');

  const timeToDeadline = deadlineMilestone
    ? Math.max(
        0,
        Math.floor((deadlineMilestone.timestamp.getTime() - now.getTime()) / (1000 * 60 * 60)),
      )
    : null;
  const timeToPONR = ponrMilestone
    ? Math.max(
        0,
        Math.floor((ponrMilestone.timestamp.getTime() - now.getTime()) / (1000 * 60 * 60)),
      )
    : null;

  return (
    <motion.div
      className={cn('space-y-4', className)}
      role="img"
      aria-label={`Event timeline with ${milestones.length} milestones`}
      initial={animate ? { opacity: 0 } : undefined}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <span className="sr-only">
        {`Timeline: ${milestones.length} milestones from ${milestones[0]?.label ?? 'start'} to ${milestones[milestones.length - 1]?.label ?? 'end'}.`}
      </span>
      {/* Time Status Bar */}
      <motion.div
        className="flex items-center justify-between p-3 rounded-xl bg-muted/40 border border-border"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="flex items-center gap-2">
          <motion.div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: chartColors.cyan.primary }}
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className="text-xs font-mono text-accent uppercase">
            Timeline Active
          </span>
        </div>

        <div className="flex items-center gap-4">
          {timeToDeadline !== null && (
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-severity-high" />
              <span className="text-xs font-mono">
                <span className="text-muted-foreground">Deadline:</span>
                <span className="text-severity-high font-bold ml-1">
                  {timeToDeadline}h
                </span>
              </span>
            </div>
          )}
          {timeToPONR !== null && (
            <div className="flex items-center gap-2">
              <Skull className="h-3.5 w-3.5 text-severity-critical" />
              <span className="text-xs font-mono">
                <span className="text-muted-foreground">PONR:</span>
                <span className="text-severity-critical font-bold ml-1">{timeToPONR}h</span>
              </span>
            </div>
          )}
        </div>
      </motion.div>

      {/* Horizontal Timeline */}
      <div className="relative h-36 w-full">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `linear-gradient(to right, ${chartColors.chartAxis} 1px, transparent 1px)`,
            backgroundSize: '10% 100%',
          }}
        />

        {/* Background glow track - dark mode only */}
        {isDark && (
          <motion.div
            className="absolute inset-x-4 top-1/2 -translate-y-1/2 h-12 rounded-full blur-xl"
            style={{
              background: `linear-gradient(to right, ${chartColors.cyan.dim}, ${chartColors.amber.dim}, ${chartColors.red.dim})`,
            }}
            initial={animate ? { opacity: 0 } : undefined}
            animate={{ opacity: 0.5 }}
            transition={{ delay: 0.3, duration: 0.8 }}
          />
        )}

        {/* Base Line */}
        <motion.div
          className="absolute left-4 right-4 top-1/2 h-1 -translate-y-1/2 rounded-full overflow-hidden"
          style={{
            background: `linear-gradient(to right, ${chartColors.chartAxis}, ${chartColors.mutedForeground})`,
          }}
          initial={animate ? { scaleX: 0, opacity: 0 } : undefined}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ duration: 1, ease: 'easeOut' }}
        >
          {/* Animated scan line - dark mode only */}
          {isDark && (
            <motion.div
              className="absolute inset-y-0 w-20"
              style={{
                background: `linear-gradient(to right, transparent, ${chartColors.cyan.primary}40, transparent)`,
              }}
              animate={{ x: ['-100%', '500%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          )}
        </motion.div>

        {/* Progress (completed portion) */}
        <motion.div
          className="absolute left-4 top-1/2 h-1.5 -translate-y-1/2 rounded-full"
          style={{
            background: `linear-gradient(to right, ${chartColors.cyan.tertiary}, ${chartColors.cyan.primary})`,
            boxShadow: isDark ? `0 0 20px ${chartColors.cyan.glow}` : 'none',
          }}
          initial={animate ? { width: 0 } : undefined}
          animate={{ width: `${Math.min(nowPosition, 100) * 0.92}%` }}
          transition={{ duration: 1.2, delay: 0.5, ease: 'easeOut' }}
        />

        {/* NOW Marker */}
        <motion.div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-30"
          style={{ left: `calc(4% + ${nowPosition * 0.92}%)` }}
          initial={animate ? { scale: 0, opacity: 0 } : undefined}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.8, ...springs.bouncy }}
        >
          <div className="flex flex-col items-center">
            <motion.div
              className="flex items-center gap-1 px-2 py-1 rounded bg-accent/20 border border-accent/50 mb-2"
              animate={
                isDark
                  ? {
                      borderColor: [
                        `${chartColors.cyan.primary}50`,
                        chartColors.cyan.primary,
                        `${chartColors.cyan.primary}50`,
                      ],
                    }
                  : undefined
              }
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <Radio className="h-3 w-3 text-accent" />
              <span className="text-[10px] font-mono font-bold text-accent uppercase tracking-wider">
                NOW
              </span>
            </motion.div>

            {/* Outer pulse rings */}
            <div className="relative">
              {isDark && (
                <>
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: chartColors.cyan.primary }}
                    animate={{
                      scale: [1, 2.5],
                      opacity: [0.4, 0],
                    }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    style={{ backgroundColor: chartColors.cyan.primary }}
                    animate={{
                      scale: [1, 2],
                      opacity: [0.3, 0],
                    }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
                  />
                </>
              )}

              {/* Main marker */}
              <motion.div
                className="relative h-12 w-12 rounded-full flex items-center justify-center border-2"
                style={{
                  background: `linear-gradient(135deg, ${chartColors.cyan.primary}30, ${chartColors.cyan.tertiary}30)`,
                  borderColor: chartColors.cyan.primary,
                  boxShadow: isDark
                    ? `0 0 30px ${chartColors.cyan.glow}`
                    : `0 0 8px ${chartColors.cyan.dim}`,
                }}
                whileHover={{ scale: 1.15 }}
                transition={springs.bouncy}
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                >
                  <Clock className="h-5 w-5 text-accent" />
                </motion.div>
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* Milestones */}
        <AnimatePresence>
          {sortedMilestones
            .filter((m) => m.type !== 'now')
            .map((milestone, index) => {
              const position = getPosition(milestone.timestamp);
              const isPast = milestone.timestamp.getTime() < now.getTime();

              return (
                <TerminalMilestoneMarker
                  key={milestone.id}
                  milestone={milestone}
                  position={position}
                  isPast={isPast}
                  index={index}
                  animate={animate}
                />
              );
            })}
        </AnimatePresence>
      </div>

      {/* Legend with terminal styling */}
      <motion.div
        className="flex flex-wrap items-center justify-center gap-4 text-xs font-mono pt-2 border-t border-border"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {[
          { icon: Radio, label: 'Current', color: chartColors.cyan.primary },
          { icon: AlertTriangle, label: 'Deadline', color: chartColors.amber.primary },
          { icon: Target, label: 'Impact', color: chartColors.slate.primary },
          { icon: Skull, label: 'No Return', color: chartColors.red.primary },
        ].map(({ icon: Icon, label, color }) => (
          <motion.div
            key={label}
            variants={staggerItem}
            className="flex items-center gap-2 px-2 py-1 rounded bg-muted/40"
          >
            <Icon className="h-3.5 w-3.5" style={{ color }} />
            <span className="text-muted-foreground">{label}</span>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
}

interface TerminalMilestoneMarkerProps {
  milestone: TimelineMilestone;
  position: number;
  isPast: boolean;
  index: number;
  animate?: boolean;
}

function TerminalMilestoneMarker({
  milestone,
  position,
  isPast,
  index,
  animate = true,
}: TerminalMilestoneMarkerProps) {
  const chartColors = useChartColors();
  const { isDark } = chartColors;

  const config = {
    now: {
      icon: Clock,
      color: chartColors.cyan.primary,
      glow: chartColors.cyan.glow,
      size: 'h-12 w-12',
    },
    deadline: {
      icon: AlertTriangle,
      color: isPast ? chartColors.red.primary : chartColors.amber.primary,
      glow: isPast ? chartColors.red.glow : chartColors.amber.glow,
      size: 'h-10 w-10',
    },
    impact: {
      icon: Target,
      color: chartColors.slate.primary,
      glow: 'transparent',
      size: 'h-9 w-9',
    },
    point_of_no_return: {
      icon: Skull,
      color: chartColors.red.primary,
      glow: chartColors.red.glow,
      size: 'h-10 w-10',
    },
    event: {
      icon: ChevronRight,
      color: chartColors.slate.primary,
      glow: 'transparent',
      size: 'h-7 w-7',
    },
  };

  const { icon: Icon, color, glow, size } = config[milestone.type];
  const isAbove = milestone.type === 'deadline' || milestone.type === 'point_of_no_return';
  const isUrgent = milestone.type === 'deadline' || milestone.type === 'point_of_no_return';

  return (
    <motion.div
      className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 z-10"
      style={{ left: `calc(4% + ${position * 0.92}%)` }}
      initial={animate ? { scale: 0, opacity: 0 } : undefined}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay: 0.9 + index * 0.15, ...springs.bouncy }}
    >
      <motion.div
        className={cn('flex flex-col items-center', isAbove ? 'flex-col-reverse' : 'flex-col')}
        whileHover={{ scale: 1.08 }}
        transition={springs.snappy}
      >
        {/* Label */}
        <motion.div
          className={cn(
            'text-center whitespace-nowrap px-2 py-1 rounded-lg bg-muted/50 border border-border',
            isAbove ? 'mt-2' : 'mb-2',
            isPast ? 'opacity-50' : '',
          )}
          initial={animate ? { opacity: 0, y: isAbove ? 8 : -8 } : undefined}
          animate={{ opacity: isPast ? 0.5 : 1, y: 0 }}
          transition={{ delay: 1.1 + index * 0.15 }}
        >
          <p className="text-[10px] font-mono font-bold uppercase tracking-wide" style={{ color }}>
            {milestone.label}
          </p>
          <p className="text-[9px] text-muted-foreground/70 font-mono">
            {formatDate(milestone.timestamp, { includeTime: true })}
          </p>
        </motion.div>

        {/* Marker */}
        <div className="relative">
          {/* Pulse effect for urgent markers */}
          {isUrgent && !isPast && isDark && (
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{ backgroundColor: color }}
              animate={{ scale: [1, 1.8], opacity: [0.5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
          )}

          <motion.div
            className={cn(
              'rounded-full flex items-center justify-center border-2',
              size,
              isPast && 'opacity-50',
            )}
            style={{
              background: `linear-gradient(135deg, ${color}20, ${color}10)`,
              borderColor: color,
              boxShadow: isUrgent && isDark ? `0 0 20px ${glow}` : 'none',
            }}
            whileHover={{
              scale: 1.2,
              boxShadow: isDark ? `0 0 30px ${glow}` : `0 0 8px ${color}30`,
            }}
          >
            <motion.div
              animate={isUrgent && !isPast ? { rotate: [0, 10, -10, 0] } : undefined}
              transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
            >
              <Icon className="h-4 w-4" style={{ color }} />
            </motion.div>
          </motion.div>
        </div>
      </motion.div>
    </motion.div>
  );
}

/**
 * Helper function to create milestones from Q2 data
 */
export function createTimelineMilestones(
  decisionDeadline: string,
  timeToImpactHours: number,
  pointOfNoReturn?: string,
): TimelineMilestone[] {
  const milestones: TimelineMilestone[] = [];
  const now = new Date();

  milestones.push({
    id: 'deadline',
    label: 'Deadline',
    timestamp: new Date(decisionDeadline),
    type: 'deadline',
    description: 'Action must be taken by this time',
  });

  milestones.push({
    id: 'impact',
    label: 'Impact',
    timestamp: new Date(now.getTime() + timeToImpactHours * 60 * 60 * 1000),
    type: 'impact',
    description: 'When you will feel the impact',
  });

  if (pointOfNoReturn) {
    milestones.push({
      id: 'ponr',
      label: 'No Return',
      timestamp: new Date(pointOfNoReturn),
      type: 'point_of_no_return',
      description: 'After this, options become very limited',
    });
  }

  return milestones;
}

export default TimelineVisualization;
