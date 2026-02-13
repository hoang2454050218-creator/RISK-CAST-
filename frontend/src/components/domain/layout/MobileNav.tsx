import { useState, useCallback, useEffect, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  AlertTriangle,
  FileText,
  Bell,
  MoreHorizontal,
  Users,
  BarChart3,
  Globe,
  FileSearch,
  Settings,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';
import { useDecisionsList, useEscalationsList } from '@/hooks';

interface MobileNavProps {
  className?: string;
}

interface NavItem {
  label: string;
  href: string;
  icon: typeof LayoutDashboard;
  badge?: number;
  ariaLabel?: string;
}

// ── Primary items shown in bottom bar ───────────────────
const primaryItems: NavItem[] = [
  { label: 'Home', href: '/dashboard', icon: LayoutDashboard, ariaLabel: 'Dashboard home' },
  { label: 'Signals', href: '/signals', icon: AlertTriangle, ariaLabel: 'View signals' },
  { label: 'Decisions', href: '/decisions', icon: FileText, ariaLabel: 'View decisions' },
  { label: 'Review', href: '/human-review', icon: Bell, ariaLabel: 'Human review queue' },
];

// ── Overflow items shown in "More" sheet ────────────────
const overflowItems: NavItem[] = [
  { label: 'Customers', href: '/customers', icon: Users },
  { label: 'Analytics', href: '/analytics', icon: BarChart3 },
  { label: 'Oracle Reality', href: '/reality', icon: Globe },
  { label: 'Audit Trail', href: '/audit', icon: FileSearch },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export function MobileNav({ className }: MobileNavProps) {
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const location = useLocation();

  // Dynamic badge counts from live data
  const { data: decisions } = useDecisionsList();
  const { data: escalations } = useEscalationsList();

  const pendingDecisions = decisions?.filter((d) => d.status === 'PENDING').length ?? 0;
  const pendingEscalations = escalations?.filter((e) => e.status === 'PENDING').length ?? 0;

  const dynamicPrimaryItems = useMemo(
    () =>
      primaryItems.map((item) => {
        if (item.href === '/decisions' && pendingDecisions > 0) {
          return {
            ...item,
            badge: pendingDecisions,
            ariaLabel: `View decisions (${pendingDecisions} pending)`,
          };
        }
        if (item.href === '/human-review' && pendingEscalations > 0) {
          return {
            ...item,
            badge: pendingEscalations,
            ariaLabel: `Human review queue (${pendingEscalations} pending)`,
          };
        }
        return item;
      }),
    [pendingDecisions, pendingEscalations],
  );

  // Close sheet on route change
  useEffect(() => {
    setIsSheetOpen(false);
  }, [location.pathname]);

  // Close on Escape
  useEffect(() => {
    if (!isSheetOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsSheetOpen(false);
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isSheetOpen]);

  const toggleSheet = useCallback(() => setIsSheetOpen((v) => !v), []);

  // Check if any overflow route is active
  const isOverflowActive = overflowItems.some(
    (item) => location.pathname === item.href || location.pathname.startsWith(item.href + '/'),
  );

  return (
    <>
      {/* Bottom sheet overlay */}
      <AnimatePresence>
        {isSheetOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSheetOpen(false)}
            />

            {/* Sheet */}
            <motion.div
              className="fixed bottom-16 left-0 right-0 z-50 mx-3 mb-2 rounded-xl border bg-card shadow-2xl md:hidden"
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 40 }}
              transition={springs.smooth}
            >
              <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b">
                <span className="text-xs font-mono font-semibold uppercase tracking-widest text-muted-foreground">
                  More
                </span>
                <button
                  onClick={() => setIsSheetOpen(false)}
                  className="p-2.5 -mr-1.5 rounded-md hover:bg-muted transition-colors min-h-[44px] min-w-[44px] inline-flex items-center justify-center"
                  aria-label="Close menu"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>

              <div className="p-2 space-y-0.5">
                {overflowItems.map((item) => {
                  const Icon = item.icon;
                  const isActive =
                    location.pathname === item.href ||
                    location.pathname.startsWith(item.href + '/');

                  return (
                    <NavLink
                      key={item.href}
                      to={item.href}
                      className={cn(
                        'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                        isActive
                          ? 'bg-accent/10 text-accent'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Bottom navigation bar */}
      <nav
        className={cn(
          'fixed bottom-0 left-0 right-0 z-40 border-t-0 topbar-border md:hidden',
          'topbar-glass pb-[env(safe-area-inset-bottom)]',
          className,
        )}
        role="navigation"
        aria-label="Mobile navigation"
      >
        <div className="flex h-16 items-center justify-around">
          {dynamicPrimaryItems.map((item) => (
            <MobileNavItem key={item.href} item={item} />
          ))}

          {/* More button */}
          <button
            onClick={toggleSheet}
            aria-label="More navigation options"
            aria-expanded={isSheetOpen}
            className={cn(
              'relative flex flex-col items-center justify-center gap-1',
              'min-h-[44px] min-w-[44px] px-3 py-2',
              'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
              isSheetOpen || isOverflowActive
                ? 'text-accent'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <MoreHorizontal className="h-5 w-5" aria-hidden="true" />
            <span className="text-[10px] font-medium">More</span>

            {/* Active indicator for overflow routes */}
            {isOverflowActive && !isSheetOpen && (
              <span className="absolute top-1.5 right-2.5 h-2 w-2 rounded-full bg-accent" />
            )}
          </button>
        </div>

        {/* Safe area padding for devices with home indicator */}
        <div className="h-safe-area-inset-bottom bg-background" aria-hidden="true" />
      </nav>
    </>
  );
}

// ── MobileNavItem ───────────────────────────────────────
interface MobileNavItemProps {
  item: NavItem;
}

function MobileNavItem({ item }: MobileNavItemProps) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.href}
      aria-label={item.ariaLabel || item.label}
      className={({ isActive }) =>
        cn(
          'relative flex flex-col items-center justify-center gap-1',
          'min-h-[44px] min-w-[44px] px-3 py-2',
          'transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
          isActive ? 'text-accent' : 'text-muted-foreground hover:text-foreground',
        )
      }
    >
      <div className="relative">
        <Icon className="h-5 w-5" aria-hidden="true" />
        {item.badge !== undefined && item.badge > 0 && (
          <span
            className="absolute -right-2 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-urgency-immediate px-1 text-[10px] font-bold text-white"
            aria-hidden="true"
          >
            {item.badge}
          </span>
        )}
      </div>
      <span className="text-[10px] font-medium">{item.label}</span>
    </NavLink>
  );
}
