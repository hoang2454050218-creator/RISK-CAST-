import { useState } from 'react';
import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge, AnimatedBadge } from '@/components/ui/badge';
import { MapPin, Route, Quote, Ship, AlertTriangle, ChevronRight, Zap, Radio } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import type { Q1WhatIsHappening as Q1Data, Chokepoint, ShipmentExposure } from '@/types/decision';

interface Q1Props {
  data: Q1Data;
  /** Optional: affected shipments for at-a-glance preview */
  affectedShipments?: ShipmentExposure[];
  /** Optional: linked signal IDs for cross-referencing */
  signalIds?: string[];
  className?: string;
}

const chokepointLabels: Record<Chokepoint, string> = {
  RED_SEA: 'Red Sea',
  SUEZ: 'Suez Canal',
  PANAMA: 'Panama Canal',
  MALACCA: 'Strait of Malacca',
  STRAIT_OF_HORMUZ: 'Strait of Hormuz',
};

export function Q1WhatIsHappening({ data, affectedShipments, signalIds, className }: Q1Props) {
  const [showAllShipments, setShowAllShipments] = useState(false);
  const displayedShipments = affectedShipments
    ? showAllShipments
      ? affectedShipments
      : affectedShipments.slice(0, 3)
    : [];

  return (
    <section aria-labelledby="q1-heading">
      <Card className={cn('border-l-4 border-l-accent overflow-hidden', className)}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={springs.smooth}
            >
              <CardTitle
                id="q1-heading"
                className="text-sm font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-2"
              >
                <Zap className="h-4 w-4 text-accent" />
                Q1: What is Happening?
              </CardTitle>
            </motion.div>
            <AnimatedBadge variant="outline" delay={0.2}>
              {data.event_type}
            </AnimatedBadge>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Event Summary - The main headline */}
          <motion.div
            className="space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, ...springs.smooth }}
          >
            <p className="text-lg font-semibold leading-snug text-primary">{data.event_summary}</p>
          </motion.div>

          {/* Personalized Impact - Why this matters to YOU */}
          <motion.div
            className="rounded-xl bg-gradient-to-r from-accent/5 to-action-reroute/5 border border-accent/20 p-4"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.15, ...springs.smooth }}
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-start gap-3">
              <motion.div
                initial={{ rotate: -10, scale: 0 }}
                animate={{ rotate: 0, scale: 1 }}
                transition={{ delay: 0.3, ...springs.bouncy }}
              >
                <Quote className="h-5 w-5 text-accent shrink-0 mt-0.5" />
              </motion.div>
              <p className="text-sm font-medium text-primary">{data.personalized_impact}</p>
            </div>
          </motion.div>

          {/* Affected Shipments At-a-Glance */}
          {affectedShipments && affectedShipments.length > 0 && (
            <motion.div
              className="space-y-3 rounded-xl bg-severity-high/5 border border-severity-high/20 p-4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, ...springs.smooth }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <AlertTriangle className="h-4 w-4 text-severity-high" />
                  </motion.div>
                  <span className="text-xs font-semibold uppercase tracking-wide text-severity-high">
                    Your Affected Shipments
                  </span>
                </div>
                <Badge variant="high" className="text-xs" pulse>
                  {affectedShipments.length} at risk
                </Badge>
              </div>

              {/* Quick shipment list with stagger animation */}
              <motion.div
                className="space-y-1.5"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {displayedShipments.map((shipment) => (
                  <motion.div
                    key={shipment.shipment_id}
                    variants={staggerItem}
                    className="flex items-center justify-between rounded-lg bg-background/80 px-3 py-2 hover:bg-background transition-colors"
                    whileHover={{ x: 4 }}
                  >
                    <div className="flex items-center gap-2">
                      <Ship className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-mono text-xs font-medium">{shipment.shipment_id}</span>
                      <span className="text-xs text-muted-foreground">• {shipment.route}</span>
                    </div>
                    <span className="font-mono text-xs font-semibold text-severity-high font-tabular">
                      {formatCurrency(shipment.exposure_usd, { compact: true })}
                    </span>
                  </motion.div>
                ))}
              </motion.div>

              {affectedShipments.length > 3 && (
                <motion.button
                  className="w-full flex items-center justify-center gap-1 text-xs text-severity-high hover:underline"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setShowAllShipments((prev) => !prev)}
                >
                  <span>
                    {showAllShipments
                      ? 'Show fewer'
                      : `View all ${affectedShipments.length} shipments`}
                  </span>
                  <ChevronRight
                    className={cn(
                      'h-3 w-3 transition-transform',
                      showAllShipments && 'rotate-90',
                    )}
                  />
                </motion.button>
              )}

              {/* Total exposure summary */}
              <div className="flex items-center justify-between pt-2 border-t border-severity-high/20">
                <span className="text-xs text-muted-foreground">Total exposure at risk</span>
                <motion.span
                  className="font-mono text-sm font-bold text-severity-high font-tabular"
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={springs.bouncy}
                >
                  {formatCurrency(affectedShipments.reduce((sum, s) => sum + s.exposure_usd, 0))}
                </motion.span>
              </div>
            </motion.div>
          )}

          {/* Affected Areas */}
          <motion.div
            className="grid gap-4 sm:grid-cols-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {/* Chokepoints */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <MapPin className="h-3.5 w-3.5" />
                <span>Affected Chokepoints</span>
              </div>
              <motion.div
                className="flex flex-wrap gap-1.5"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {data.affected_chokepoints.map((chokepoint) => (
                  <motion.div key={chokepoint} variants={staggerItem}>
                    <Link to={`/signals?chokepoint=${chokepoint}`}>
                      <Badge variant="secondary" className="text-xs hover:bg-accent/10 cursor-pointer transition-colors">
                        {chokepointLabels[chokepoint] || chokepoint}
                        <ChevronRight className="h-3 w-3 ml-0.5" />
                      </Badge>
                    </Link>
                  </motion.div>
                ))}
              </motion.div>
            </div>

            {/* Routes */}
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Route className="h-3.5 w-3.5" />
                <span>Affected Routes</span>
              </div>
              <motion.div
                className="flex flex-wrap gap-1.5"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {data.affected_routes.map((route) => (
                  <motion.div key={route} variants={staggerItem}>
                    <Badge variant="outline" className="text-xs">
                      {route}
                    </Badge>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </motion.div>

          {/* Linked Signals — Cross-reference trail */}
          {signalIds && signalIds.length > 0 && (
            <motion.div
              className="space-y-2 pt-2 border-t border-border/50"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, ...springs.smooth }}
            >
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Radio className="h-3.5 w-3.5 text-info" />
                <span>Based on {signalIds.length} signal{signalIds.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {signalIds.map((id) => (
                  <Link
                    key={id}
                    to={`/signals`}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-info/5 border border-info/20 text-[11px] font-mono text-info hover:bg-info/10 transition-colors"
                  >
                    {id}
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                ))}
              </div>
            </motion.div>
          )}

          {/* Source Attribution */}
          <motion.div
            className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <span>Source:</span>
            <span className="font-medium">{data.source_attribution}</span>
          </motion.div>
        </CardContent>
      </Card>
    </section>
  );
}
