import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CostDisplay } from '@/components/domain/common/CostDisplay';
import { CostEscalationChart } from '@/components/charts/CostEscalationChart';
import { AlertOctagon, Clock, Skull, BarChart3, AlertTriangle, Timer } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type { Q7WhatIfNothing as Q7Data, CostEscalationPoint } from '@/types/decision';

interface Q7Props {
  data: Q7Data;
  className?: string;
}

export function Q7IfNothing({ data, className }: Q7Props) {
  const pointOfNoReturn = new Date(data.point_of_no_return);

  return (
    <section aria-labelledby="q7-heading">
      <Card className={cn('border-l-4 border-l-error shadow-lg shadow-error/10', className)}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={springs.smooth}
            >
              <CardTitle
                id="q7-heading"
                className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
              >
                Q7: What If We Do Nothing?
              </CardTitle>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1, ...springs.bouncy }}
            >
              <motion.div
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ duration: 1, repeat: Infinity, repeatDelay: 1 }}
              >
                <AlertOctagon className="h-5 w-5 text-error" />
              </motion.div>
            </motion.div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Inaction Cost - THE BIG SCARY NUMBER */}
          <motion.div
            className="rounded-lg bg-error/5 border border-error/20 p-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, ...springs.smooth }}
            whileHover={{ scale: 1.01, borderColor: 'rgba(var(--error), 0.3)' }}
          >
            <CostDisplay
              amount={data.inaction_cost_usd}
              confidenceInterval={data.inaction_cost_ci_90}
              label="Cost of Inaction"
              size="xl"
            />
          </motion.div>

          {/* Secondary Impact Metrics */}
          <motion.div
            className="grid gap-4 sm:grid-cols-2"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {/* Delay Impact */}
            <motion.div
              className="rounded-lg bg-muted/50 p-4 space-y-1"
              variants={staggerItem}
              whileHover={{ scale: 1.02 }}
              transition={springs.snappy}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>Delay Impact</span>
              </div>
              <motion.p
                className="font-mono text-2xl font-semibold text-primary font-tabular"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                +{data.inaction_delay_days} days
              </motion.p>
              <p className="text-xs text-muted-foreground">Additional delay if no action</p>
            </motion.div>

            {/* Point of No Return with Live Countdown */}
            <motion.div variants={staggerItem}>
              <PONRCountdown pointOfNoReturn={pointOfNoReturn} />
            </motion.div>
          </motion.div>

          {/* Cost Escalation Chart - VISUAL TIME VS COST */}
          {data.cost_escalation.length > 0 && (
            <motion.div
              className="space-y-3 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                <span>Cost Escalation Over Time</span>
              </div>

              {/* Visual Chart - THE CRITICAL VISUALIZATION */}
              <CostEscalationChart
                data={data.cost_escalation}
                currentTime={new Date()}
                pointOfNoReturn={data.point_of_no_return}
                className="border-none shadow-none -mx-2"
              />

              {/* Detailed Timeline Below Chart */}
              <div className="relative mt-4">
                <motion.div
                  className="absolute left-3 top-2 bottom-2 w-0.5 bg-gradient-to-b from-warning via-orange-500 to-error"
                  initial={{ scaleY: 0 }}
                  animate={{ scaleY: 1 }}
                  transition={{ delay: 0.6, duration: 0.5 }}
                  style={{ transformOrigin: 'top' }}
                />

                <motion.div
                  className="space-y-3"
                  variants={staggerContainer}
                  initial="hidden"
                  animate="visible"
                >
                  {data.cost_escalation.map((point, index) => (
                    <motion.div key={index} variants={staggerItem}>
                      <CostEscalationItem
                        point={point}
                        isLast={index === data.cost_escalation.length - 1}
                        progress={index / (data.cost_escalation.length - 1)}
                        index={index}
                      />
                    </motion.div>
                  ))}
                </motion.div>
              </div>
            </motion.div>
          )}

          {/* Worst Case Scenario */}
          <motion.div
            className="space-y-2 pt-2 border-t"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
          >
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-error">
              <motion.div
                animate={{ rotate: [0, 5, -5, 0] }}
                transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
              >
                <AlertOctagon className="h-3.5 w-3.5" />
              </motion.div>
              <span>Worst Case Scenario</span>
            </div>

            <motion.div
              className="rounded-lg bg-error/5 border border-error/20 p-4"
              whileHover={{ scale: 1.01, borderColor: 'rgba(var(--error), 0.35)' }}
              transition={springs.snappy}
            >
              <p className="text-sm text-primary font-medium leading-relaxed">
                {data.worst_case_scenario}
              </p>
            </motion.div>
          </motion.div>
        </CardContent>
      </Card>
    </section>
  );
}

/**
 * PONR Countdown - Live countdown to Point of No Return
 */
interface PONRCountdownProps {
  pointOfNoReturn: Date;
}

function PONRCountdown({ pointOfNoReturn }: PONRCountdownProps) {
  const [timeRemaining, setTimeRemaining] = useState(getTimeRemaining(pointOfNoReturn));

  useEffect(() => {
    const interval = setInterval(() => {
      const remaining = getTimeRemaining(pointOfNoReturn);
      setTimeRemaining(remaining);
    }, 1000);

    return () => clearInterval(interval);
  }, [pointOfNoReturn]);

  const isExpired = timeRemaining.total <= 0;
  const isCritical = timeRemaining.total <= 3600000 && !isExpired; // Less than 1 hour
  const isUrgent = timeRemaining.total <= 86400000 && !isCritical && !isExpired; // Less than 24 hours

  // Calculate percentage remaining (assuming max 7 days = 100%)
  const maxDuration = 7 * 24 * 60 * 60 * 1000; // 7 days in ms
  const percentRemaining = Math.max(0, Math.min(100, (timeRemaining.total / maxDuration) * 100));

  return (
    <motion.div
      className={cn(
        'rounded-lg p-4 space-y-3 transition-all',
        isExpired && 'bg-error/20 border-2 border-error',
        isCritical && !isExpired && 'bg-error/10 border border-error',
        isUrgent && !isCritical && 'bg-orange-500/10 border border-orange-500',
        !isUrgent && !isCritical && !isExpired && 'bg-error/5 border border-error/20',
      )}
      animate={isCritical ? { scale: [1, 1.01, 1] } : {}}
      transition={{ duration: 0.5, repeat: isCritical ? Infinity : 0 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-error">
          <motion.div
            animate={
              isCritical
                ? {
                    y: [0, -2, 0],
                    scale: [1, 1.1, 1],
                  }
                : {}
            }
            transition={{ duration: 0.5, repeat: isCritical ? Infinity : 0 }}
          >
            <Skull className="h-3.5 w-3.5" />
          </motion.div>
          <span>Point of No Return</span>
        </div>

        {!isExpired && (
          <motion.div
            className="flex items-center gap-1 text-xs text-muted-foreground"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          >
            <Timer className="h-3 w-3" />
            <span>Live</span>
          </motion.div>
        )}
      </div>

      {/* Countdown Display */}
      {isExpired ? (
        <motion.div
          className="text-center py-2"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={springs.bouncy}
        >
          <div className="flex items-center justify-center gap-2 text-error">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
            >
              <AlertOctagon className="h-6 w-6" />
            </motion.div>
            <span className="text-xl font-bold">PONR PASSED</span>
          </div>
          <p className="text-sm text-error/80 mt-1">Options are now severely limited</p>
        </motion.div>
      ) : (
        <>
          {/* Time blocks */}
          <div className="grid grid-cols-4 gap-2">
            <TimeBlock value={timeRemaining.days} label="DAYS" critical={isCritical} />
            <TimeBlock value={timeRemaining.hours} label="HRS" critical={isCritical} />
            <TimeBlock value={timeRemaining.minutes} label="MIN" critical={isCritical} />
            <TimeBlock value={timeRemaining.seconds} label="SEC" critical={isCritical} />
          </div>

          {/* Progress bar */}
          <div className="space-y-1">
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <motion.div
                className={cn(
                  'h-full rounded-full',
                  isCritical ? 'bg-error' : isUrgent ? 'bg-orange-500' : 'bg-warning',
                )}
                initial={{ width: 0 }}
                animate={{ width: `${percentRemaining}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
            </div>
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Now</span>
              <span>{formatDate(pointOfNoReturn, { includeTime: true })}</span>
            </div>
          </div>

          {/* Urgency message */}
          {isCritical && (
            <motion.div
              className="flex items-center gap-2 text-sm text-error bg-error/10 rounded p-2"
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springs.smooth}
            >
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 0.5, repeat: Infinity }}
              >
                <AlertTriangle className="h-4 w-4 shrink-0" />
              </motion.div>
              <span className="font-medium">Critical: Action required within the hour!</span>
            </motion.div>
          )}
          {isUrgent && !isCritical && (
            <motion.div
              className="flex items-center gap-2 text-sm text-warning bg-orange-500/10 rounded p-2"
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springs.smooth}
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>Urgent: Less than 24 hours remaining</span>
            </motion.div>
          )}
        </>
      )}

      {/* Info text */}
      <p className="text-xs text-muted-foreground">
        After this point, recovery options become significantly more expensive or unavailable
      </p>
    </motion.div>
  );
}

interface TimeBlockProps {
  value: number;
  label: string;
  critical?: boolean;
}

function TimeBlock({ value, label, critical }: TimeBlockProps) {
  return (
    <motion.div
      className={cn(
        'text-center rounded-lg py-2 px-1',
        critical ? 'bg-error/20' : 'bg-muted/50',
      )}
      whileHover={{ scale: 1.05 }}
      transition={springs.snappy}
    >
      <motion.div
        className={cn(
          'font-mono text-2xl font-bold tabular-nums',
          critical ? 'text-error' : 'text-primary',
        )}
        key={value}
        initial={{ y: -5, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {String(value).padStart(2, '0')}
      </motion.div>
      <div className="text-[10px] font-medium text-muted-foreground tracking-wider">{label}</div>
    </motion.div>
  );
}

function getTimeRemaining(targetDate: Date) {
  const now = new Date();
  const total = targetDate.getTime() - now.getTime();

  if (total <= 0) {
    return { total: 0, days: 0, hours: 0, minutes: 0, seconds: 0 };
  }

  const days = Math.floor(total / (1000 * 60 * 60 * 24));
  const hours = Math.floor((total % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((total % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((total % (1000 * 60)) / 1000);

  return { total, days, hours, minutes, seconds };
}

interface CostEscalationItemProps {
  point: CostEscalationPoint;
  isLast: boolean;
  progress: number; // 0 to 1
  index: number;
}

function CostEscalationItem({ point, isLast: _isLast, progress, index }: CostEscalationItemProps) {
  const timestamp = new Date(point.timestamp);

  // Color based on progress through escalation
  const dotColor = progress < 0.33 ? 'bg-warning' : progress < 0.66 ? 'bg-orange-500' : 'bg-error';

  const textColor =
    progress < 0.33 ? 'text-warning' : progress < 0.66 ? 'text-orange-500' : 'text-error';

  return (
    <motion.div
      className="flex items-start gap-4 pl-0"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 * index, ...springs.smooth }}
    >
      {/* Timeline dot */}
      <motion.div
        className={cn(
          'relative z-10 h-6 w-6 rounded-full flex items-center justify-center',
          dotColor,
        )}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1 * index + 0.1, ...springs.bouncy }}
        whileHover={{ scale: 1.15 }}
      >
        <div className="h-2 w-2 rounded-full bg-background" />
      </motion.div>

      {/* Content */}
      <div className="flex-1 pt-0.5">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-muted-foreground">
            {formatDate(timestamp, { includeTime: true })}
          </span>
          <motion.span
            className={cn('font-mono text-lg font-semibold font-tabular', textColor)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 * index + 0.2 }}
          >
            {formatCurrency(point.cost_usd)}
          </motion.span>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{point.description}</p>
      </div>
    </motion.div>
  );
}
