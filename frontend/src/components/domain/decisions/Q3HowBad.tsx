import { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { SeverityBadge } from '@/components/domain/common/SeverityBadge';
import { ExposureChart } from '@/components/charts/ExposureChart';
import {
  ScenarioVisualization,
  createScenariosFromDecision,
} from '@/components/charts/ScenarioVisualization';
import { AnimatedNumber, AnimatedCurrency } from '@/components/ui/animated-number';
import {
  Package,
  Clock,
  Ship,
  ChevronRight,
  BarChart3,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDelayRange } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type { Q3HowBadIsIt as Q3Data } from '@/types/decision';

interface Q3Props {
  data: Q3Data;
  className?: string;
}

export function Q3HowBad({ data, className }: Q3Props) {
  const [showAllShipments, setShowAllShipments] = useState(false);
  const displayedShipments = showAllShipments
    ? data.breakdown_by_shipment
    : data.breakdown_by_shipment.slice(0, 3);

  // Get severity color for border
  const severityBorderColors = {
    CRITICAL: 'border-l-severity-critical',
    HIGH: 'border-l-severity-high',
    MEDIUM: 'border-l-severity-medium',
    LOW: 'border-l-severity-low',
  };

  const severityGlowColors = {
    CRITICAL: 'shadow-severity-critical/20',
    HIGH: 'shadow-severity-high/20',
    MEDIUM: 'shadow-severity-medium/20',
    LOW: 'shadow-severity-low/20',
  };

  return (
    <section aria-labelledby="q3-heading">
      <Card
        className={cn(
          'border-l-4 overflow-hidden',
          severityBorderColors[data.severity],
          data.severity === 'CRITICAL' && 'shadow-lg',
          data.severity === 'CRITICAL' && severityGlowColors[data.severity],
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
                id="q3-heading"
                className="text-sm font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-2"
              >
                <AlertCircle
                  className={cn(
                    'h-4 w-4',
                    data.severity === 'CRITICAL' && 'text-severity-critical',
                    data.severity === 'HIGH' && 'text-severity-high',
                    data.severity === 'MEDIUM' && 'text-severity-medium',
                    data.severity === 'LOW' && 'text-severity-low',
                  )}
                />
                Q3: How Bad Is It?
              </CardTitle>
            </motion.div>
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, ...springs.bouncy }}
            >
              <SeverityBadge severity={data.severity} />
            </motion.div>
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {/* Main Metrics - BIG NUMBERS with animation */}
          <motion.div
            className="grid gap-6 sm:grid-cols-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, ...springs.smooth }}
          >
            {/* Total Exposure */}
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Total Exposure
              </p>
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, ...springs.bouncy }}
              >
                <p className="font-mono text-4xl font-bold text-primary font-tabular">
                  <AnimatedCurrency value={data.total_exposure_usd} duration={1} />
                </p>
              </motion.div>
              {data.exposure_ci_90 && (
                <p className="text-sm text-muted-foreground">
                  90% CI: {formatCurrency(data.exposure_ci_90.lower, { compact: true })} -{' '}
                  {formatCurrency(data.exposure_ci_90.upper, { compact: true })}
                </p>
              )}
            </div>

            {/* Expected Delay */}
            <div className="space-y-1">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Expected Delay
              </p>
              <motion.div
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.25, ...springs.bouncy }}
              >
                <p className="font-mono text-4xl font-semibold text-primary font-tabular">
                  {formatDelayRange(data.delay_range[0], data.delay_range[1])}
                </p>
              </motion.div>
              <p className="text-sm text-muted-foreground">
                Most likely: <span className="font-medium">{data.expected_delay_days} days</span>
              </p>
            </div>
          </motion.div>

          {/* Secondary Metrics with stagger */}
          <motion.div
            className="grid gap-4 sm:grid-cols-3"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            <motion.div
              variants={staggerItem}
              className="rounded-xl bg-muted/50 p-4 space-y-1 hover:bg-muted transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Ship className="h-3.5 w-3.5" />
                <span>Shipments</span>
              </div>
              <p className="font-mono text-2xl font-semibold text-primary font-tabular">
                <AnimatedNumber value={data.shipments_affected} />
              </p>
            </motion.div>

            <motion.div
              variants={staggerItem}
              className="rounded-xl bg-muted/50 p-4 space-y-1 hover:bg-muted transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Package className="h-3.5 w-3.5" />
                <span>TEU</span>
              </div>
              <p className="font-mono text-2xl font-semibold text-primary font-tabular">
                <AnimatedNumber value={data.teu_affected} />
              </p>
            </motion.div>

            <motion.div
              variants={staggerItem}
              className="rounded-xl bg-muted/50 p-4 space-y-1 hover:bg-muted transition-colors"
              whileHover={{ scale: 1.02 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>Avg/Shipment</span>
              </div>
              <p className="font-mono text-2xl font-semibold text-primary font-tabular">
                <AnimatedCurrency
                  value={data.shipments_affected > 0 ? data.total_exposure_usd / data.shipments_affected : 0}
                  compact
                />
              </p>
            </motion.div>
          </motion.div>

          {/* Scenario Analysis - Best/Base/Worst Case */}
          <motion.div
            className="space-y-3 pt-2 border-t"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <TrendingDown className="h-3.5 w-3.5" />
              <span>Scenario Analysis</span>
            </div>

            <ScenarioVisualization
              scenarios={createScenariosFromDecision(
                data.total_exposure_usd,
                data.expected_delay_days,
              )}
              currentChoice="base"
            />
          </motion.div>

          {/* Exposure Chart - VISUAL DISTRIBUTION */}
          {data.breakdown_by_shipment.length > 0 && (
            <motion.div
              className="space-y-3 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                <span>Exposure Distribution</span>
              </div>

              {/* Visual Chart */}
              <ExposureChart
                data={data.breakdown_by_shipment}
                className="border-none shadow-none -mx-2"
              />
            </motion.div>
          )}

          {/* Shipment Breakdown - Detailed List */}
          {data.breakdown_by_shipment.length > 0 && (
            <motion.div
              className="space-y-3 pt-2 border-t"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Affected Shipments Detail
                </span>
                <motion.button
                  className="text-xs text-accent hover:underline flex items-center gap-1"
                  whileHover={{ x: 2 }}
                  onClick={() => setShowAllShipments((prev) => !prev)}
                >
                  {showAllShipments ? 'Show fewer' : 'View all'}
                  <ChevronRight
                    className={cn(
                      'h-3 w-3 transition-transform',
                      showAllShipments && 'rotate-90',
                    )}
                  />
                </motion.button>
              </div>

              <motion.div
                className="space-y-2"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {displayedShipments.map((shipment) => (
                  <motion.div
                    key={shipment.shipment_id}
                    variants={staggerItem}
                    className="flex items-center justify-between rounded-xl bg-muted/50 px-4 py-3 hover:bg-muted transition-colors"
                    whileHover={{ x: 4 }}
                  >
                    <div className="space-y-0.5">
                      <p className="font-mono text-sm font-medium">{shipment.shipment_id}</p>
                      <p className="text-xs text-muted-foreground">{shipment.route}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm font-semibold font-tabular">
                        {formatCurrency(shipment.exposure_usd)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Cargo: {formatCurrency(shipment.cargo_value_usd, { compact: true })}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {!showAllShipments && data.breakdown_by_shipment.length > 3 && (
                <p className="text-xs text-muted-foreground text-center">
                  +{data.breakdown_by_shipment.length - 3} more shipments
                </p>
              )}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
