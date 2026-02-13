/**
 * SignalCard - Ultra-Premium Bloomberg-Grade Design
 * Glass morphism, glow borders, animated data visualization
 * "Each card is a mini intelligence briefing"
 */

import { Link } from 'react-router';
import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import {
  AlertTriangle,
  Ship,
  CloudRain,
  Globe,
  TrendingUp,
  Truck,
  FileText,
  MapPin,
  Radio,
  ArrowUpRight,
  BarChart3,
  Shield,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { springs } from '@/lib/animations';
import type { Signal, SignalStatus, EventType, SignalSource } from '@/types/signal';

interface SignalCardProps {
  signal: Signal;
  variant?: 'default' | 'compact';
  className?: string;
}

const eventTypeConfig: Record<EventType, { icon: typeof AlertTriangle; label: string; color: string; bg: string }> = {
  ROUTE_DISRUPTION: { icon: Ship, label: 'Route Disruption', color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/20' },
  PORT_CONGESTION: { icon: MapPin, label: 'Port Congestion', color: 'text-warning', bg: 'bg-warning/10 border-warning/20' },
  WEATHER_EVENT: { icon: CloudRain, label: 'Weather Event', color: 'text-info', bg: 'bg-info/10 border-info/20' },
  GEOPOLITICAL: { icon: Globe, label: 'Geopolitical', color: 'text-action-reroute', bg: 'bg-action-reroute/10 border-action-reroute/20' },
  RATE_SPIKE: { icon: TrendingUp, label: 'Rate Spike', color: 'text-urgency-soon', bg: 'bg-urgency-soon/10 border-urgency-soon/20' },
  CARRIER_ISSUE: { icon: Truck, label: 'Carrier Issue', color: 'text-action-insure', bg: 'bg-action-insure/10 border-action-insure/20' },
  CUSTOMS_DELAY: { icon: FileText, label: 'Customs Delay', color: 'text-success', bg: 'bg-success/10 border-success/20' },
};

const statusStyle: Record<SignalStatus, {
  label: string;
  topGradient: string;
  badge: string;
  dotColor: string;
  glowClass: string;
  borderClass: string;
}> = {
  ACTIVE: {
    label: 'Active',
    topGradient: 'from-urgency-urgent via-urgency-urgent/80 to-urgency-urgent',
    badge: 'bg-urgency-urgent/15 text-urgency-urgent border-urgency-urgent/30',
    dotColor: 'bg-urgency-urgent',
    glowClass: 'rc-glow-amber', // lint-ignore-token — glow class in index.css
    borderClass: 'border-urgency-urgent/20',
  },
  CONFIRMED: {
    label: 'Confirmed',
    topGradient: 'from-urgency-immediate via-urgency-immediate/80 to-urgency-immediate',
    badge: 'bg-urgency-immediate/15 text-urgency-immediate border-urgency-immediate/30',
    dotColor: 'bg-urgency-immediate',
    glowClass: 'rc-glow-red', // lint-ignore-token
    borderClass: 'border-urgency-immediate/20',
  },
  EXPIRED: {
    label: 'Expired',
    topGradient: 'from-muted-foreground/40 via-muted-foreground/30 to-muted-foreground/40',
    badge: 'bg-muted-foreground/10 text-muted-foreground border-muted-foreground/20',
    dotColor: 'bg-muted-foreground',
    glowClass: '',
    borderClass: 'border-border',
  },
  DISMISSED: {
    label: 'Dismissed',
    topGradient: 'from-muted-foreground/40 via-muted-foreground/30 to-muted-foreground/40',
    badge: 'bg-muted-foreground/10 text-muted-foreground border-muted-foreground/20',
    dotColor: 'bg-muted-foreground',
    glowClass: '',
    borderClass: 'border-border',
  },
};

const sourceConfig: Record<SignalSource, { label: string; className: string }> = {
  POLYMARKET: { label: 'Polymarket', className: 'bg-action-reroute/10 text-action-reroute border-action-reroute/25' },
  NEWS: { label: 'News', className: 'bg-info/10 text-info border-info/25' },
  AIS: { label: 'AIS', className: 'bg-success/10 text-success border-success/25' },
  RATES: { label: 'Rates', className: 'bg-warning/10 text-warning border-warning/25' },
  WEATHER: { label: 'Weather', className: 'bg-action-insure/10 text-action-insure border-action-insure/25' },
  GOVERNMENT: { label: "Gov't", className: 'bg-muted-foreground/10 text-muted-foreground border-muted-foreground/25' },
  SOCIAL_MEDIA: { label: 'Social', className: 'bg-category-social/10 text-category-social border-category-social/25' },
};

const defaults = {
  event: { icon: Radio, label: 'Unknown', color: 'text-muted-foreground', bg: 'bg-muted-foreground/10 border-muted-foreground/20' },
  status: statusStyle.EXPIRED,
  source: { label: 'Unknown', className: 'bg-muted-foreground/10 text-muted-foreground border-muted-foreground/20' },
};

// Get probability color — uses design tokens
function getProbColor(p: number) {
  if (p >= 80) return { text: 'text-destructive', bar: 'bg-destructive', glow: 'rc-text-glow-red' };
  if (p >= 60) return { text: 'text-warning', bar: 'bg-warning', glow: 'rc-text-glow-amber' };
  if (p >= 40) return { text: 'text-info', bar: 'bg-info', glow: 'rc-text-glow-blue' };
  return { text: 'text-muted-foreground', bar: 'bg-muted-foreground', glow: '' };
}

function getConfColor(c: number) {
  if (c >= 80) return { text: 'text-confidence-high', bar: 'bg-confidence-high' };
  if (c >= 50) return { text: 'text-confidence-medium', bar: 'bg-confidence-medium' };
  return { text: 'text-confidence-low', bar: 'bg-confidence-low' };
}

export function SignalCard({ signal, variant = 'default', className }: SignalCardProps) {
  const evtCfg = eventTypeConfig[signal.event_type] ?? defaults.event;
  const status = statusStyle[signal.status] ?? defaults.status;
  const source = sourceConfig[signal.primary_source] ?? defaults.source;
  const Icon = evtCfg.icon;
  const isActive = signal.status === 'ACTIVE' || signal.status === 'CONFIRMED';
  const probColor = getProbColor(signal.probability);
  const confColor = getConfColor(signal.confidence ?? 0);

  if (variant === 'compact') {
    return <CompactSignalCard signal={signal} className={className} />;
  }

  return (
    <Link to={`/signals/${signal.signal_id}`} className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background">
      <motion.div
        role="article"
        aria-label={`Signal: ${signal.event_title}, Status: ${signal.status}`}
        className={cn(
          'group relative h-full flex flex-col overflow-hidden rounded-2xl',
          'bg-card/80 backdrop-blur-sm',
          'border shadow-level-1 transition-all duration-200',
          isActive ? status.borderClass : 'border-border/40',
          isActive && status.glowClass,
          'hover:shadow-level-2',
          className,
        )}
        whileHover={{ y: -6, transition: { duration: 0.25, ease: 'easeOut' } }}
      >
        {/* ── Accent top bar with shimmer ── */}
        <div className={cn('h-1.5 w-full bg-gradient-to-r relative overflow-hidden', status.topGradient)}>
          {isActive && (
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            />
          )}
        </div>

        {/* ── Header ── */}
        <div className="relative flex items-start justify-between gap-3 p-4 pb-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className={cn('flex-shrink-0 p-2.5 rounded-xl border', evtCfg.bg)}>
              <Icon className={cn('h-4.5 w-4.5', evtCfg.color)} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5">
                <Badge className={cn('text-[10px] font-mono uppercase tracking-wider border gap-1.5 px-2', status.badge)}>
                  {isActive && (
                    <span className="relative flex h-1.5 w-1.5">
                      <span className={cn('absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping', status.dotColor)} />
                      <span className={cn('relative inline-flex h-1.5 w-1.5 rounded-full', status.dotColor)} />
                    </span>
                  )}
                  {status.label}
                </Badge>
                <span className="text-[10px] text-muted-foreground/60 font-mono truncate">{evtCfg.label}</span>
              </div>
            </div>
          </div>
          <Badge className={cn('text-[10px] font-mono border flex-shrink-0', source.className)}>
            {source.label}
          </Badge>

          {/* Hover arrow */}
          <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-all duration-300 group-hover:translate-x-1 group-hover:-translate-y-1">
            <ArrowUpRight className="h-4 w-4 text-accent" />
          </div>
        </div>

        {/* ── Title + Description ── */}
        <div className="px-4 pb-3 flex-1">
          <h3 className="font-semibold text-[13px] text-foreground leading-snug line-clamp-2 group-hover:text-accent transition-colors duration-200">
            {signal.event_title}
          </h3>
          <p className="text-[11px] text-muted-foreground/70 mt-1.5 line-clamp-2 leading-relaxed">
            {signal.event_description}
          </p>
        </div>

        {/* ── Premium Data Panel ── */}
        <div className="mx-3 mb-3 rounded-xl overflow-hidden border border-border/30 bg-muted/20">
          <div className="grid grid-cols-3 divide-x divide-border/20">

            {/* Probability */}
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-1">
                <BarChart3 className="h-3 w-3 text-muted-foreground/50" />
                <span className="text-[8px] text-muted-foreground/50 uppercase tracking-[0.15em] font-mono font-medium">
                  PROB
                </span>
              </div>
              <p className={cn('font-mono text-xl font-black tabular-nums leading-none tracking-tight', probColor.text, probColor.glow)}>
                {Math.round(signal.probability)}%
              </p>
              <div className="h-1.5 w-full rounded-full bg-border/30 overflow-hidden">
                <motion.div
                  className={cn('h-full rounded-full', probColor.bar)}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(signal.probability, 100)}%` }}
                  transition={{ duration: 1, ease: [0.4, 0, 0.2, 1] }}
                />
              </div>
            </div>

            {/* Confidence */}
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-1">
                <Shield className="h-3 w-3 text-muted-foreground/50" />
                <span className="text-[8px] text-muted-foreground/50 uppercase tracking-[0.15em] font-mono font-medium">
                  CONF
                </span>
              </div>
              <p className={cn('font-mono text-xl font-black tabular-nums leading-none tracking-tight', confColor.text)}>
                {Math.round(signal.confidence ?? 0)}%
              </p>
              <div className="h-1.5 w-full rounded-full bg-border/30 overflow-hidden">
                <motion.div
                  className={cn('h-full rounded-full', confColor.bar)}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(signal.confidence ?? 0, 100)}%` }}
                  transition={{ duration: 1, ease: [0.4, 0, 0.2, 1], delay: 0.15 }}
                />
              </div>
            </div>

            {/* Impact */}
            <div className="p-3 space-y-2">
              <div className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-muted-foreground/50" />
                <span className="text-[8px] text-muted-foreground/50 uppercase tracking-[0.15em] font-mono font-medium">
                  IMPACT
                </span>
              </div>
              <p className="font-mono text-lg font-bold text-foreground/80 tabular-nums leading-none tracking-tight">
                {signal.estimated_impact_usd
                  ? formatCurrency(signal.estimated_impact_usd, { compact: true })
                  : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* ── Chokepoints ── */}
        {signal.affected_chokepoints?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-4 pb-3">
            {signal.affected_chokepoints.slice(0, 3).map((cp) => (
              <span
                key={cp}
                className="inline-flex items-center gap-1 text-[9px] font-mono px-2 py-0.5 rounded-md bg-muted/50 text-muted-foreground/70 border border-border/30"
              >
                <MapPin className="h-2.5 w-2.5" />
                {cp.replace('_', ' ').toUpperCase()}
              </span>
            ))}
          </div>
        )}

        {/* ── Footer ── */}
        <div className="flex items-center justify-between px-4 py-2.5 mt-auto border-t border-border/30 bg-muted/10">
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground/50 font-mono">
            <Layers className="h-3 w-3" />
            {signal.evidence?.length ?? 0} sources
          </span>
          <span className="text-[10px] text-muted-foreground/40 font-mono">
            {formatDate(signal.updated_at, { relative: true })}
          </span>
        </div>
      </motion.div>
    </Link>
  );
}

/* ═══════════════════════════════════════
   COMPACT VARIANT
   ═══════════════════════════════════════ */

function CompactSignalCard({ signal, className }: { signal: Signal; className?: string }) {
  const evtCfg = eventTypeConfig[signal.event_type] ?? defaults.event;
  const status = statusStyle[signal.status] ?? defaults.status;
  const source = sourceConfig[signal.primary_source] ?? defaults.source;
  const Icon = evtCfg.icon;
  const isActive = signal.status === 'ACTIVE' || signal.status === 'CONFIRMED';
  const probColor = getProbColor(signal.probability);

  return (
    <Link to={`/signals/${signal.signal_id}`} className="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background">
      <motion.div
        className={cn(
          'group relative flex items-center gap-4 p-4 rounded-2xl overflow-hidden',
          'bg-card/80 backdrop-blur-sm border shadow-level-1 transition-all duration-200',
          isActive ? status.borderClass : 'border-border/40',
          isActive && status.glowClass,
          'hover:shadow-level-2',
          className,
        )}
        whileHover={{ x: 4 }}
        transition={springs.snappy}
      >
        {/* Left accent */}
        <div className={cn('absolute inset-y-0 left-0 w-1 bg-gradient-to-b rounded-l-2xl', status.topGradient)} />

        <div className={cn('flex-shrink-0 p-2 rounded-xl border', evtCfg.bg)}>
          <Icon className={cn('h-4 w-4', evtCfg.color)} />
        </div>

        <div className="flex-1 min-w-0 pl-1">
          <div className="flex items-center gap-1.5 mb-1">
            <Badge className={cn('text-[9px] font-mono border gap-1', status.badge)}>
              {isActive && (
                <span className="relative flex h-1 w-1">
                  <span className={cn('absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping', status.dotColor)} />
                  <span className={cn('relative inline-flex h-1 w-1 rounded-full', status.dotColor)} />
                </span>
              )}
              {status.label}
            </Badge>
            <Badge className={cn('text-[9px] font-mono border', source.className)}>
              {source.label}
            </Badge>
          </div>
          <p className="font-semibold text-sm text-foreground truncate group-hover:text-accent transition-colors">{signal.event_title}</p>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground/50 font-mono">
            <span>{signal.customers_affected} customers</span>
            <span className="text-border/40">|</span>
            <span>{signal.shipments_affected} shipments</span>
          </div>
        </div>

        <div className="text-right flex-shrink-0 space-y-1">
          <p className={cn('font-mono text-2xl font-black tabular-nums tracking-tight leading-none', probColor.text, probColor.glow)}>
            {Math.round(signal.probability)}%
          </p>
          <p className="text-[8px] text-muted-foreground/40 uppercase tracking-widest font-mono">probability</p>
        </div>
      </motion.div>
    </Link>
  );
}

export default SignalCard;
