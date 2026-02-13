/**
 * Signals Page - Premium Signal Intelligence Terminal
 * Style: Bloomberg data-density + Linear cleanness + subtle glow
 */

import { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { FilterDropdown } from '@/components/ui/filter-dropdown';
import { SkeletonSignalsList } from '@/components/ui/skeleton';
import { Pagination } from '@/components/ui/pagination';
import { useToast } from '@/components/ui/toast';
import { SignalCard } from '@/components/domain/signals';
import { useSignalsList, usePagination } from '@/hooks';
import {
  Search,
  LayoutGrid,
  List,
  RefreshCw,
  Radio,
  AlertTriangle,
  Zap,
  Shield,
  Activity,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { staggerContainer, staggerItem, pageTransition, springs } from '@/lib/animations';
import type { SignalStatus, EventType } from '@/types/signal';

type ViewMode = 'grid' | 'list';
type SortBy = 'probability' | 'confidence' | 'impact' | 'updated';

export function SignalsPage() {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortBy>('probability');
  const [filterStatus, setFilterStatus] = useState<SignalStatus | 'ALL'>('ALL');
  const [filterType, setFilterType] = useState<EventType | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const { success } = useToast();
  const navigate = useNavigate();

  const { data: signals, isLoading, error, refetch, isRefetching } = useSignalsList();
  const pagination = usePagination({ defaultPageSize: 20 });

  const handleRefresh = () => {
    refetch();
    success('Signals refreshed successfully');
  };

  const allSignals = signals ?? [];

  const filteredSignals = useMemo(() => {
    return allSignals
      .filter((s) => {
        if (filterStatus !== 'ALL' && s.status !== filterStatus) return false;
        if (filterType !== 'ALL' && s.event_type !== filterType) return false;
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          return (
            s.event_title.toLowerCase().includes(query) ||
            s.event_description.toLowerCase().includes(query) ||
            s.signal_id.toLowerCase().includes(query)
          );
        }
        return true;
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'probability': return b.probability - a.probability;
          case 'confidence': return b.confidence - a.confidence;
          case 'impact': return (b.estimated_impact_usd || 0) - (a.estimated_impact_usd || 0);
          case 'updated': return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
          default: return 0;
        }
      });
  }, [allSignals, filterStatus, filterType, searchQuery, sortBy]);

  const activeCount = allSignals.filter((s) => s.status === 'ACTIVE').length;
  const confirmedCount = allSignals.filter((s) => s.status === 'CONFIRMED').length;
  const criticalCount = allSignals.filter((s) => s.probability >= 80).length;

  const { items: paginatedSignals, totalPages, totalItems } = pagination.paginate(filteredSignals);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;
      if (!paginatedSignals.length) return;
      switch (e.key) {
        case 'j': e.preventDefault(); setSelectedIndex((i) => Math.min(i + 1, paginatedSignals.length - 1)); break;
        case 'k': e.preventDefault(); setSelectedIndex((i) => Math.max(i - 1, 0)); break;
        case 'Enter':
          if (selectedIndex >= 0 && selectedIndex < paginatedSignals.length) {
            e.preventDefault();
            navigate(`/signals/${paginatedSignals[selectedIndex].signal_id}`);
          }
          break;
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [paginatedSignals, selectedIndex, navigate]);

  useEffect(() => { setSelectedIndex(-1); }, [filterStatus, filterType, searchQuery, pagination.page]);

  if (isLoading) return <SkeletonSignalsList />;

  if (error) {
    return (
      <div className="rounded-2xl bg-card border border-border p-12 shadow-sm">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="p-3 rounded-xl bg-error/10 border border-error/20 mb-4">
            <AlertTriangle className="h-8 w-8 text-error" />
          </div>
          <p className="text-base font-semibold text-foreground mb-1">Failed to load signals</p>
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
    <motion.div className="relative space-y-5" variants={pageTransition} initial="hidden" animate="visible">
      {/* Gradient mesh */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-60 overflow-hidden -z-10">
        <div className="absolute -top-20 -right-20 h-60 w-60 rounded-full bg-accent/[0.04] blur-3xl" />
        <div className="absolute -top-10 left-1/4 h-40 w-40 rounded-full bg-warning/[0.03] blur-3xl" />
      </div>

      {/* ── Page Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent/10 border border-accent/20">
              <Radio className="h-5 w-5 text-accent" />
            </div>
            Signal Intelligence
          </h1>
          <p className="text-xs font-mono text-muted-foreground mt-1.5 flex items-center gap-2">
            <span>{filteredSignals.length} signals detected</span>
            <span className="text-border">|</span>
            <span className="text-muted-foreground/60">j/k to navigate, Enter to open</span>
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          className="h-9 gap-2 rounded-xl bg-card border-border hover:bg-muted hover:border-accent/20 text-foreground/80"
          onClick={handleRefresh}
          disabled={isRefetching}
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isRefetching && 'animate-spin')} />
          <span className="font-mono text-xs">{isRefetching ? 'SYNCING...' : 'SCAN'}</span>
        </Button>
      </div>

      {/* ── Live Stats Strip ─────────────────────────────────── */}
      <motion.div
        className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-sm p-1.5"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ...springs.smooth }}
      >
        <div className="grid grid-cols-4 gap-1.5">
          {[
            {
              label: 'TOTAL',
              value: allSignals.length,
              icon: Activity,
              color: 'text-foreground',
              iconColor: 'text-muted-foreground/60',
              bg: 'bg-muted/20',
              glow: '',
            },
            {
              label: 'ACTIVE',
              value: activeCount,
              icon: Zap,
              color: 'text-blue-400',
              iconColor: 'text-blue-400',
              bg: activeCount > 0 ? 'bg-blue-500/[0.06]' : 'bg-muted/20',
              glow: activeCount > 0 ? 'rc-text-glow-blue' : '',
            },
            {
              label: 'CRITICAL',
              value: criticalCount,
              icon: AlertTriangle,
              color: criticalCount > 0 ? 'text-red-400' : 'text-muted-foreground',
              iconColor: criticalCount > 0 ? 'text-red-400' : 'text-muted-foreground/60',
              bg: criticalCount > 0 ? 'bg-red-500/[0.06]' : 'bg-muted/20',
              glow: criticalCount > 0 ? 'rc-text-glow-red' : '',
              pulse: criticalCount > 0,
            },
            {
              label: 'CONFIRMED',
              value: confirmedCount,
              icon: Shield,
              color: 'text-emerald-400',
              iconColor: 'text-emerald-400',
              bg: confirmedCount > 0 ? 'bg-emerald-500/[0.06]' : 'bg-muted/20',
              glow: confirmedCount > 0 ? 'rc-text-glow-green' : '',
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className={cn(
                'flex items-center gap-3 rounded-xl px-4 py-3 transition-colors border border-transparent',
                stat.bg,
              )}
            >
              <stat.icon className={cn('h-5 w-5 shrink-0', stat.iconColor)} />
              <div className="min-w-0">
                <p className={cn('text-2xl font-black font-mono tabular-nums leading-none tracking-tight', stat.color, stat.glow)}>
                  {stat.value}
                </p>
                <p className="text-[8px] font-mono text-muted-foreground/40 tracking-[0.15em] mt-1">{stat.label}</p>
              </div>
              {'pulse' in stat && stat.pulse && (
                <span className="relative flex h-2.5 w-2.5 ml-auto shrink-0">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500/50" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                </span>
              )}
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Filters Bar ──────────────────────────────────────── */}
      <div className="p-3 rounded-2xl bg-card border border-border/60 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {/* Search */}
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              placeholder="Search signals..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 w-full rounded-xl border border-border bg-muted/50 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/50 font-mono"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <FilterDropdown
              label="Status"
              value={filterStatus}
              accentColor="amber"
              options={[
                { value: 'ALL', label: 'All Status' },
                { value: 'ACTIVE', label: 'Active' },
                { value: 'CONFIRMED', label: 'Confirmed' },
                { value: 'EXPIRED', label: 'Expired' },
              ]}
              onChange={(v) => setFilterStatus(v as SignalStatus | 'ALL')}
            />
            <FilterDropdown
              label="Type"
              value={filterType}
              accentColor="amber"
              options={[
                { value: 'ALL', label: 'All Types' },
                { value: 'ROUTE_DISRUPTION', label: 'Route Disruption' },
                { value: 'PORT_CONGESTION', label: 'Port Congestion' },
                { value: 'RATE_SPIKE', label: 'Rate Spike' },
                { value: 'GEOPOLITICAL', label: 'Geopolitical' },
              ]}
              onChange={(v) => setFilterType(v as EventType | 'ALL')}
            />
            <FilterDropdown
              label="Sort"
              value={sortBy}
              accentColor="amber"
              options={[
                { value: 'probability', label: 'By Probability' },
                { value: 'confidence', label: 'By Confidence' },
                { value: 'impact', label: 'By Impact' },
                { value: 'updated', label: 'By Updated' },
              ]}
              onChange={(v) => setSortBy(v as SortBy)}
            />

            {/* View Toggle */}
            <div className="flex items-center rounded-lg border border-border bg-muted/50 p-0.5">
              <button
                onClick={() => setViewMode('grid')}
                className={cn(
                  'p-1.5 rounded-md transition-all',
                  viewMode === 'grid' ? 'bg-card text-accent shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={cn(
                  'p-1.5 rounded-md transition-all',
                  viewMode === 'list' ? 'bg-card text-accent shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Signal Grid/List ─────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {paginatedSignals.length > 0 ? (
          <motion.div
            key="signals-grid"
            className={cn(
              viewMode === 'grid' && 'grid gap-5 sm:grid-cols-2 xl:grid-cols-3 auto-rows-fr',
              viewMode === 'list' && 'space-y-2',
            )}
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {paginatedSignals.map((signal, idx) => (
              <motion.div
                key={signal.signal_id}
                variants={staggerItem}
                className="h-full"
                onClick={() => setSelectedIndex(idx)}
              >
                <SignalCard
                  signal={signal}
                  variant={viewMode === 'list' ? 'compact' : 'default'}
                  className={cn(
                    'h-full',
                    selectedIndex === idx && 'ring-2 ring-accent ring-offset-1 ring-offset-background',
                  )}
                />
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <motion.div
            key="no-signals"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="rounded-2xl bg-card border border-border/60 p-16 shadow-sm"
          >
            <div className="flex flex-col items-center justify-center text-center">
              <div className="relative mb-5">
                <div className="p-4 rounded-2xl bg-muted/50 border border-border/40">
                  <Radio className="h-8 w-8 text-muted-foreground/40" />
                </div>
                <motion.div
                  className="absolute inset-0 rounded-2xl border border-accent/20"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 2.5, repeat: Infinity }}
                />
              </div>
              <p className="text-base font-semibold text-foreground mb-1">No signals found</p>
              <p className="text-xs text-muted-foreground font-mono">
                Try adjusting your filters or search query
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Pagination */}
      <Pagination
        currentPage={pagination.page}
        totalPages={totalPages}
        onPageChange={pagination.setPage}
        pageSize={pagination.pageSize}
        onPageSizeChange={pagination.setPageSize}
        totalItems={totalItems}
      />
    </motion.div>
  );
}

export default SignalsPage;
