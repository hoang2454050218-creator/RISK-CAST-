/**
 * Decisions Page - Enterprise Data Terminal Style
 * Style: Data-dense, Dark, Analytical, High-trust
 *
 * Data flow: useDecisionsList() → React Query → API → mock fallback
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { FilterDropdown } from '@/components/ui/filter-dropdown';
import { ActiveFilterChip } from '@/components/ui/active-filter-chip';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { SkeletonDecisionsList } from '@/components/ui/skeleton';
import { Pagination } from '@/components/ui/pagination';
import { DecisionCard } from '@/components/domain/decisions/DecisionCard';
import { useDecisionsList, useAcknowledgeDecision, usePagination } from '@/hooks';
import {
  Search,
  LayoutGrid,
  List,
  RefreshCw,
  Bookmark,
  BookmarkCheck,
  Check,
  ChevronDown,
  AlertTriangle,
  Brain,
  Zap,
  Clock,
  Eye,
  Download,
  TrendingDown,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/formatters';
import { useToast } from '@/components/ui/toast';
import { staggerContainer, staggerItem, pageTransition, springs } from '@/lib/animations';
import type { Decision, DecisionStatus, Urgency, Severity } from '@/types/decision';

type ViewMode = 'grid' | 'list';
type SortBy = 'urgency' | 'exposure' | 'deadline' | 'created';

interface SavedView {
  id: string;
  name: string;
  filters: {
    status: DecisionStatus | 'ALL';
    urgency: Urgency | 'ALL';
    severity: Severity | 'ALL';
    sortBy: SortBy;
  };
}

const DEFAULT_VIEWS: SavedView[] = [
  {
    id: 'urgent-pending',
    name: 'Urgent Pending',
    filters: { status: 'PENDING', urgency: 'IMMEDIATE', severity: 'ALL', sortBy: 'urgency' },
  },
  {
    id: 'high-exposure',
    name: 'High Exposure',
    filters: { status: 'ALL', urgency: 'ALL', severity: 'CRITICAL', sortBy: 'exposure' },
  },
  {
    id: 'recent',
    name: 'Recently Created',
    filters: { status: 'ALL', urgency: 'ALL', severity: 'ALL', sortBy: 'created' },
  },
];

const VIEWS_STORAGE_KEY = 'riskcast:saved-views:decisions';
const MAX_VIEWS = 5;

function loadPersistedViews(): SavedView[] {
  try {
    const raw = localStorage.getItem(VIEWS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as SavedView[];
      const defaultIds = new Set(DEFAULT_VIEWS.map((d) => d.id));
      const userViews = parsed.filter((v) => !defaultIds.has(v.id));
      return [...DEFAULT_VIEWS, ...userViews.slice(0, MAX_VIEWS)];
    }
  } catch { /* ignore */ }
  return DEFAULT_VIEWS;
}

function persistViews(views: SavedView[]) {
  try {
    localStorage.setItem(VIEWS_STORAGE_KEY, JSON.stringify(views));
  } catch { /* ignore */ }
}

export function DecisionsPage() {
  const { success, info, error: showError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  // ─── React Query + Pagination ──────────────────────────
  const {
    data: decisions,
    isLoading: isQueryLoading,
    error: queryError,
    refetch,
    isRefetching,
  } = useDecisionsList();
  const acknowledgeMutation = useAcknowledgeDecision();
  const pagination = usePagination({ defaultPageSize: 20 });

  // ─── Local UI state ───────────────────────────────────
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [sortBy, setSortBy] = useState<SortBy>('urgency');
  const [filterStatus, setFilterStatus] = useState<DecisionStatus | 'ALL'>('ALL');
  const [filterUrgency, setFilterUrgency] = useState<Urgency | 'ALL'>('ALL');
  const [filterSeverity, setFilterSeverity] = useState<Severity | 'ALL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCustomer, setFilterCustomer] = useState<string | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[]>(loadPersistedViews);
  const [activeViewId, setActiveViewId] = useState<string | null>(null);
  const [showSavedViewsPanel, setShowSavedViewsPanel] = useState(false);
  const [confirmDecisionId, setConfirmDecisionId] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const navigate = useNavigate();

  // Sync URL params to filter state on mount
  useEffect(() => {
    const urgency = searchParams.get('urgency');
    if (urgency) setFilterUrgency(urgency as Urgency);
    const status = searchParams.get('status');
    if (status) setFilterStatus(status as DecisionStatus);
    const severity = searchParams.get('severity');
    if (severity) setFilterSeverity(severity as Severity);
    const customer = searchParams.get('customer');
    if (customer) setFilterCustomer(customer);
    const q = searchParams.get('q');
    if (q) setSearchQuery(q);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const hasActiveFilters =
    filterStatus !== 'ALL' ||
    filterUrgency !== 'ALL' ||
    filterSeverity !== 'ALL' ||
    filterCustomer !== null ||
    searchQuery !== '';

  // Expand mock decisions with additional synthetic entries for rich list
  const allDecisions = useMemo<Decision[]>(() => {
    if (!decisions?.length) return [];
    return [
      ...decisions,
      ...decisions.map((d, i) => ({
        ...d,
        decision_id: `dec_list_${i + 4}`,
        status: (['PENDING', 'ACKNOWLEDGED', 'OVERRIDDEN'] as const)[i % 3] as DecisionStatus,
        q2_when: {
          ...(d.q2_when ?? {}),
          urgency: (['IMMEDIATE', 'URGENT', 'SOON', 'WATCH'] as const)[i % 4] as Urgency,
        },
        q3_severity: {
          ...(d.q3_severity ?? {}),
          severity: (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const)[i % 4] as Severity,
          total_exposure_usd: 50000 + ((i * 47123) % 300000),
        },
        created_at: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
      })),
    ];
  }, [decisions]);

  // ─── Filter + Sort ────────────────────────────────────
  const filteredDecisions = useMemo(() => {
    return allDecisions
      .filter((d) => {
        if (filterStatus !== 'ALL' && d.status !== filterStatus) return false;
        if (filterUrgency !== 'ALL' && d.q2_when?.urgency !== filterUrgency) return false;
        if (filterSeverity !== 'ALL' && d.q3_severity?.severity !== filterSeverity) return false;
        if (filterCustomer) {
          const customerMatch =
            d.customer_id.toLowerCase().includes(filterCustomer.toLowerCase()) ||
            (d.q1_what?.event_summary ?? '').toLowerCase().includes(filterCustomer.toLowerCase());
          if (!customerMatch) return false;
        }
        if (searchQuery) {
          const q = searchQuery.toLowerCase();
          return (
            (d.q1_what?.event_summary ?? '').toLowerCase().includes(q) ||
            d.decision_id.toLowerCase().includes(q) ||
            d.customer_id.toLowerCase().includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => {
        switch (sortBy) {
          case 'urgency': {
            const order: Record<string, number> = { IMMEDIATE: 0, URGENT: 1, SOON: 2, WATCH: 3 };
            return (order[a.q2_when?.urgency ?? 'WATCH'] ?? 3) - (order[b.q2_when?.urgency ?? 'WATCH'] ?? 3);
          }
          case 'exposure':
            return (b.q3_severity?.total_exposure_usd ?? 0) - (a.q3_severity?.total_exposure_usd ?? 0);
          case 'deadline':
            return new Date(a.expires_at).getTime() - new Date(b.expires_at).getTime();
          case 'created':
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
          default:
            return 0;
        }
      });
  }, [allDecisions, filterStatus, filterUrgency, filterSeverity, filterCustomer, searchQuery, sortBy]);

  const pendingCount = allDecisions.filter((d) => d.status === 'PENDING').length;
  const immediateCount = allDecisions.filter((d) => d.q2_when?.urgency === 'IMMEDIATE').length;
  const urgentCount = allDecisions.filter((d) => d.q2_when?.urgency === 'URGENT').length;
  const totalExposure = allDecisions.reduce((sum, d) => sum + (d.q3_severity?.total_exposure_usd ?? 0), 0);
  const totalInactionCost = allDecisions
    .filter((d) => d.status === 'PENDING')
    .reduce((sum, d) => sum + (d.q7_inaction?.inaction_cost_usd ?? 0), 0);
  const totalPotentialSavings = allDecisions
    .filter((d) => d.status === 'PENDING')
    .reduce((sum, d) => {
      const exposure = d.q3_severity?.total_exposure_usd ?? 0;
      const cost = d.q5_action?.estimated_cost_usd ?? 0;
      return sum + Math.max(0, exposure - cost);
    }, 0);

  // Paginate the filtered/sorted results
  const {
    items: paginatedDecisions,
    totalPages,
    totalItems,
  } = pagination.paginate(filteredDecisions);

  // ─── Keyboard shortcuts (j/k/Enter/a/e) ───────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return;

      const items = paginatedDecisions;
      if (!items.length) return;

      switch (e.key) {
        case 'j': // Next item
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, items.length - 1));
          break;
        case 'k': // Previous item
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter': // Open selected
          if (selectedIndex >= 0 && selectedIndex < items.length) {
            e.preventDefault();
            navigate(`/decisions/${items[selectedIndex].decision_id}`);
          }
          break;
        case 'a': // Acknowledge selected
          if (selectedIndex >= 0 && selectedIndex < items.length) {
            e.preventDefault();
            const d = items[selectedIndex];
            if (d.status === 'PENDING') {
              setConfirmDecisionId(d.decision_id);
            }
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [paginatedDecisions, selectedIndex, navigate]);

  // Sync filters to URL params
  useEffect(() => {
    setSearchParams(
      (prev) => {
        const syncParam = (key: string, val: string | null, defaultVal?: string) => {
          if (val && val !== defaultVal && val !== 'ALL') prev.set(key, val);
          else prev.delete(key);
        };
        syncParam('status', filterStatus, 'ALL');
        syncParam('urgency', filterUrgency, 'ALL');
        syncParam('severity', filterSeverity, 'ALL');
        syncParam('sort', sortBy, 'urgency');
        syncParam('customer', filterCustomer);
        if (searchQuery) prev.set('q', searchQuery);
        else prev.delete('q');
        return prev;
      },
      { replace: true },
    );
  }, [filterStatus, filterUrgency, filterSeverity, sortBy, filterCustomer, searchQuery, setSearchParams]);

  // Reset selection when page/filters change
  useEffect(() => {
    setSelectedIndex(-1);
  }, [filterStatus, filterUrgency, filterSeverity, searchQuery, pagination.page]);

  // ─── Callbacks ────────────────────────────────────────
  const clearAllFilters = useCallback(() => {
    setFilterStatus('ALL');
    setFilterUrgency('ALL');
    setFilterSeverity('ALL');
    setSearchQuery('');
    setActiveViewId(null);
    info('Filters cleared');
  }, [info]);

  const applyView = useCallback(
    (view: SavedView) => {
      setFilterStatus(view.filters.status);
      setFilterUrgency(view.filters.urgency);
      setFilterSeverity(view.filters.severity);
      setSortBy(view.filters.sortBy);
      setActiveViewId(view.id);
      setShowSavedViewsPanel(false);
      info(`Applied view: ${view.name}`);
    },
    [info],
  );

  const saveCurrentView = useCallback(() => {
    const viewName = prompt('Enter a name for this view:');
    if (!viewName) return;
    const newView: SavedView = {
      id: `custom-${Date.now()}`,
      name: viewName,
      filters: { status: filterStatus, urgency: filterUrgency, severity: filterSeverity, sortBy },
    };
    setSavedViews((prev) => {
      const updated = [...prev, newView].slice(0, DEFAULT_VIEWS.length + MAX_VIEWS);
      persistViews(updated);
      return updated;
    });
    setActiveViewId(newView.id);
    success(`View "${viewName}" saved`);
  }, [filterStatus, filterUrgency, filterSeverity, sortBy, success]);

  const handleRefresh = useCallback(() => {
    refetch();
    success('Decisions refreshed');
  }, [refetch, success]);

  // ─── Acknowledge with confirmation + mutation ─────────
  const handleAcknowledgeRequest = useCallback((decisionId: string) => {
    setConfirmDecisionId(decisionId);
  }, []);

  const handleConfirmAcknowledge = useCallback(async () => {
    if (!confirmDecisionId) return;
    try {
      await acknowledgeMutation.mutateAsync({
        decision_id: confirmDecisionId,
        acknowledged_by: 'current_user',
      });
      success(`Decision acknowledged`);
    } catch {
      showError('Failed to acknowledge. Please retry.');
    }
    setConfirmDecisionId(null);
  }, [confirmDecisionId, acknowledgeMutation, success, showError]);

  const confirmingDecision = confirmDecisionId
    ? allDecisions.find((d) => d.decision_id === confirmDecisionId)
    : null;

  // ─── Loading state ────────────────────────────────────
  if (isQueryLoading) {
    return <SkeletonDecisionsList />;
  }

  // ─── Error state ──────────────────────────────────────
  if (queryError) {
    return (
      <div className="rounded-xl bg-card border border-border p-12 shadow-sm">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 mb-4">
            <AlertTriangle className="h-8 w-8 text-destructive" />
          </div>
          <p className="text-base font-semibold text-foreground mb-1">Failed to load decisions</p>
          <p className="text-xs text-muted-foreground font-mono mb-4">
            {queryError instanceof Error ? queryError.message : 'Unknown error'}
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
      className="relative space-y-5 pb-20"
      variants={pageTransition}
      initial="hidden"
      animate="visible"
    >
      {/* Gradient mesh background */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-60 overflow-hidden -z-10">
        <div className="absolute -top-20 -left-20 h-60 w-60 rounded-full bg-warning/[0.04] blur-3xl" />
        <div className="absolute -top-10 right-1/4 h-40 w-40 rounded-full bg-accent/[0.03] blur-3xl" />
      </div>

      {/* ── Page Header ──────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-3">
            <div className="p-2 rounded-xl bg-accent/10 border border-accent/20">
              <Brain className="h-5 w-5 text-accent" />
            </div>
            Decision Engine
          </h1>
          <p className="text-xs font-mono text-muted-foreground mt-1.5 flex items-center gap-2">
            <span>{filteredDecisions.length} decisions</span>
            <span className="text-border">|</span>
            <span className="text-muted-foreground/60">j/k navigate, Enter open, a acknowledge</span>
          </p>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Saved Views */}
          <div className="relative">
            <button
              onClick={() => setShowSavedViewsPanel(!showSavedViewsPanel)}
              className={cn(
                'flex items-center gap-2 h-9 px-3.5 text-xs font-mono rounded-xl border transition-all',
                activeViewId
                  ? 'bg-accent/10 text-accent border-accent/30'
                  : 'bg-card text-muted-foreground border-border hover:border-accent/20',
              )}
            >
              {activeViewId ? <BookmarkCheck className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
              <span>Views</span>
              <ChevronDown className="h-3 w-3" />
            </button>

            <AnimatePresence>
              {showSavedViewsPanel && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowSavedViewsPanel(false)} />
                  <motion.div
                    initial={{ opacity: 0, y: -5, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -5, scale: 0.98 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-border/60 bg-card shadow-xl overflow-hidden backdrop-blur-xl"
                  >
                    <div className="p-2.5 border-b border-border/60">
                      <p className="text-[10px] font-mono text-muted-foreground px-1 tracking-wider">SAVED VIEWS</p>
                    </div>
                    <div className="p-1">
                      {savedViews.map((view) => (
                        <button
                          key={view.id}
                          onClick={() => applyView(view)}
                          className={cn(
                            'flex w-full items-center gap-2 px-2.5 py-2 text-xs font-mono rounded-lg transition-colors',
                            activeViewId === view.id ? 'bg-accent/10 text-accent' : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                          )}
                        >
                          {activeViewId === view.id ? <Check className="h-3 w-3" /> : <Bookmark className="h-3 w-3 text-muted-foreground/40" />}
                          {view.name}
                        </button>
                      ))}
                    </div>
                    <div className="p-2 border-t border-border/60">
                      <Button variant="ghost" size="sm" className="w-full justify-start gap-2 text-xs font-mono text-muted-foreground hover:text-foreground" onClick={saveCurrentView}>
                        <BookmarkCheck className="h-3 w-3" />
                        Save Current View
                      </Button>
                    </div>
                  </motion.div>
                </>
              )}
            </AnimatePresence>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="h-9 gap-2 rounded-xl bg-card border-border hover:bg-muted hover:border-accent/20 text-foreground/80"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={cn('h-3.5 w-3.5', isRefetching && 'animate-spin')} />
            <span className="font-mono text-xs">{isRefetching ? 'SYNCING...' : 'REFRESH'}</span>
          </Button>
        </div>
      </div>

      {/* ── Urgency Summary Strip ────────────────────────────── */}
      <motion.div
        className="rounded-2xl border border-border/40 bg-card/60 backdrop-blur-sm shadow-level-1 p-1.5"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, ...springs.smooth }}
      >
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
          {[
            { label: 'IMMEDIATE', value: immediateCount, color: 'text-urgency-immediate', bg: immediateCount > 0 ? 'bg-urgency-immediate/[0.06]' : 'bg-muted/20', icon: Zap, glow: immediateCount > 0 ? 'rc-text-glow-red' : '', pulse: immediateCount > 0 },
            { label: 'URGENT', value: urgentCount, color: 'text-urgency-urgent', bg: urgentCount > 0 ? 'bg-urgency-urgent/[0.06]' : 'bg-muted/20', icon: AlertTriangle, glow: urgentCount > 0 ? 'rc-text-glow-amber' : '', pulse: false },
            { label: 'PENDING', value: pendingCount, color: 'text-info', bg: pendingCount > 0 ? 'bg-info/[0.06]' : 'bg-muted/20', icon: Clock, glow: '', pulse: false },
            { label: 'EXPOSURE', value: formatCurrency(totalExposure, { compact: true }), color: 'text-foreground', bg: 'bg-muted/20', icon: Eye, glow: '', pulse: false, isText: true },
            { label: 'CAN SAVE', value: formatCurrency(totalPotentialSavings, { compact: true }), color: 'text-success', bg: totalPotentialSavings > 0 ? 'bg-success/[0.04]' : 'bg-muted/20', icon: TrendingDown, glow: '', pulse: false, isText: true },
            { label: 'IF NOTHING', value: formatCurrency(totalInactionCost, { compact: true }), color: 'text-destructive/70', bg: totalInactionCost > 0 ? 'bg-destructive/[0.03]' : 'bg-muted/20', icon: ShieldAlert, glow: '', pulse: false, isText: true },
          ].map((stat) => (
            <div key={stat.label} className={cn('flex items-center gap-2.5 rounded-xl px-3.5 py-3 transition-colors', stat.bg)}>
              <stat.icon className={cn('h-5 w-5 shrink-0', stat.color)} />
              <div className="min-w-0">
                <p className={cn('text-2xl font-black font-mono tabular-nums leading-none tracking-tight', stat.color, stat.glow)}>
                  {stat.value}
                </p>
                <p className="text-[8px] font-mono text-muted-foreground/40 tracking-[0.15em] mt-1">{stat.label}</p>
              </div>
              {stat.pulse && (
                <span className="relative flex h-2.5 w-2.5 ml-auto shrink-0">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive/50" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-destructive" />
                </span>
              )}
            </div>
          ))}
        </div>
      </motion.div>

      {/* ── Filters Bar ──────────────────────────────────────── */}
      <div className="p-3 rounded-2xl bg-card border border-border/60 shadow-level-1">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="search"
                placeholder="Search decisions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                maxLength={200}
                className="h-9 w-full rounded-xl border border-border bg-muted/50 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/50 font-mono"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <FilterDropdown
                label="Status"
                value={filterStatus}
                options={[
                  { value: 'ALL', label: 'All Status' },
                  { value: 'PENDING', label: 'Pending' },
                  { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
                  { value: 'OVERRIDDEN', label: 'Overridden' },
                  { value: 'ESCALATED', label: 'Escalated' },
                ]}
                onChange={(v) => {
                  setFilterStatus(v as DecisionStatus | 'ALL');
                  setActiveViewId(null);
                }}
              />
              <FilterDropdown
                label="Urgency"
                value={filterUrgency}
                options={[
                  { value: 'ALL', label: 'All Urgency' },
                  { value: 'IMMEDIATE', label: 'Immediate' },
                  { value: 'URGENT', label: 'Urgent' },
                  { value: 'SOON', label: 'Soon' },
                  { value: 'WATCH', label: 'Watch' },
                ]}
                onChange={(v) => {
                  setFilterUrgency(v as Urgency | 'ALL');
                  setActiveViewId(null);
                }}
              />
              <FilterDropdown
                label="Severity"
                value={filterSeverity}
                options={[
                  { value: 'ALL', label: 'All Severity' },
                  { value: 'CRITICAL', label: 'Critical' },
                  { value: 'HIGH', label: 'High' },
                  { value: 'MEDIUM', label: 'Medium' },
                  { value: 'LOW', label: 'Low' },
                ]}
                onChange={(v) => {
                  setFilterSeverity(v as Severity | 'ALL');
                  setActiveViewId(null);
                }}
              />
              <FilterDropdown
                label="Sort"
                value={sortBy}
                options={[
                  { value: 'urgency', label: 'By Urgency' },
                  { value: 'exposure', label: 'By Exposure' },
                  { value: 'deadline', label: 'By Deadline' },
                  { value: 'created', label: 'By Created' },
                ]}
                onChange={(v) => setSortBy(v as SortBy)}
              />

              <div className="flex items-center rounded-lg border border-border bg-muted/50 p-0.5">
                <button
                  onClick={() => setViewMode('grid')}
                  className={cn(
                    'p-2.5 sm:p-1.5 rounded-md transition-all min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 inline-flex items-center justify-center',
                    viewMode === 'grid' ? 'bg-card text-accent shadow-sm' : 'text-muted-foreground hover:text-foreground',
                  )}
                  aria-label="Grid view"
                >
                  <LayoutGrid className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={cn(
                    'p-2.5 sm:p-1.5 rounded-md transition-all min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 inline-flex items-center justify-center',
                    viewMode === 'list' ? 'bg-card text-accent shadow-sm' : 'text-muted-foreground hover:text-foreground',
                  )}
                  aria-label="List view"
                >
                  <List className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          <AnimatePresence>
            {hasActiveFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap items-center gap-2 pt-2 border-t border-border"
              >
                <span className="text-[10px] font-mono text-muted-foreground">ACTIVE:</span>
                {filterStatus !== 'ALL' && (
                  <ActiveFilterChip label={filterStatus} onRemove={() => setFilterStatus('ALL')} />
                )}
                {filterUrgency !== 'ALL' && (
                  <ActiveFilterChip
                    label={filterUrgency}
                    onRemove={() => setFilterUrgency('ALL')}
                  />
                )}
                {filterSeverity !== 'ALL' && (
                  <ActiveFilterChip
                    label={filterSeverity}
                    onRemove={() => setFilterSeverity('ALL')}
                  />
                )}
                {filterCustomer && (
                  <ActiveFilterChip
                    label={`Customer: ${filterCustomer}`}
                    onRemove={() => {
                      setFilterCustomer(null);
                      setSearchParams((prev) => { prev.delete('customer'); return prev; });
                    }}
                  />
                )}
                {searchQuery && (
                  <ActiveFilterChip
                    label={`"${searchQuery}"`}
                    onRemove={() => setSearchQuery('')}
                  />
                )}
                <button
                  onClick={clearAllFilters}
                  className="text-[10px] text-muted-foreground hover:text-foreground px-2 py-1 rounded hover:bg-muted font-mono"
                >
                  CLEAR ALL
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Quick Filter Presets */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <span className="text-[10px] font-mono text-muted-foreground shrink-0 tracking-wider">QUICK FILTERS</span>
        {[
          { label: 'Immediate', action: () => { setFilterUrgency('IMMEDIATE'); setFilterStatus('PENDING'); }, color: 'hover:border-error/30 hover:text-error' },
          { label: 'Pending', action: () => { setFilterStatus('PENDING'); setFilterUrgency('ALL'); }, color: 'hover:border-accent/30 hover:text-accent' },
          { label: 'High Exposure', action: () => { clearAllFilters(); setSortBy('exposure'); }, color: 'hover:border-warning/30 hover:text-warning' },
          { label: 'All', action: () => clearAllFilters(), color: '' },
        ].map((preset) => (
          <button
            key={preset.label}
            onClick={preset.action}
            className={cn(
              'shrink-0 px-3 py-1.5 text-[11px] font-medium rounded-lg border border-border/60 bg-card hover:bg-muted transition-all text-muted-foreground',
              preset.color,
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Decision Grid/List */}
      <AnimatePresence mode="wait">
        {paginatedDecisions.length > 0 ? (
          <motion.div
            key="decisions-grid"
            className={cn(
              viewMode === 'grid' && 'grid gap-5 sm:grid-cols-2 xl:grid-cols-3 auto-rows-fr',
              viewMode === 'list' && 'space-y-2',
            )}
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {paginatedDecisions.map((decision, idx) => (
              <motion.div
                key={decision.decision_id}
                variants={staggerItem}
                className="h-full"
                onClick={() => setSelectedIndex(idx)}
              >
                <DecisionCard
                  decision={decision}
                  onAcknowledge={handleAcknowledgeRequest}
                  isLoading={
                    acknowledgeMutation.isPending && confirmDecisionId === decision.decision_id
                  }
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
            key="no-decisions"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="rounded-2xl bg-card border border-border/60 p-16 shadow-sm"
          >
            <div className="flex flex-col items-center justify-center text-center">
              <div className="relative mb-5">
                <div className="p-4 rounded-2xl bg-muted/50 border border-border/40">
                  <Brain className="h-8 w-8 text-muted-foreground/40" />
                </div>
                <motion.div
                  className="absolute inset-0 rounded-2xl border border-accent/20"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.3, 0, 0.3] }}
                  transition={{ duration: 2.5, repeat: Infinity }}
                />
              </div>
              <p className="text-base font-semibold text-foreground mb-1">No decisions found</p>
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

      {/* ── Floating Action Bar ────────────────────────────── */}
      {pendingCount > 0 && (
        <motion.div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, ...springs.bouncy }}
        >
          <div className="flex items-center gap-3 px-5 py-3 rounded-2xl border border-border/60 bg-card/90 backdrop-blur-xl shadow-xl">
            <span className="text-[11px] font-mono text-muted-foreground">
              {pendingCount} pending
            </span>
            <div className="w-px h-4 bg-border" />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground"
              onClick={() => { setFilterStatus('PENDING'); setFilterUrgency('ALL'); }}
            >
              <Eye className="h-3 w-3" />
              View Pending
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 text-xs font-mono text-muted-foreground hover:text-foreground"
              onClick={handleRefresh}
            >
              <Download className="h-3 w-3" />
              Export
            </Button>
          </div>
        </motion.div>
      )}

      {/* Acknowledge Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={confirmDecisionId !== null}
        onConfirm={handleConfirmAcknowledge}
        onCancel={() => setConfirmDecisionId(null)}
        title="Accept this recommendation?"
        description={
          confirmingDecision
            ? `Accept action for "${(confirmingDecision.q1_what?.event_summary ?? 'this decision').slice(0, 60)}..." with ${formatCurrency(confirmingDecision.q3_severity?.total_exposure_usd ?? 0)} exposure. This will be logged and committed.`
            : 'Accept the recommended action for this decision.'
        }
        confirmLabel="Accept & Commit"
        variant="default"
        isLoading={acknowledgeMutation.isPending}
      />
    </motion.div>
  );
}

export default DecisionsPage;
