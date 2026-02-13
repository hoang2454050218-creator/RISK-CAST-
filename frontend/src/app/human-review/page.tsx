/**
 * Human Review Page - AI Risk Terminal Style
 * Style: Data-dense, Dark Terminal, Analytical, High-trust
 * Consistent with system-wide terminal aesthetic
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { SkeletonHumanReview } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import { useTheme } from '@/components/ui/theme-provider';
import { StatCard } from '@/components/domain/common/StatCard';
import { FilterDropdown } from '@/components/ui/filter-dropdown';
import { EscalationCard } from '@/components/domain/escalations';
import type {
  Escalation,
  EscalationPriority,
  EscalationStatus,
} from '@/components/domain/escalations';
import { useEscalationsList } from '@/hooks';
import {
  Clock,
  CheckCircle,
  RefreshCw,
  Shield,
  Activity,
  Radio,
  Eye,
  Target,
  DollarSign,
  Flame,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import { springs, staggerContainer, staggerItem } from '@/lib/animations';

export function HumanReviewPage() {
  const [filterPriority, setFilterPriority] = useState<EscalationPriority | 'ALL'>('ALL');
  const [filterStatus, setFilterStatus] = useState<EscalationStatus | 'ALL'>('ALL');
  const { success } = useToast();
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  // ─── React Query ──────────────────────────────────────
  const { data: escalations, isLoading, error, refetch, isRefetching } = useEscalationsList();

  const handleRefresh = () => {
    refetch();
    success('Escalations refreshed');
  };

  const allEscalations = (escalations ?? []) as Escalation[];

  const filteredEscalations = allEscalations
    .filter((e) => {
      if (filterPriority !== 'ALL' && e.priority !== filterPriority) return false;
      if (filterStatus !== 'ALL' && e.status !== filterStatus) return false;
      return true;
    })
    .sort((a, b) => {
      const priorityOrder = { CRITICAL: 0, HIGH: 1, NORMAL: 2 };
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return new Date(a.sla_deadline).getTime() - new Date(b.sla_deadline).getTime();
    });

  const criticalCount = allEscalations.filter(
    (e) => e.priority === 'CRITICAL' && e.status !== 'RESOLVED',
  ).length;
  const pendingCount = allEscalations.filter((e) => e.status === 'PENDING').length;
  const inReviewCount = allEscalations.filter((e) => e.status === 'IN_REVIEW').length;
  const totalExposure = allEscalations
    .filter((e) => e.status !== 'RESOLVED')
    .reduce((sum, e) => sum + e.exposure_usd, 0);

  const avgSlaHours = useMemo(() => {
    const active = allEscalations.filter((e) => e.status !== 'RESOLVED');
    if (active.length === 0) return 0;
    const totalHours = active.reduce((sum, e) => {
      const remaining = (new Date(e.sla_deadline).getTime() - Date.now()) / (1000 * 60 * 60);
      return sum + Math.max(0, remaining);
    }, 0);
    return Math.round(totalHours / active.length);
  }, [allEscalations]);

  // ─── Loading state ────────────────────────────────────
  if (isLoading) {
    return <SkeletonHumanReview />;
  }

  // ─── Error state ──────────────────────────────────────
  if (error) {
    return (
      <div className="rounded-xl bg-card border border-border p-12 shadow-sm">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="p-3 rounded-lg bg-error/10 border border-error/20 mb-4">
            <AlertTriangle className="h-8 w-8 text-error" />
          </div>
          <p className="text-base font-semibold text-foreground mb-1">Failed to load escalations</p>
          <p className="text-xs text-muted-foreground font-mono mb-4">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
          <Button onClick={() => refetch()} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* ═══ System Status Bar ═══ */}
      <motion.div
        className={cn(
          'flex items-center justify-between px-4 py-2 rounded-lg border text-[10px] font-mono uppercase tracking-wider',
          'bg-card border-border shadow-sm',
        )}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <motion.div
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                criticalCount > 0 ? 'bg-error' : 'bg-success',
              )}
              animate={criticalCount > 0 ? { opacity: [1, 0.4, 1] } : {}}
              transition={{ duration: 1, repeat: Infinity }}
            />
            <span className="text-muted-foreground">
              Review Queue:{' '}
              <span
                className={cn(
                  'font-semibold',
                  criticalCount > 0 ? 'text-error' : 'text-success',
                )}
              >
                {criticalCount > 0 ? 'ALERT' : 'CLEAR'}
              </span>
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-muted-foreground">
            <Activity className="h-3 w-3" />
            <span>
              Queue: <span className="text-foreground">{filteredEscalations.length}</span>
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 text-muted-foreground">
            <DollarSign className="h-3 w-3" />
            <span>
              Exposure: <span className="text-foreground">{formatCurrency(totalExposure)}</span>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Radio className="h-3 w-3" />
          <span>
            Avg SLA: <span className="text-foreground">{avgSlaHours}h</span>
          </span>
        </div>
      </motion.div>

      {/* ═══ Page Header ═══ */}
      <motion.div
        className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
      >
        <div>
          <motion.h1
            className="text-2xl font-bold text-foreground flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <motion.div
              className={cn(
                'p-2.5 rounded-xl border',
                'bg-gradient-to-br from-error/10 to-warning/10',
                'border-error/20',
              )}
              animate={criticalCount > 0 ? { scale: [1, 1.05, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Shield className="h-5 w-5 text-error" />
            </motion.div>
            Human Review
          </motion.h1>
          <motion.p
            className="text-xs text-muted-foreground font-mono mt-1.5 flex items-center gap-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span>{filteredEscalations.length} ESCALATIONS</span>
            <span className="text-border">•</span>
            <span
              className={cn(criticalCount > 0 && 'text-error font-semibold')}
            >
              {criticalCount} CRITICAL
            </span>
            <span className="text-border">•</span>
            <span>{pendingCount} PENDING</span>
          </motion.p>
        </div>

        <motion.div
          className="flex items-center gap-2"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
        >
          <Button
            variant="outline"
            size="sm"
            className={cn(
              'gap-2 h-8 border-border',
              'bg-card hover:bg-muted text-muted-foreground hover:text-foreground',
            )}
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isRefetching && 'animate-spin')} />
            <span className="text-[10px] font-mono tracking-wider">
              {isRefetching ? 'REFRESHING...' : 'REFRESH'}
            </span>
          </Button>
        </motion.div>
      </motion.div>

      {/* ═══ Stats Dashboard ═══ */}
      <motion.div
        className="grid gap-3 grid-cols-2 lg:grid-cols-4"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Flame}
            value={criticalCount}
            label="Critical"
            sublabel="< 2h SLA"
            accentColor="red"
            urgent
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Clock}
            value={pendingCount}
            label="Pending"
            sublabel="Awaiting"
            accentColor="amber"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={Eye}
            value={inReviewCount}
            label="In Review"
            sublabel="Active"
            accentColor="blue"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <StatCard
            icon={DollarSign}
            value={totalExposure}
            label="Total Exposure"
            sublabel="Active"
            accentColor="accent"
            isCurrency
          />
        </motion.div>
      </motion.div>

      {/* ═══ Filter Bar ═══ */}
      <motion.div
        className={cn(
          'flex flex-col sm:flex-row sm:items-center gap-3 p-3 rounded-lg border',
          'bg-card border-border shadow-sm',
        )}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <FilterDropdown
          label="Priority"
          value={filterPriority}
          options={[
            { value: 'ALL', label: 'All' },
            { value: 'CRITICAL', label: 'Critical' },
            { value: 'HIGH', label: 'High' },
            { value: 'NORMAL', label: 'Normal' },
          ]}
          onChange={(v) => setFilterPriority(v as EscalationPriority | 'ALL')}
          accentColor="red"
        />

        <div className="hidden sm:block w-px h-6 bg-border mx-1" />

        <FilterDropdown
          label="Status"
          value={filterStatus}
          options={[
            { value: 'ALL', label: 'All' },
            { value: 'PENDING', label: 'Pending' },
            { value: 'IN_REVIEW', label: 'In Review' },
            { value: 'RESOLVED', label: 'Resolved' },
          ]}
          onChange={(v) => setFilterStatus(v as EscalationStatus | 'ALL')}
          accentColor="amber"
        />
      </motion.div>

      {/* ═══ Escalation Queue ═══ */}
      <div className="space-y-2.5">
        {/* Queue Header */}
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground uppercase tracking-wider">
            <Target className="h-3.5 w-3.5" />
            <span>Escalation Queue</span>
            <span className="text-border">|</span>
            <span className="text-foreground font-semibold">{filteredEscalations.length} items</span>
          </div>
          <div className="text-xs font-mono text-muted-foreground">
            Sorted by priority + SLA
          </div>
        </div>

        <motion.div
          className="space-y-2.5"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          <AnimatePresence>
            {filteredEscalations.map((escalation, index) => (
              <motion.div key={escalation.id} variants={staggerItem} layout>
                <EscalationCard escalation={escalation} index={index} isDark={isDark} />
              </motion.div>
            ))}
          </AnimatePresence>

          {filteredEscalations.length === 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={springs.smooth}
              className={cn(
                'relative overflow-hidden rounded-xl border p-16 text-center',
                'bg-card border-border shadow-sm',
              )}
            >
              {isDark && (
                <>
                  <div className="absolute top-0 left-0 w-3 h-3 border-l-2 border-t-2 border-success/30" />
                  <div className="absolute top-0 right-0 w-3 h-3 border-r-2 border-t-2 border-success/30" />
                  <div className="absolute bottom-0 left-0 w-3 h-3 border-l-2 border-b-2 border-success/30" />
                  <div className="absolute bottom-0 right-0 w-3 h-3 border-r-2 border-b-2 border-success/30" />
                </>
              )}
              <motion.div
                className="inline-flex p-5 rounded-2xl bg-success/10 border border-success/20 mb-5"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                <CheckCircle className="h-10 w-10 text-success" />
              </motion.div>
              <p className="text-lg font-bold text-foreground mb-1">Queue Clear</p>
              <p className="text-sm text-muted-foreground">
                No escalations matching current filters
              </p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </motion.div>
  );
}

export default HumanReviewPage;
