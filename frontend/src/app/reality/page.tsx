import { useState } from 'react';
import { motion } from 'framer-motion';
import { useRealityEngine } from '@/hooks/useRealityEngine';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  Globe,
  Ship,
  Anchor,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  MapPin,
  Clock,
  AlertTriangle,
  CheckCircle,
  Activity,
  Waves,
  Wind,
  DollarSign,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';
import { AnimatedNumber, AnimatedCurrency } from '@/components/ui/animated-number';

type ChokepointStatus = 'NORMAL' | 'CONGESTED' | 'DISRUPTED' | 'CRITICAL';

interface ChokepointHealth {
  id: string;
  name: string;
  region: string;
  status: ChokepointStatus;
  vessels_waiting: number;
  avg_delay_days: number;
  transit_time_change: number;
  last_updated: string;
  incidents: string[];
  weather: { condition: string; wind_speed_knots: number; wave_height_m: number };
}
interface FreightRate {
  route: string;
  current_usd: number;
  week_ago_usd: number;
  change_pct: number;
  trend: 'UP' | 'DOWN' | 'STABLE';
  last_updated: string;
}
interface VesselAlert {
  id: string;
  vessel_name: string;
  imo: string;
  alert_type: 'DIVERSION' | 'DELAY' | 'PORT_CHANGE' | 'SPEED_CHANGE';
  message: string;
  timestamp: string;
  route: string;
}

const statusConfig: Record<
  ChokepointStatus,
  { label: string; className: string; icon: typeof CheckCircle; gradient: string }
> = {
  NORMAL: {
    label: 'Normal',
    className:
      'bg-gradient-to-r from-success to-success text-white shadow-lg shadow-success/25',
    icon: CheckCircle,
    gradient: 'from-success/20 to-success/10',
  },
  CONGESTED: {
    label: 'Congested',
    className:
      'bg-gradient-to-r from-warning to-warning text-white shadow-lg shadow-warning/25',
    icon: Clock,
    gradient: 'from-warning/20 to-warning/10',
  },
  DISRUPTED: {
    label: 'Disrupted',
    className:
      'bg-gradient-to-r from-error to-error text-white shadow-lg shadow-error/25',
    icon: AlertTriangle,
    gradient: 'from-error/20 to-error/10',
  },
  CRITICAL: {
    label: 'Critical',
    className:
      'bg-gradient-to-r from-error to-error text-white shadow-lg shadow-error/30 animate-pulse',
    icon: AlertTriangle,
    gradient: 'from-error/20 to-error/10',
  },
};

const alertTypeConfig = {
  DIVERSION: {
    label: 'Diversion',
    className: 'bg-action-reroute/10 text-action-reroute border border-action-reroute/30',
  },
  DELAY: {
    label: 'Delay',
    className: 'bg-warning/10 text-warning border border-warning/30',
  },
  PORT_CHANGE: {
    label: 'Port Change',
    className: 'bg-info/10 text-info border border-info/30',
  },
  SPEED_CHANGE: {
    label: 'Speed Change',
    className: 'bg-muted text-muted-foreground border border-border',
  },
};

export function RealityPage() {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const { data, isLoading, error, refetch } = useRealityEngine();

  // Map hook data to local types
  const chokepoints: ChokepointHealth[] = (data?.chokepoints ?? []).map(cp => ({
    id: cp.id,
    name: cp.name,
    region: cp.region,
    status: (cp.status === 'critical' ? 'CRITICAL' : cp.status === 'degraded' ? 'CONGESTED' : 'NORMAL') as ChokepointStatus,
    vessels_waiting: cp.vesselCount,
    avg_delay_days: cp.transitDelayDays,
    transit_time_change: cp.transitDelayDays > 0 ? cp.transitDelayDays * 8 : 0,
    last_updated: cp.lastIncident,
    incidents: [],
    weather: { condition: 'N/A', wind_speed_knots: 0, wave_height_m: 0 },
  }));

  const rates: FreightRate[] = (data?.rates ?? []).map(r => ({
    route: r.route,
    current_usd: r.currentRate,
    week_ago_usd: r.previousRate,
    change_pct: Math.round(r.change * 10) / 10,
    trend: (r.change > 2 ? 'UP' : r.change < -2 ? 'DOWN' : 'STABLE') as FreightRate['trend'],
    last_updated: r.lastUpdated,
  }));

  const vesselAlerts: VesselAlert[] = (data?.vesselAlerts ?? []).map(a => ({
    id: a.id,
    vessel_name: a.vesselName,
    imo: '',
    alert_type: (a.alertType === 'port_congestion' ? 'PORT_CHANGE' : a.alertType.toUpperCase()) as VesselAlert['alert_type'],
    message: a.description,
    timestamp: a.timestamp,
    route: a.location,
  }));

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const criticalCount = chokepoints.filter(
    (c) => c.status === 'CRITICAL' || c.status === 'DISRUPTED',
  ).length;
  const congestedCount = chokepoints.filter((c) => c.status === 'CONGESTED').length;
  const totalVessels = chokepoints.reduce((sum, c) => sum + c.vessels_waiting, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <Globe className="h-8 w-8 animate-pulse text-accent mx-auto" />
          <p className="text-sm text-muted-foreground">Loading reality data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-sm text-error">Failed to load reality data</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Page Header */}
      <motion.div
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div>
          <motion.h1
            className="text-3xl font-bold bg-gradient-to-r from-foreground via-foreground/90 to-foreground/70 bg-clip-text text-transparent flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <motion.div
              className="p-2 rounded-xl bg-gradient-to-br from-accent/20 to-accent/20"
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 6, repeat: Infinity }}
            >
              <Globe className="h-6 w-6 text-accent" />
            </motion.div>
            Reality (Oracle)
          </motion.h1>
          <motion.p
            className="text-sm text-muted-foreground mt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Real-time global shipping intelligence • Last updated{' '}
            {formatDate(new Date().toISOString(), { relative: true })}
          </motion.p>
        </div>

        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
          <Button
            variant="outline"
            className="gap-2 bg-gradient-to-r from-accent/10 to-accent/10 border-accent/30 hover:border-accent/50 shadow-lg"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn('h-4 w-4 text-accent', isRefreshing && 'animate-spin')} />
            <span className="font-medium">{isRefreshing ? 'Refreshing...' : 'Refresh Data'}</span>
          </Button>
        </motion.div>
      </motion.div>

      {/* Global Status Summary */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            icon={AlertTriangle}
            accentColor="red"
            value={criticalCount}
            label="Critical/Disrupted"
            urgent={criticalCount > 0}
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Clock}
            accentColor="orange"
            value={congestedCount}
            label="Congested Routes"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Ship}
            accentColor="blue"
            value={totalVessels}
            label="Vessels Waiting"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={TrendingUp}
            accentColor="red"
            value="+31%"
            label="Avg Rate Change"
            variant="overlay"
          />
        </motion.div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chokepoint Health - 2 columns */}
        <motion.div
          className="lg:col-span-2"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, ...springs.smooth }}
        >
          <Card className="overflow-hidden shadow-md bg-card shadow-sm">
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-accent" />
                Chokepoint Health
              </CardTitle>
              <CardDescription>Real-time status of major shipping chokepoints</CardDescription>
            </CardHeader>
            <CardContent>
              <motion.div
                className="space-y-4"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {chokepoints.map((chokepoint) => {
                  const config = statusConfig[chokepoint.status];
                  const StatusIcon = config.icon;
                  return (
                    <motion.div
                      key={chokepoint.id}
                      variants={staggerItem}
                      whileHover={{ x: 4, scale: 1.005 }}
                      transition={springs.snappy}
                      className={cn(
                        'p-4 rounded-xl transition-all bg-gradient-to-r',
                        config.gradient,
                        chokepoint.status === 'CRITICAL' && 'ring-1 ring-error/40',
                        chokepoint.status === 'DISRUPTED' && 'ring-1 ring-error/30',
                      )}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-bold">{chokepoint.name}</h3>
                            <Badge className={config.className}>
                              <StatusIcon className="h-3 w-3 mr-1" />
                              {config.label}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {chokepoint.region}
                            </span>
                          </div>

                          {chokepoint.incidents.length > 0 && (
                            <ul className="text-sm text-muted-foreground space-y-1">
                              {chokepoint.incidents.map((incident, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  <AlertTriangle className="h-3 w-3 mt-1 shrink-0 text-warning" />
                                  {incident}
                                </li>
                              ))}
                            </ul>
                          )}

                          <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2">
                            <span>{chokepoint.weather.condition}</span>
                            <span className="flex items-center gap-1">
                              <Wind className="h-3 w-3" />
                              {chokepoint.weather.wind_speed_knots} kts
                            </span>
                            <span className="flex items-center gap-1">
                              <Waves className="h-3 w-3" />
                              {chokepoint.weather.wave_height_m}m
                            </span>
                          </div>
                        </div>

                        <div className="text-right space-y-2 shrink-0">
                          <div className="p-2 rounded-lg bg-background/50">
                            <p className="font-mono text-xl font-bold">
                              <AnimatedNumber value={chokepoint.vessels_waiting} />
                            </p>
                            <p className="text-xs text-muted-foreground">Vessels</p>
                          </div>
                          <div className="p-2 rounded-lg bg-background/50">
                            <p
                              className={cn(
                                'font-mono text-sm font-bold',
                                chokepoint.avg_delay_days > 5 && 'text-error',
                              )}
                            >
                              +{chokepoint.avg_delay_days}d
                            </p>
                            <p className="text-xs text-muted-foreground">Avg Delay</p>
                          </div>
                          {chokepoint.transit_time_change > 0 && (
                            <div className="p-2 rounded-lg bg-background/50">
                              <p className="font-mono text-sm font-bold text-error">
                                +{chokepoint.transit_time_change}%
                              </p>
                              <p className="text-xs text-muted-foreground">Transit Time</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Freight Rates */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, ...springs.smooth }}
        >
          <Card className="overflow-hidden shadow-md bg-card shadow-sm h-full">
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-success/50 to-transparent" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-success" />
                Spot Rates (FEU)
              </CardTitle>
              <CardDescription>Current container shipping rates</CardDescription>
            </CardHeader>
            <CardContent>
              <motion.div
                className="space-y-3"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {rates.map((rate) => (
                  <motion.div
                    key={rate.route}
                    variants={staggerItem}
                    whileHover={{ x: 4 }}
                    className="flex items-center justify-between p-3 rounded-xl bg-muted/40 hover:bg-muted transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium">{rate.route}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(rate.last_updated, { relative: true })}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono font-bold">
                        <AnimatedCurrency value={rate.current_usd} />
                      </p>
                      <p
                        className={cn(
                          'text-xs font-mono font-bold flex items-center gap-1 justify-end',
                          rate.change_pct > 0
                            ? 'text-error'
                            : rate.change_pct < 0
                              ? 'text-success'
                              : 'text-muted-foreground',
                        )}
                      >
                        {rate.change_pct > 0 ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : rate.change_pct < 0 ? (
                          <TrendingDown className="h-3 w-3" />
                        ) : null}
                        {rate.change_pct > 0 ? '+' : ''}
                        {rate.change_pct}%
                      </p>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Vessel Alerts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, ...springs.smooth }}
      >
        <Card className="overflow-hidden shadow-md bg-card shadow-sm">
          <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-purple-500/50 to-transparent" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-500" />
              Recent Vessel Alerts
            </CardTitle>
            <CardDescription>
              Real-time updates from AIS tracking and carrier notifications
            </CardDescription>
          </CardHeader>
          <CardContent>
            <motion.div
              className="space-y-3"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {vesselAlerts.map((alert) => {
                const config = alertTypeConfig[alert.alert_type];
                return (
                  <motion.div
                    key={alert.id}
                    variants={staggerItem}
                    whileHover={{ x: 4, scale: 1.005 }}
                    transition={springs.snappy}
                    className="flex items-start gap-4 p-4 rounded-xl bg-muted/40 hover:bg-muted transition-colors"
                  >
                    <motion.div
                      className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted shrink-0"
                      whileHover={{ scale: 1.1, rotate: 5 }}
                    >
                      <Anchor className="h-5 w-5 text-purple-500" />
                    </motion.div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-bold text-sm">{alert.vessel_name}</span>
                        <Badge className={config.className}>{config.label}</Badge>
                        <span className="text-xs text-muted-foreground font-mono">{alert.imo}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.message}</p>
                      <p className="text-xs text-muted-foreground mt-1">Route: {alert.route}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-muted-foreground font-mono">
                        {formatDate(alert.timestamp, { relative: true })}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}

export default RealityPage;
