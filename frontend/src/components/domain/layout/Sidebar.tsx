import { useState, useEffect, useCallback, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  AlertTriangle,
  FileText,
  Users,
  Bell,
  BarChart3,
  FileSearch,
  Globe,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useUser } from '@/contexts/user-context';
import type { UserRole } from '@/contexts/user-context';
// Health check uses direct fetch to avoid ApiError noise in console
import { useDecisionsList, useEscalationsList } from '@/hooks';
import { springs } from '@/lib/animations';
import { usePermissions } from '@/lib/permissions';

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
  className?: string;
}

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  badge?: number;
  badgeVariant?: 'default' | 'urgent' | 'critical';
}

// ── 3-section navigation structure ──────────────────────
const operationsItems: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Signals', href: '/signals', icon: AlertTriangle },
  { label: 'Decisions', href: '/decisions', icon: FileText },
  { label: 'Human Review', href: '/human-review', icon: Bell },
  { label: 'Customers', href: '/customers', icon: Users },
];

const intelligenceItems: NavItem[] = [
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'Oracle Reality', href: '/reality', icon: Globe },
];

const systemItems: NavItem[] = [
  { label: 'Audit Trail', href: '/audit', icon: FileSearch },
  { label: 'Settings', href: '/settings', icon: Settings },
];

// ── Role display config ─────────────────────────────────
const ROLE_CONFIG: Record<UserRole, { label: string; color: string }> = {
  admin: { label: 'ADMIN', color: 'text-accent' },
  analyst: { label: 'ANALYST', color: 'text-accent' },
  manager: { label: 'MANAGER', color: 'text-accent' },
  executive: { label: 'EXECUTIVE', color: 'text-warning' },
  viewer: { label: 'VIEWER', color: 'text-muted-foreground' },
};

// ── Animation variants ──────────────────────────────────
const sidebarVariants = {
  expanded: { width: 256, transition: springs.smooth },
  collapsed: { width: 64, transition: springs.smooth },
};

const logoTextVariants = {
  expanded: {
    opacity: 1,
    x: 0,
    display: 'block',
    transition: { delay: 0.1, ...springs.smooth },
  },
  collapsed: {
    opacity: 0,
    x: -10,
    transitionEnd: { display: 'none' },
    transition: springs.smooth,
  },
};

const navItemTextVariants = {
  expanded: { opacity: 1, x: 0, width: 'auto', transition: springs.smooth },
  collapsed: { opacity: 0, x: -10, width: 0, transition: springs.smooth },
};

const sectionLabelVariants = {
  expanded: { opacity: 1, height: 'auto', transition: { delay: 0.05, ...springs.smooth } },
  collapsed: { opacity: 0, height: 0, transition: springs.smooth },
};

// ── Sidebar Component ───────────────────────────────────
export function Sidebar({ isCollapsed, onToggle, className }: SidebarProps) {
  const { user } = useUser();
  const { visibleNavItems, role } = usePermissions();
  const roleConfig = ROLE_CONFIG[role] ?? ROLE_CONFIG.analyst;

  // Dynamic badge counts from live data
  const { data: decisions } = useDecisionsList();
  const { data: escalations } = useEscalationsList();

  const pendingDecisions = decisions?.filter((d) => d.status === 'PENDING').length ?? 0;
  const pendingEscalations = escalations?.filter((e) => e.status === 'PENDING').length ?? 0;

  const dynamicOpsItems = useMemo(
    () =>
      operationsItems.map((item) => {
        if (item.href === '/decisions' && pendingDecisions > 0) {
          return { ...item, badge: pendingDecisions, badgeVariant: 'urgent' as const };
        }
        if (item.href === '/human-review' && pendingEscalations > 0) {
          return { ...item, badge: pendingEscalations, badgeVariant: 'critical' as const };
        }
        return item;
      }),
    [pendingDecisions, pendingEscalations],
  );

  // Filter nav items by role permissions
  const filteredOpsItems = useMemo(
    () => dynamicOpsItems.filter(item => visibleNavItems.some(vi => vi.path === item.href)),
    [dynamicOpsItems, visibleNavItems],
  );
  const filteredIntelItems = useMemo(
    () => intelligenceItems.filter(item => visibleNavItems.some(vi => vi.path === item.href)),
    [visibleNavItems],
  );
  const filteredSystemItems = useMemo(
    () => systemItems.filter(item => visibleNavItems.some(vi => vi.path === item.href)),
    [visibleNavItems],
  );

  return (
    <motion.aside
      initial={false}
      animate={isCollapsed ? 'collapsed' : 'expanded'}
      variants={sidebarVariants}
      className={cn(
        'fixed left-0 top-0 z-40 flex h-screen flex-col sidebar',
        className,
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b border-sidebar-border px-3">
        <motion.div
          className="flex items-center gap-3"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <motion.div
            className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-accent shadow-sm transition-shadow"
            whileHover={{ scale: 1.05 }}
            transition={springs.snappy}
          >
            <Zap className="h-5 w-5 text-white" />
          </motion.div>

          <motion.div variants={logoTextVariants} className="overflow-hidden">
            <h1 className="text-lg font-bold tracking-tight notranslate" translate="no">
              <span className="text-gradient">RISKCAST</span>
            </h1>
            <p className="text-[10px] text-muted-foreground -mt-0.5 notranslate" translate="no">Decision Intelligence</p>
          </motion.div>
        </motion.div>

        <AnimatePresence>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={springs.snappy}
              className="ml-auto"
            >
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={onToggle}
                className="hover:bg-accent/10"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation — 3-section layout (supports Arrow Up/Down + Enter) */}
      <nav
        aria-label="Main navigation"
        className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1"
        onKeyDown={(e) => {
          const nav = e.currentTarget;
          const links = Array.from(nav.querySelectorAll<HTMLAnchorElement>('a[href]'));
          const current = document.activeElement as HTMLElement;
          const idx = links.indexOf(current as HTMLAnchorElement);

          if (e.key === 'ArrowDown') {
            e.preventDefault();
            const next = idx < links.length - 1 ? idx + 1 : 0;
            links[next]?.focus();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prev = idx > 0 ? idx - 1 : links.length - 1;
            links[prev]?.focus();
          }
        }}
      >
        {/* OPERATIONS — primary workflow */}
        {filteredOpsItems.length > 0 && (
          <>
            <SectionLabel label="Operations" isCollapsed={isCollapsed} />
            {filteredOpsItems.map((item, i) => (
              <NavItemComponent key={item.href} item={item} isCollapsed={isCollapsed} index={i} />
            ))}
          </>
        )}

        {/* Divider */}
        {filteredOpsItems.length > 0 && filteredIntelItems.length > 0 && (
          <div className="my-3 mx-2 border-t border-sidebar-border" />
        )}

        {/* INTELLIGENCE — analytical views */}
        {filteredIntelItems.length > 0 && (
          <>
            <SectionLabel label="Intelligence" isCollapsed={isCollapsed} />
            {filteredIntelItems.map((item, i) => (
              <NavItemComponent
                key={item.href}
                item={item}
                isCollapsed={isCollapsed}
                index={filteredOpsItems.length + i + 1}
              />
            ))}
          </>
        )}

        {/* Divider */}
        {(filteredOpsItems.length > 0 || filteredIntelItems.length > 0) && filteredSystemItems.length > 0 && (
          <div className="my-3 mx-2 border-t border-sidebar-border" />
        )}

        {/* SYSTEM — administrative */}
        {filteredSystemItems.length > 0 && (
          <>
            <SectionLabel label="System" isCollapsed={isCollapsed} />
            {filteredSystemItems.map((item, i) => (
              <NavItemComponent
                key={item.href}
                item={item}
                isCollapsed={isCollapsed}
                index={filteredOpsItems.length + filteredIntelItems.length + i + 2}
              />
            ))}
          </>
        )}
      </nav>

      {/* Collapse toggle (when collapsed) */}
      <AnimatePresence>
        {isCollapsed && (
          <motion.div
            className="border-t border-sidebar-border p-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="w-full hover:bg-accent/10"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer — role indicator + version */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            className="border-t border-sidebar-border p-4 space-y-2"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={springs.smooth}
          >
            {/* Role badge */}
            <div className="flex items-center gap-2">
              <Shield className={cn('h-3.5 w-3.5', roleConfig.color)} />
              <span
                className={cn('text-[10px] font-mono font-bold tracking-widest', roleConfig.color)}
              >
                {roleConfig.label}
              </span>
            </div>

            <SystemStatus />
            <p className="text-[10px] text-muted-foreground/60">RISKCAST &bull; Enterprise</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}

// ── Section label ───────────────────────────────────────
function SectionLabel({ label, isCollapsed }: { label: string; isCollapsed: boolean }) {
  return (
    <motion.div variants={sectionLabelVariants} className="overflow-hidden">
      {!isCollapsed && (
        <p className="px-3 pt-2 pb-1 text-[10px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/60">
          {label}
        </p>
      )}
    </motion.div>
  );
}

// ── NavItem ─────────────────────────────────────────────
interface NavItemProps {
  item: NavItem;
  isCollapsed: boolean;
  index: number;
}

function NavItemComponent({ item, isCollapsed, index }: NavItemProps) {
  const Icon = item.icon;
  const location = useLocation();
  const isActive =
    location.pathname === item.href ||
    (item.href !== '/dashboard' && location.pathname.startsWith(item.href));

  const badgeColors = {
    default: 'bg-muted text-muted-foreground',
    urgent: 'bg-urgency-urgent text-white',
    critical: 'bg-urgency-immediate text-white',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, ...springs.smooth }}
      className="relative group"
    >
      <NavLink
        to={item.href}
        aria-current={isActive ? 'page' : undefined}
        className={cn(
          'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium',
          'transition-all duration-200',
          isActive ? 'text-accent font-semibold' : 'text-sidebar-foreground hover:text-foreground',
          isCollapsed && 'justify-center px-2',
        )}
        title={isCollapsed ? item.label : undefined}
      >
        {/* Active indicator */}
        <AnimatePresence>
          {isActive && (
            <motion.div
              layoutId="activeIndicator"
              className="absolute inset-0 rounded-lg bg-accent/20 border border-accent/40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={springs.smooth}
            />
          )}
        </AnimatePresence>

        {/* Active left bar */}
        <AnimatePresence>
          {isActive && !isCollapsed && (
            <motion.div
              className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-accent"
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              exit={{ scaleY: 0 }}
              transition={springs.smooth}
            />
          )}
        </AnimatePresence>

        {/* Hover background */}
        <motion.div
          className="absolute inset-0 rounded-lg bg-sidebar-accent opacity-0 group-hover:opacity-100"
          initial={false}
          transition={{ duration: 0.2 }}
        />

        {/* Icon */}
        <motion.div
          className="relative z-10"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          transition={springs.snappy}
        >
          <Icon
            className={cn(
              'h-5 w-5 shrink-0 transition-colors',
              isActive ? 'text-accent' : 'text-muted-foreground group-hover:text-foreground',
            )}
          />
        </motion.div>

        {/* Label */}
        <motion.span variants={navItemTextVariants} className="relative z-10 flex-1 truncate">
          {item.label}
        </motion.span>

        {/* Badge (expanded) */}
        <AnimatePresence>
          {!isCollapsed && item.badge !== undefined && item.badge > 0 && (
            <motion.span
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={springs.bouncy}
              className={cn(
                'relative z-10 flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold',
                badgeColors[item.badgeVariant ?? 'default'],
                item.badgeVariant === 'critical' &&
                  'animate-pulse shadow-lg shadow-urgency-immediate/30',
              )}
            >
              {item.badge}
            </motion.span>
          )}
        </AnimatePresence>

        {/* Collapsed badge dot */}
        <AnimatePresence>
          {isCollapsed && item.badge !== undefined && item.badge > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={springs.bouncy}
              className={cn(
                'absolute right-1 top-1 h-2.5 w-2.5 rounded-full',
                item.badgeVariant === 'critical'
                  ? 'bg-urgency-immediate animate-pulse shadow-md shadow-urgency-immediate/50'
                  : item.badgeVariant === 'urgent'
                    ? 'bg-urgency-urgent'
                    : 'bg-muted-foreground',
              )}
            />
          )}
        </AnimatePresence>
      </NavLink>

      {/* Tooltip for collapsed state — CSS-driven for performance */}
      {isCollapsed && (
        <div
          className="absolute left-full top-1/2 -translate-y-1/2 ml-2 z-50 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-150 delay-200"
          role="tooltip"
        >
          <div className="bg-popover text-popover-foreground text-sm font-medium px-3 py-1.5 rounded-md shadow-lg border whitespace-nowrap">
            {item.label}
            {item.badge !== undefined && item.badge > 0 && (
              <span
                className={cn(
                  'ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold',
                  badgeColors[item.badgeVariant ?? 'default'],
                )}
              >
                {item.badge}
              </span>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ── System health status ────────────────────────────────
function SystemStatus() {
  const [status, setStatus] = useState<'online' | 'offline'>('offline');
  const [failures, setFailures] = useState(0);

  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 2000);
      const response = await fetch(`/health`, {
        method: 'GET',
        signal: controller.signal,
      });
      clearTimeout(timeout);
      if (response.ok || response.status < 500) {
        setStatus('online');
        setFailures(0);
      } else {
        setStatus('offline');
        setFailures((c) => c + 1);
      }
    } catch {
      setStatus('offline');
      setFailures((c) => c + 1);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    // Back off: 30s online, exponential up to 120s offline
    const intervalMs = failures === 0 ? 30_000 : Math.min(60_000 * failures, 120_000);
    const interval = setInterval(checkHealth, intervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, failures]);

  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-2 w-2 shrink-0">
        {status === 'online' && (
          <motion.span
            className="absolute inline-flex h-full w-full rounded-full bg-success/50"
            animate={{ scale: [1, 2.5], opacity: [0.5, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
        <span
          className={cn(
            'relative inline-flex h-2 w-2 rounded-full',
            status === 'online'
            ? 'bg-success'
            : 'bg-error',
          )}
        />
      </span>
      <span
        className={cn(
          'font-mono text-[10px] tracking-wider',
          status === 'online'
            ? 'text-success/60'
            : 'text-error/60',
        )}
      >
        {status === 'online' ? 'SYSTEM ONLINE' : 'OFFLINE'}
      </span>
    </div>
  );
}
