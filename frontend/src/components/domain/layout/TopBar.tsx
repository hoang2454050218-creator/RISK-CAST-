import { useState, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  Search,
  User,
  Menu,
  ChevronDown,
  LogOut,
  Settings,
  HelpCircle,
  Command,
  Sun,
  Moon,
  Monitor,
  DollarSign,
  Clock,
  TrendingDown,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from '@/components/ui/toast';
import { useTheme } from '@/components/ui/theme-provider';
import { useUser } from '@/contexts/user-context';
import { useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';

import { formatCurrency } from '@/lib/formatters';
import { springs, dropdownVariants, staggerContainer, staggerItem } from '@/lib/animations';
import { useQueryClient } from '@tanstack/react-query';
import { useDecisionsList, useEscalationsList } from '@/hooks';
import type { Decision } from '@/types/decision';
import type { Escalation } from '@/components/domain/escalations';

// ---------------------------------------------------------------------------
// DataFreshness – shows how stale the decisions cache is
// ---------------------------------------------------------------------------
function DataFreshness() {
  const queryClient = useQueryClient();
  const [, setTick] = useState(0);

  // Re-render every 10 s so the "Xm ago" label stays current
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 10_000);
    return () => clearInterval(interval);
  }, []);

  // Check multiple query sources — use whichever was updated most recently
  const decisionsState = queryClient.getQueryState(['decisions', 'list']);
  const dashboardState = queryClient.getQueryState(['dashboard', 7]);
  const signalsState = queryClient.getQueryState(['signals', 'list']);

  const dataUpdatedAt = Math.max(
    decisionsState?.dataUpdatedAt ?? 0,
    dashboardState?.dataUpdatedAt ?? 0,
    signalsState?.dataUpdatedAt ?? 0,
  ) || undefined;

  // No data cached yet → "Syncing…" with blue pulsing dot
  if (!dataUpdatedAt) {
    return (
      <div className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
        </span>
        <span>Syncing…</span>
      </div>
    );
  }

  const ageMs = Date.now() - dataUpdatedAt;
  const ageMinutes = Math.floor(ageMs / 60_000);

  let dotColor: string;
  let pulse = false;
  let label: string;

  if (ageMs < 60_000) {
    // Fresh – green pulsing
    dotColor = 'bg-success';
    pulse = true;
    label = 'Fresh';
  } else if (ageMs < 300_000) {
    // Stale – yellow
    dotColor = 'bg-warning';
    label = `${ageMinutes}m ago`;
  } else {
    // Very stale – red
    dotColor = 'bg-destructive';
    label = `${ageMinutes}m ago`;
  }

  const isStale = ageMs >= 300_000;

  return (
    <div
      className={cn(
        'freshness-container',
        isStale && 'border-warning/30 bg-warning/5',
      )}
      title={`Last sync: ${new Date(dataUpdatedAt).toLocaleTimeString()}`}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
              dotColor,
            )}
          />
        )}
        <span className={cn('relative inline-flex h-2 w-2 rounded-full', dotColor)} />
      </span>
      <span className={cn(isStale && 'text-warning')}>{label}</span>
    </div>
  );
}

interface TopBarProps {
  onMenuClick?: () => void;
  onSearchClick?: () => void;
  showMenuButton?: boolean;
  className?: string;
}

export function TopBar({
  onMenuClick,
  onSearchClick,
  showMenuButton = false,
  className,
}: TopBarProps) {
  const { user } = useUser();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showThemeMenu, setShowThemeMenu] = useState(false);
  const { theme, resolvedTheme, setTheme } = useTheme();

  // Live notification data from decisions & escalations
  const { data: decisions = [] } = useDecisionsList();
  const { data: escalations = [] } = useEscalationsList();

  const pendingDecisions = useMemo(
    () => decisions.filter((d: Decision) => d.status === 'PENDING'),
    [decisions],
  );
  const pendingEscalations = useMemo(
    () => escalations.filter((e: Escalation) => e.status === 'PENDING'),
    [escalations],
  );
  const notificationCount = pendingDecisions.length + pendingEscalations.length;

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={springs.smooth}
      className={cn(
        'sticky top-0 z-30 flex h-14 items-center topbar-border',
        'topbar-glass border-b-0',
        className,
      )}
      role="banner"
    >
      {/* Left section - Menu button (mobile only — sidebar handles desktop nav) */}
      <div className="flex items-center gap-2 px-4 md:hidden">
        <AnimatePresence>
          {showMenuButton && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
            >
              <Button
                variant="ghost"
                size="icon"
                onClick={onMenuClick}
                aria-label="Open menu"
                className="text-muted-foreground hover:text-foreground hover:bg-muted"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Center section - Search */}
      <div className="flex-1 flex justify-center px-4">
        <motion.button
          onClick={onSearchClick}
          className={cn(
            'relative w-full max-w-md h-9 rounded-lg px-3 text-sm text-left',
            'search-command-trigger',
            'flex items-center gap-2 group',
          )}
          whileHover={{ scale: 1.005 }}
          whileTap={{ scale: 0.995 }}
          aria-label="Open command palette (Ctrl+K or Cmd+K)"
        >
          <Search className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
          <span className="text-muted-foreground flex-1 text-xs font-mono">
            Search decisions, signals, customers...
          </span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            <Command className="h-2.5 w-2.5" />
            <span>K</span>
          </kbd>
        </motion.button>
      </div>

      {/* Right section - Actions (pushed to far right) */}
      <div className="flex items-center gap-1.5 px-4" role="navigation" aria-label="Quick actions">
        {/* Data freshness indicator */}
        <div className="hidden sm:block mr-1">
          <DataFreshness />
        </div>

        {/* Separator */}
        <div className="hidden sm:block w-px h-5 bg-border mx-0.5" />

        {/* Theme toggle dropdown */}
        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowThemeMenu(!showThemeMenu)}
            aria-label="Change theme"
            aria-expanded={showThemeMenu}
            title={`Switch theme (currently ${resolvedTheme === 'dark' ? 'Control Room' : 'Field Mode'})`}
            className="h-9 w-9 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg"
          >
            <AnimatePresence mode="wait">
              {resolvedTheme === 'dark' ? (
                <motion.div
                  key="moon"
                  initial={{ rotate: -90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: 90, opacity: 0 }}
                  transition={springs.snappy}
                >
                  <Moon className="h-[18px] w-[18px]" />
                </motion.div>
              ) : (
                <motion.div
                  key="sun"
                  initial={{ rotate: 90, opacity: 0 }}
                  animate={{ rotate: 0, opacity: 1 }}
                  exit={{ rotate: -90, opacity: 0 }}
                  transition={springs.snappy}
                >
                  <Sun className="h-[18px] w-[18px]" />
                </motion.div>
              )}
            </AnimatePresence>
          </Button>

          {/* Theme Dropdown Menu */}
          <AnimatePresence>
            {showThemeMenu && (
              <motion.div
                variants={dropdownVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="absolute right-0 top-full mt-2 w-36 rounded-lg border border-border bg-card shadow-lg overflow-hidden z-50"
              >
                <div className="py-1">
                  <button
                    onClick={() => {
                      setTheme('light');
                      setShowThemeMenu(false);
                    }}
                    className={cn(
                      'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors',
                      'hover:bg-muted',
                      theme === 'light' && 'bg-muted text-accent',
                    )}
                  >
                    <Sun className="h-4 w-4" />
                    <div className="text-left">
                      <span>Field Mode</span>
                      <span className="block text-[10px] text-muted-foreground">Outdoor / Print</span>
                    </div>
                    {theme === 'light' && <span className="ml-auto text-xs">✓</span>}
                  </button>
                  <button
                    onClick={() => {
                      setTheme('dark');
                      setShowThemeMenu(false);
                    }}
                    className={cn(
                      'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors',
                      'hover:bg-muted',
                      theme === 'dark' && 'bg-muted text-accent',
                    )}
                  >
                    <Moon className="h-4 w-4" />
                    <div className="text-left">
                      <span>Control Room</span>
                      <span className="block text-[10px] text-muted-foreground">Terminal / Low-light</span>
                    </div>
                    {theme === 'dark' && <span className="ml-auto text-xs">✓</span>}
                  </button>
                  <div className="h-px bg-border mx-2" />
                  <button
                    onClick={() => {
                      setTheme('system');
                      setShowThemeMenu(false);
                    }}
                    className={cn(
                      'flex w-full items-center gap-2 px-3 py-2 text-sm transition-colors',
                      'hover:bg-muted',
                      theme === 'system' && 'bg-muted text-accent',
                    )}
                  >
                    <Monitor className="h-4 w-4" />
                    <div className="text-left">
                      <span>System (Auto)</span>
                      <span className="block text-[10px] text-muted-foreground">
                        Currently: {resolvedTheme === 'dark' ? 'Dark' : 'Light'}
                      </span>
                    </div>
                    {theme === 'system' && <span className="ml-auto text-xs">✓</span>}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Notifications */}
        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowNotifications(!showNotifications)}
            className="h-8 w-8 relative text-muted-foreground hover:text-foreground hover:bg-muted"
            aria-label={`Notifications${notificationCount > 0 ? ` (${notificationCount} unread)` : ''}`}
            aria-expanded={showNotifications}
            aria-haspopup="true"
          >
            <Bell className="h-4 w-4" />
            {notificationCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[9px] font-bold text-destructive-foreground notification-badge-glow">
                {notificationCount > 9 ? '9+' : notificationCount}
              </span>
            )}
          </Button>

          <AnimatePresence>
            {showNotifications && (
              <NotificationDropdown
                onClose={() => setShowNotifications(false)}
                pendingDecisions={pendingDecisions}
                pendingEscalations={pendingEscalations}
              />
            )}
          </AnimatePresence>
        </div>

        {/* Separator */}
        <div className="hidden sm:block w-px h-5 bg-border mx-0.5" />

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 h-9 pl-1.5 pr-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="User menu"
            aria-expanded={showUserMenu}
            aria-haspopup="true"
          >
            <div className="relative flex-shrink-0 flex items-center justify-center">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-accent text-accent-foreground text-[10px] font-bold leading-none">
                {user.initials}
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border-[1.5px] border-card bg-success" />
            </div>
            <span className="hidden text-xs font-medium md:block leading-none">{user.name.split(' ')[0]}</span>
            <ChevronDown
              className={cn(
                'hidden h-3 w-3 md:block transition-transform',
                showUserMenu && 'rotate-180',
              )}
            />
          </button>

          <AnimatePresence>
            {showUserMenu && <UserMenuDropdown onClose={() => setShowUserMenu(false)} />}
          </AnimatePresence>
        </div>
      </div>
    </motion.header>
  );
}

interface DropdownProps {
  onClose: () => void;
}

// Map Decision urgency → notification urgency
function mapDecisionUrgency(urgency: string): 'critical' | 'urgent' | 'normal' {
  switch (urgency) {
    case 'IMMEDIATE':
      return 'critical';
    case 'URGENT':
      return 'urgent';
    default:
      return 'normal';
  }
}

// Map Escalation priority → notification urgency
function mapEscalationPriority(priority: string): 'critical' | 'urgent' | 'normal' {
  switch (priority) {
    case 'CRITICAL':
      return 'critical';
    case 'HIGH':
      return 'urgent';
    default:
      return 'normal';
  }
}

interface NotificationDropdownProps extends DropdownProps {
  pendingDecisions: Decision[];
  pendingEscalations: Escalation[];
}

/** Format hours remaining until a deadline */
function formatTimeRemaining(deadline: string): string {
  const ms = new Date(deadline).getTime() - Date.now();
  if (ms <= 0) return 'OVERDUE';
  const hours = Math.floor(ms / 3600000);
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours >= 1) return `${hours}h`;
  const mins = Math.floor(ms / 60000);
  return `${mins}m`;
}

/** Compact currency — delegate to centralized formatter */
const compactUSD = (amount: number): string =>
  formatCurrency(amount, { compact: true });

function NotificationDropdown({
  onClose,
  pendingDecisions,
  pendingEscalations,
}: NotificationDropdownProps) {
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Build BUSINESS-VALUE notifications from live data
  const notifications = useMemo(() => {
    const items: Array<{
      id: string;
      type: 'decision' | 'escalation';
      urgency: 'critical' | 'urgent' | 'normal';
      unread: boolean;
      link: string;
      // Business context
      headline: string;
      exposure: number;
      actionType: string;
      actionCost: number;
      savings: number;
      inactionCost: number;
      shipmentsAffected: number;
      deadline: string;
      timeRemaining: string;
      confidence: number;
      eventSummary: string;
    }> = [];

    for (const d of pendingDecisions) {
      const exposure = d.q3_severity?.total_exposure_usd ?? 0;
      const actionCost = d.q5_action?.estimated_cost_usd ?? 0;
      const inactionCost = d.q7_inaction?.inaction_cost_usd ?? 0;
      const savings = Math.max(0, exposure - actionCost);
      const shipmentsAffected = d.q3_severity?.shipments_affected ?? 0;
      const deadline = d.q5_action?.deadline ?? d.expires_at;

      items.push({
        id: d.decision_id,
        type: 'decision',
        urgency: mapDecisionUrgency(d.q2_when?.urgency ?? 'WATCH'),
        unread: true,
        link: `/decisions/${d.decision_id}`,
        headline: exposure > 0
          ? `${compactUSD(exposure)} at Risk — ${shipmentsAffected} Shipment${shipmentsAffected !== 1 ? 's' : ''}`
          : d.q1_what?.event_summary ?? 'Risk Detected',
        exposure,
        actionType: d.q5_action?.recommended_action ?? 'MONITOR',
        actionCost,
        savings,
        inactionCost,
        shipmentsAffected,
        deadline,
        timeRemaining: formatTimeRemaining(deadline),
        confidence: d.q6_confidence?.confidence_score ?? 0,
        eventSummary: d.q1_what?.event_summary ?? '',
      });
    }

    for (const e of pendingEscalations) {
      items.push({
        id: e.id,
        type: 'escalation',
        urgency: mapEscalationPriority(e.priority),
        unread: true,
        link: `/human-review/${e.id}`,
        headline: e.exposure_usd > 0
          ? `${compactUSD(e.exposure_usd)} Exposure — Needs Review`
          : e.title,
        exposure: e.exposure_usd ?? 0,
        actionType: 'REVIEW',
        actionCost: 0,
        savings: 0,
        inactionCost: e.exposure_usd ?? 0,
        shipmentsAffected: 0,
        deadline: e.sla_deadline,
        timeRemaining: formatTimeRemaining(e.sla_deadline),
        confidence: 0,
        eventSummary: e.reason ?? e.title,
      });
    }

    // Sort: critical first, then by exposure descending
    const urgencyOrder = { critical: 0, urgent: 1, normal: 2 };
    items.sort((a, b) => {
      const urgDiff = urgencyOrder[a.urgency] - urgencyOrder[b.urgency];
      if (urgDiff !== 0) return urgDiff;
      return b.exposure - a.exposure;
    });

    return items;
  }, [pendingDecisions, pendingEscalations]);

  const handleNotificationClick = (link: string) => {
    onClose();
    navigate(link);
  };

  const notifCount = notifications.length;
  const totalExposure = notifications.reduce((sum, n) => sum + n.exposure, 0);

  return (
    <motion.div
      ref={dropdownRef}
      variants={dropdownVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className="absolute right-0 top-full z-50 mt-2 w-96 rounded-xl border border-border bg-card shadow-2xl shadow-black/20"
    >
      {/* Header with total exposure */}
      <div className="border-b border-border px-4 py-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-foreground">Active Alerts</h3>
          {notifCount > 0 && (
            <Badge className="bg-destructive/20 text-destructive border-destructive/40 text-[10px]">
              {notifCount} pending
            </Badge>
          )}
        </div>
        {totalExposure > 0 && (
          <div className="flex items-center gap-2 mt-1.5">
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-mono">
              <DollarSign className="h-3 w-3 text-destructive/60" />
              <span>Total Exposure:</span>
              <span className="text-destructive font-bold">{compactUSD(totalExposure)}</span>
            </div>
          </div>
        )}
      </div>

      <motion.div
        className="max-h-[420px] overflow-y-auto"
        role="menu"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <Shield className="h-8 w-8 text-success/40 mb-2" />
            <p className="text-xs font-medium text-muted-foreground">All clear</p>
            <p className="text-[10px] text-muted-foreground/60 mt-1">
              No active risks requiring your attention
            </p>
          </div>
        ) : (
          notifications.map((notif) => (
            <motion.button
              key={notif.id}
              role="menuitem"
              variants={staggerItem}
              onClick={() => handleNotificationClick(notif.link)}
              className={cn(
                'flex w-full flex-col gap-1.5 px-4 py-3 text-left',
                'hover:bg-muted/60 transition-all duration-200 border-b border-border/50 last:border-0',
                notif.urgency === 'critical' && 'bg-destructive/[0.03]',
                notif.urgency === 'urgent' && 'bg-urgency-urgent/[0.02]',
              )}
              whileHover={{ x: 2 }}
            >
              {/* Row 1: Urgency dot + Headline + Time remaining */}
              <div className="flex items-start gap-2 w-full">
                <div className={cn(
                  'mt-1 h-2 w-2 rounded-full shrink-0',
                  notif.urgency === 'critical' && 'bg-urgency-immediate animate-pulse',
                  notif.urgency === 'urgent' && 'bg-urgency-urgent',
                  notif.urgency === 'normal' && 'bg-muted-foreground',
                )} />
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    'text-xs font-semibold leading-tight',
                    notif.urgency === 'critical' ? 'text-destructive' : 'text-foreground',
                  )}>
                    {notif.headline}
                  </p>
                </div>
                <div className={cn(
                  'flex items-center gap-1 shrink-0 px-1.5 py-0.5 rounded-md text-[9px] font-mono font-bold',
                  notif.timeRemaining === 'OVERDUE'
                    ? 'bg-destructive/20 text-destructive'
                    : 'bg-muted text-muted-foreground',
                )}>
                  <Clock className="h-2.5 w-2.5" />
                  {notif.timeRemaining}
                </div>
              </div>

              {/* Row 2: Event context */}
              <p className="text-[10px] text-muted-foreground/70 line-clamp-1 pl-4">
                {notif.eventSummary}
              </p>

              {/* Row 3: Financial decision context — THE KEY BUSINESS VALUE */}
              {notif.type === 'decision' && notif.exposure > 0 && (
                <div className="flex items-center gap-3 pl-4 mt-0.5">
                  {/* Action + Cost */}
                  <div className="flex items-center gap-1 text-[9px] font-mono">
                    <span className="px-1 py-0.5 rounded bg-accent/10 text-accent font-bold">
                      {notif.actionType}
                    </span>
                    <span className="text-muted-foreground">{compactUSD(notif.actionCost)}</span>
                  </div>

                  {/* Savings */}
                  {notif.savings > 0 && (
                    <div className="flex items-center gap-0.5 text-[9px] font-mono text-success">
                      <TrendingDown className="h-2.5 w-2.5" />
                      <span>Saves {compactUSD(notif.savings)}</span>
                    </div>
                  )}

                  {/* Inaction cost */}
                  {notif.inactionCost > 0 && (
                    <div className="flex items-center gap-0.5 text-[9px] font-mono text-destructive/70">
                      <AlertTriangle className="h-2.5 w-2.5" />
                      <span>Loss: {compactUSD(notif.inactionCost)}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Row 3 alt: Escalation context */}
              {notif.type === 'escalation' && notif.exposure > 0 && (
                <div className="flex items-center gap-2 pl-4 mt-0.5">
                  <div className="flex items-center gap-1 text-[9px] font-mono">
                    <DollarSign className="h-2.5 w-2.5 text-destructive/50" />
                    <span className="text-destructive/70 font-bold">{compactUSD(notif.exposure)} exposure</span>
                  </div>
                  <span className="text-[9px] text-muted-foreground/50 font-mono">|</span>
                  <span className="text-[9px] text-muted-foreground/70 font-mono">SLA: {notif.timeRemaining}</span>
                </div>
              )}
            </motion.button>
          ))
        )}
      </motion.div>

      {/* Footer */}
      <div className="border-t border-border p-2">
        <Button
          variant="ghost"
          className="w-full text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
          onClick={() => {
            onClose();
            navigate('/decisions');
          }}
        >
          View all decisions
        </Button>
      </div>
    </motion.div>
  );
}

function UserMenuDropdown({ onClose }: DropdownProps) {
  const { user } = useUser();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const handleNavigate = (path: string) => {
    onClose();
    navigate(path);
  };

  const handleSignOut = () => {
    onClose();
    logout();
    navigate('/');
  };

  const menuItems = [
    { icon: User, label: 'Profile', onClick: () => handleNavigate('/settings') },
    { icon: Settings, label: 'Settings', onClick: () => handleNavigate('/settings') },
    {
      icon: HelpCircle,
      label: 'Help & Support',
      onClick: () => toast.info('Help documentation coming soon!'),
    },
  ];

  return (
    <motion.div
      ref={dropdownRef}
      variants={dropdownVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className="absolute right-0 top-full z-50 mt-2 w-52 rounded-lg border border-border bg-card shadow-xl overflow-hidden"
    >
      <div className="border-b border-border px-4 py-3">
        <p className="font-medium text-sm text-foreground">{user.name}</p>
        <p className="text-[10px] text-muted-foreground font-mono">{user.email}</p>
      </div>

      <motion.div className="p-1" role="menu" variants={staggerContainer} initial="hidden" animate="visible">
        {menuItems.map((item) => (
          <motion.button
            key={item.label}
            role="menuitem"
            variants={staggerItem}
            onClick={item.onClick}
            className="flex w-full items-center gap-3 rounded px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            whileHover={{ x: 2 }}
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </motion.button>
        ))}
      </motion.div>

      <div className="border-t border-border p-1">
        <motion.button
          role="menuitem"
          onClick={handleSignOut}
          className="flex w-full items-center gap-3 rounded px-3 py-2 text-xs text-destructive hover:bg-destructive/10 transition-colors"
          whileHover={{ x: 2 }}
        >
          <LogOut className="h-4 w-4" />
          <span>Sign out</span>
        </motion.button>
      </div>
    </motion.div>
  );
}
