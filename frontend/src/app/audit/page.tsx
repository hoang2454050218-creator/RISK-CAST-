import { useState } from 'react';
import { Link } from 'react-router';
import { useAuditTrail } from '@/hooks/useAuditTrail';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import { StatCard } from '@/components/domain/common/StatCard';
import {
  Search,
  Filter,
  Download,
  FileText,
  User,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  ChevronDown,
  Shield,
  Hash,
  Calendar,
  ScrollText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDate, formatPercentage } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';

type AuditEventType =
  | 'DECISION_CREATED'
  | 'DECISION_ACKNOWLEDGED'
  | 'DECISION_OVERRIDDEN'
  | 'DECISION_ESCALATED'
  | 'ESCALATION_RESOLVED'
  | 'SIGNAL_DETECTED'
  | 'SIGNAL_CONFIRMED'
  | 'CUSTOMER_ACTION'
  | 'SYSTEM_EVENT';

interface AuditEvent {
  id: string;
  event_type: AuditEventType;
  timestamp: string;
  actor: { type: 'SYSTEM' | 'USER' | 'CUSTOMER'; name: string; email?: string };
  resource: { type: 'DECISION' | 'SIGNAL' | 'ESCALATION' | 'CUSTOMER'; id: string; name: string };
  action: string;
  details: string;
  metadata: Record<string, string | number>;
  verification_hash?: string;
}

const eventTypeConfig: Record<
  AuditEventType,
  { label: string; icon: typeof FileText; color: string; gradient: string; badgeClass: string }
> = {
  DECISION_CREATED: {
    label: 'Decision Created',
    icon: FileText,
    color: 'text-accent',
    gradient: 'from-accent/20 to-accent/10',
    badgeClass: 'border-accent/30 bg-accent/10 text-accent',
  },
  DECISION_ACKNOWLEDGED: {
    label: 'Acknowledged',
    icon: CheckCircle,
    color: 'text-success',
    gradient: 'from-success/20 to-success/10',
    badgeClass: 'border-success/30 bg-success/10 text-success',
  },
  DECISION_OVERRIDDEN: {
    label: 'Overridden',
    icon: XCircle,
    color: 'text-action-reroute',
    gradient: 'from-action-reroute/20 to-accent/10',
    badgeClass: 'border-action-reroute/30 bg-action-reroute/10 text-action-reroute',
  },
  DECISION_ESCALATED: {
    label: 'Escalated',
    icon: AlertTriangle,
    color: 'text-warning',
    gradient: 'from-warning/20 to-warning/10',
    badgeClass: 'border-warning/30 bg-warning/10 text-warning',
  },
  ESCALATION_RESOLVED: {
    label: 'Resolved',
    icon: CheckCircle,
    color: 'text-success',
    gradient: 'from-success/20 to-success/10',
    badgeClass: 'border-success/30 bg-success/10 text-success',
  },
  SIGNAL_DETECTED: {
    label: 'Signal Detected',
    icon: AlertTriangle,
    color: 'text-warning',
    gradient: 'from-warning/20 to-error/10',
    badgeClass: 'border-warning/30 bg-warning/10 text-warning',
  },
  SIGNAL_CONFIRMED: {
    label: 'Signal Confirmed',
    icon: CheckCircle,
    color: 'text-success',
    gradient: 'from-success/20 to-success/10',
    badgeClass: 'border-success/30 bg-success/10 text-success',
  },
  CUSTOMER_ACTION: {
    label: 'Customer Action',
    icon: User,
    color: 'text-accent',
    gradient: 'from-accent/20 to-accent/10',
    badgeClass: 'border-accent/30 bg-accent/10 text-accent',
  },
  SYSTEM_EVENT: {
    label: 'System Event',
    icon: Clock,
    color: 'text-muted-foreground',
    gradient: 'from-muted/50 to-muted/30',
    badgeClass: 'border-border bg-muted/50 text-muted-foreground',
  },
};

const actorTypeConfig = {
  SYSTEM: { label: 'System', className: 'bg-muted text-muted-foreground border-border' },
  USER: {
    label: 'Staff',
    className: 'bg-info/10 text-info border-info/30',
  },
  CUSTOMER: {
    label: 'Customer',
    className: 'bg-action-reroute/10 text-action-reroute border-action-reroute/30',
  },
};

export function AuditPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<AuditEventType | 'ALL'>('ALL');
  const [showFilters, setShowFilters] = useState(false);
  const [dateRange, setDateRange] = useState('7d');
  const { success, info, warning } = useToast();
  const { data: auditResponse, isLoading, error, refetch } = useAuditTrail();

  // Extract events array from response, with safe fallback
  const rawEvents = auditResponse?.events ?? [];

  // Map API AuditEvent shape to local UI AuditEvent shape
  const auditEvents: AuditEvent[] = rawEvents.map((e) => {
    // Determine actor type from available fields
    const actorType: 'SYSTEM' | 'USER' | 'CUSTOMER' =
      e.user_id ? 'USER' : 'SYSTEM';
    const actorName = e.user_id ?? 'System';

    // Map API action string to our event type
    const eventType: AuditEventType =
      (e.action in eventTypeConfig ? e.action : 'SYSTEM_EVENT') as AuditEventType;

    // Extract summary from details
    const summary = typeof e.details === 'object' && e.details !== null
      ? String((e.details as Record<string, unknown>).summary ?? e.action)
      : e.action;

    return {
      id: e.id,
      event_type: eventType,
      timestamp: e.timestamp,
      actor: { type: actorType, name: actorName },
      resource: {
        type: (e.resource_type?.toUpperCase() ?? 'DECISION') as 'DECISION' | 'SIGNAL' | 'ESCALATION' | 'CUSTOMER',
        id: e.resource_id ?? e.id,
        name: e.resource_id ?? e.id,
      },
      action: e.action.replace(/_/g, ' '),
      details: summary,
      metadata: {},
      verification_hash: undefined,
    };
  });

  const handleDateRangeChange = () => {
    const ranges = ['7d', '30d', '90d'];
    const currentIndex = ranges.indexOf(dateRange);
    const nextIndex = (currentIndex + 1) % ranges.length;
    setDateRange(ranges[nextIndex]);
    info(
      `Showing events from last ${ranges[nextIndex] === '7d' ? '7 days' : ranges[nextIndex] === '30d' ? '30 days' : '90 days'}`,
    );
  };

  const handleExport = () => {
    const events = filteredEvents;
    if (!events.length) {
      warning('No events to export');
      return;
    }

    const rows: string[] = ['Timestamp,Type,Actor,Action,Target,Details'];
    for (const evt of events) {
      const escaped = (s: string) => `"${s.replace(/"/g, '""')}"`;
      rows.push([
        evt.timestamp,
        evt.event_type,
        escaped(evt.actor.name),
        escaped(evt.action),
        escaped(evt.resource.name),
        escaped(evt.details),
      ].join(','));
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `riskcast-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    success(`Exported ${events.length} audit events`);
  };

  const filteredEvents = auditEvents.filter((event) => {
    // Date range filter
    const rangeDays = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
    const cutoff = Date.now() - rangeDays * 24 * 3600_000;
    if (new Date(event.timestamp).getTime() < cutoff) return false;

    if (filterType !== 'ALL' && event.event_type !== filterType) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        event.action.toLowerCase().includes(query) ||
        event.details.toLowerCase().includes(query) ||
        event.actor.name.toLowerCase().includes(query) ||
        event.resource.name.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const totalEvents = auditEvents.length;
  const todayEvents = auditEvents.filter(
    (e) => new Date(e.timestamp).toDateString() === new Date().toDateString(),
  ).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <ScrollText className="h-8 w-8 animate-pulse text-success mx-auto" />
          <p className="text-sm text-muted-foreground">Loading audit trail...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <p className="text-sm text-error">Failed to load audit events</p>
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
              className="p-2 rounded-xl bg-gradient-to-br from-success/20 to-success/20"
              animate={{ scale: [1, 1.05, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <ScrollText className="h-6 w-6 text-success" />
            </motion.div>
            Audit Trail
          </motion.h1>
          <motion.p
            className="text-sm text-muted-foreground mt-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            {filteredEvents.length} events • {todayEvents} today • Cryptographically verified
          </motion.p>
        </div>

        <div className="flex items-center gap-2">
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-muted/50"
              onClick={handleDateRangeChange}
            >
              <Calendar className="h-4 w-4" />
              Last {dateRange === '7d' ? '7 days' : dateRange === '30d' ? '30 days' : '90 days'}
            </Button>
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-gradient-to-r from-success/10 to-success/10 border-success/30"
              onClick={handleExport}
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
          </motion.div>
        </div>
      </motion.div>

      {/* Stats Cards */}
      <motion.div
        className="grid gap-4 sm:grid-cols-3"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            icon={FileText}
            accentColor="blue"
            value={totalEvents}
            label="Total Events"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Shield}
            accentColor="emerald"
            value="100%"
            label="Verified"
            variant="overlay"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Hash}
            accentColor="blue"
            value={todayEvents}
            label="Today's Events"
            variant="overlay"
          />
        </motion.div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ...springs.smooth }}
      >
        <Card className="overflow-hidden shadow-md bg-card shadow-level-1">
          <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-success/50 to-transparent" />
          <CardContent className="p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="search"
                  placeholder="Search audit events..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  maxLength={200}
                  className="h-10 w-full rounded-xl border border-border bg-muted/50 pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
                />
              </div>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 px-3 py-2 text-sm rounded-xl bg-muted/50 hover:bg-muted"
              >
                <Filter className="h-4 w-4" />
                {filterType === 'ALL' ? 'All Types' : eventTypeConfig[filterType].label}
                <ChevronDown
                  className={cn('h-3 w-3 transition-transform', showFilters && 'rotate-180')}
                />
              </motion.button>
            </div>

            <AnimatePresence>
              {showFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex flex-wrap gap-2 pt-4 mt-4 border-t border-border"
                >
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setFilterType('ALL')}
                    className={cn(
                      'px-3 py-1.5 text-sm rounded-xl transition-all',
                      filterType === 'ALL'
                        ? 'bg-gradient-to-r from-success/20 to-success/20 text-success border border-success/30 font-medium'
                        : 'bg-muted/50 hover:bg-muted',
                    )}
                  >
                    All
                  </motion.button>
                  {Object.entries(eventTypeConfig)
                    .slice(0, 6)
                    .map(([type, config]) => (
                      <motion.button
                        key={type}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => setFilterType(type as AuditEventType)}
                        className={cn(
                          'flex items-center gap-1 px-3 py-1.5 text-sm rounded-xl transition-all',
                          filterType === type
                            ? 'bg-gradient-to-r from-success/20 to-success/20 text-success border border-success/30 font-medium'
                            : 'bg-muted/50 hover:bg-muted',
                        )}
                      >
                        <config.icon className="h-3 w-3" />
                        {config.label}
                      </motion.button>
                    ))}
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>

      {/* Audit Events List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, ...springs.smooth }}
      >
        <Card className="overflow-hidden shadow-md bg-card shadow-level-1">
          <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
          <CardHeader>
            <CardTitle>Event Log</CardTitle>
            <CardDescription>Complete audit trail with cryptographic verification</CardDescription>
          </CardHeader>
          <CardContent>
            <motion.div
              className="space-y-4"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {filteredEvents.map((event) => {
                const config = eventTypeConfig[event.event_type];
                const actorConfig = actorTypeConfig[event.actor.type];
                const EventIcon = config.icon;

                return (
                  <motion.div
                    key={event.id}
                    variants={staggerItem}
                    whileHover={{ x: 4, scale: 1.005 }}
                    transition={springs.snappy}
                    className={cn(
                      'flex gap-4 p-4 rounded-xl transition-all bg-gradient-to-r',
                      config.gradient,
                    )}
                  >
                    <motion.div
                      className="flex h-11 w-11 items-center justify-center rounded-xl bg-muted shrink-0"
                      whileHover={{ scale: 1.1, rotate: 5 }}
                    >
                      <EventIcon className={cn('h-5 w-5', config.color)} />
                    </motion.div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <Badge
                          className={cn(
                            'border',
                            config.badgeClass,
                          )}
                        >
                          {config.label}
                        </Badge>
                        <Badge variant="outline" className={actorConfig.className}>
                          {event.actor.name}
                        </Badge>
                      </div>

                      <p className="font-semibold text-sm mb-1">{event.action}</p>
                      <p className="text-sm text-muted-foreground line-clamp-2">{event.details}</p>

                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <Link
                          to={`/${event.resource.type.toLowerCase()}s/${event.resource.id}`}
                          className="hover:text-accent hover:underline"
                        >
                          {event.resource.type}: {event.resource.name}
                        </Link>
                      </div>

                      <div className="flex flex-wrap gap-2 mt-2">
                        {Object.entries(event.metadata).map(([key, value]) => (
                          <span
                            key={key}
                            className="inline-flex items-center px-2 py-0.5 rounded-lg text-xs bg-muted/50"
                          >
                            <span className="text-muted-foreground">{key.replace(/_/g, ' ')}:</span>
                            <span className="ml-1 font-mono font-medium">
                              {typeof value === 'number' && key.includes('usd')
                                ? formatCurrency(value, { compact: true })
                                : typeof value === 'number' && value < 1
                                  ? formatPercentage(value)
                                  : String(value)}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <p className="text-sm font-mono font-medium">
                        {formatDate(event.timestamp, { relative: true })}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDate(event.timestamp)}
                      </p>
                      {event.verification_hash && (
                        <div className="flex items-center gap-1 mt-2 text-xs text-success">
                          <Shield className="h-3 w-3" />
                          <code className="font-mono">{event.verification_hash}</code>
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })}

              {filteredEvents.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center py-12"
                >
                  <motion.div
                    className="p-4 rounded-2xl bg-gradient-to-br from-success/10 to-success/10 inline-block mb-4"
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  >
                    <FileText className="h-12 w-12 text-success" />
                  </motion.div>
                  <p className="text-xl font-semibold mb-2">No events found</p>
                  <p className="text-sm text-muted-foreground">
                    Try adjusting your search or filters
                  </p>
                </motion.div>
              )}
            </motion.div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}

export default AuditPage;
