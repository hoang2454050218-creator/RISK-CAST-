import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { UrgencyBadge } from '@/components/domain/common/UrgencyBadge';
import { CountdownTimer } from '@/components/domain/common/CountdownTimer';
import {
  TimelineVisualization,
  createTimelineMilestones,
} from '@/components/charts/TimelineVisualization';
import { Clock, Calendar, AlertTriangle, Zap, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate, formatDuration } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type { Q2WhenWillItHappen as Q2Data } from '@/types/decision';

interface Q2Props {
  data: Q2Data;
  className?: string;
}

export function Q2When({ data, className }: Q2Props) {
  const deadline = new Date(data.decision_deadline);
  const hoursToImpact = data.time_to_impact_hours;

  // Get urgency color for border
  const urgencyBorderColors = {
    IMMEDIATE: 'border-l-urgency-immediate',
    URGENT: 'border-l-urgency-urgent',
    SOON: 'border-l-urgency-soon',
    WATCH: 'border-l-urgency-watch',
  };

  // Get urgency glow
  const urgencyGlow = {
    IMMEDIATE: 'shadow-lg shadow-urgency-immediate/20',
    URGENT: 'shadow-md shadow-urgency-urgent/15',
    SOON: '',
    WATCH: '',
  };

  return (
    <section aria-labelledby="q2-heading">
      <Card
        className={cn(
          'border-l-4',
          urgencyBorderColors[data.urgency],
          urgencyGlow[data.urgency],
          className,
        )}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={springs.smooth}
            >
              <CardTitle
                id="q2-heading"
                className="text-sm font-semibold uppercase tracking-wide text-muted-foreground"
              >
                Q2: When?
              </CardTitle>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1, ...springs.bouncy }}
            >
              <UrgencyBadge urgency={data.urgency} />
            </motion.div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Decision Countdown - THE MOST IMPORTANT */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, ...springs.smooth }}
          >
            <CountdownTimer deadline={deadline} label="Decision deadline" size="lg" />
          </motion.div>

          {/* VISUAL TIMELINE - CRITICAL REQUIREMENT */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25, ...springs.smooth }}
          >
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
              >
                <GitBranch className="h-3.5 w-3.5" />
              </motion.div>
              <span>Visual Timeline</span>
            </div>
            <div className="rounded-lg bg-muted/30 p-4">
              <TimelineVisualization
                milestones={createTimelineMilestones(
                  data.decision_deadline,
                  data.time_to_impact_hours,
                )}
              />
            </div>
          </motion.div>

          {/* Timeline Grid */}
          <motion.div
            className="grid gap-4 sm:grid-cols-2"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {/* Time to Impact */}
            <motion.div
              className="rounded-lg bg-muted/50 p-4 space-y-1"
              variants={staggerItem}
              whileHover={{ scale: 1.02, backgroundColor: 'rgba(var(--muted), 0.6)' }}
              transition={springs.snappy}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
                >
                  <Zap className="h-3.5 w-3.5 text-warning" />
                </motion.div>
                <span>Time to Impact</span>
              </div>
              <motion.p
                className="font-mono text-2xl font-semibold text-primary font-tabular"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                {hoursToImpact < 24 ? `${hoursToImpact}h` : formatDuration(hoursToImpact / 24)}
              </motion.p>
            </motion.div>

            {/* Deadline Date */}
            <motion.div
              className="rounded-lg bg-muted/50 p-4 space-y-1"
              variants={staggerItem}
              whileHover={{ scale: 1.02, backgroundColor: 'rgba(var(--muted), 0.6)' }}
              transition={springs.snappy}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" />
                <span>Deadline</span>
              </div>
              <motion.p
                className="text-lg font-medium text-primary"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.45 }}
              >
                {formatDate(deadline, { includeTime: true })}
              </motion.p>
            </motion.div>
          </motion.div>

          {/* Event Timeline Description */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, ...springs.smooth }}
          >
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span>Event Timeline</span>
            </div>
            <p className="text-sm text-primary leading-relaxed">{data.event_timeline}</p>
          </motion.div>

          {/* Escalation Triggers */}
          {data.escalation_triggers.length > 0 && (
            <motion.div
              className="space-y-2 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 0.6, repeat: Infinity, repeatDelay: 1.5 }}
                >
                  <AlertTriangle className="h-3.5 w-3.5 text-warning" />
                </motion.div>
                <span>Will Escalate If</span>
              </div>
              <motion.ul
                className="space-y-1"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {data.escalation_triggers.map((trigger, index) => (
                  <motion.li
                    key={index}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                    variants={staggerItem}
                  >
                    <span className="text-warning mt-1">•</span>
                    <span>{trigger}</span>
                  </motion.li>
                ))}
              </motion.ul>
            </motion.div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
