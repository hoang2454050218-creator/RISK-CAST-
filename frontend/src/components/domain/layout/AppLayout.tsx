import { useState, useEffect } from 'react';
import { Outlet } from 'react-router';
import { motion, AnimatePresence } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { MobileNav } from './MobileNav';
import { CommandPalette, useCommandPalette } from '@/components/ui/command-palette';
import { ErrorBoundary } from '@/components/ui/error-boundary';
import { ChatWidget } from '@/components/domain/chat/ChatWidget';
import { KeyboardShortcutsPanel } from '@/components/ui/keyboard-shortcuts-panel';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

export function AppLayout() {
  // Initialize sidebar collapsed state based on current viewport:
  // Tablet (768–1023px) → collapsed, Desktop (1024px+) → expanded
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    const md = window.matchMedia('(min-width: 768px)').matches;
    const lg = window.matchMedia('(min-width: 1024px)').matches;
    return md && !lg;
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isAboveMd, setIsAboveMd] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches,
  );
  const commandPalette = useCommandPalette();
  useKeyboardShortcuts({ enabled: true });

  // Responsive sidebar: auto-collapse on tablet (md), auto-expand on desktop (lg)
  useEffect(() => {
    const mdMql = window.matchMedia('(min-width: 768px)');
    const lgMql = window.matchMedia('(min-width: 1024px)');

    const update = () => {
      const md = mdMql.matches;
      const lg = lgMql.matches;
      setIsAboveMd(md);
      if (md && !lg) setSidebarCollapsed(true);
      else if (lg) setSidebarCollapsed(false);
    };

    mdMql.addEventListener('change', update);
    lgMql.addEventListener('change', update);
    return () => {
      mdMql.removeEventListener('change', update);
      lgMql.removeEventListener('change', update);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Skip Link for Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:bg-background focus:p-4 focus:text-foreground"
      >
        Skip to main content
      </a>

      {/* Global Command Palette (Cmd+K) */}
      <CommandPalette isOpen={commandPalette.isOpen} onClose={commandPalette.close} />

      {/* Desktop Sidebar */}
      <div className="hidden md:block">
        <Sidebar
          isCollapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
              onClick={() => setMobileMenuOpen(false)}
              aria-hidden="true"
            />
            <motion.div
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={springs.smooth}
              className="fixed inset-y-0 left-0 z-50 md:hidden"
            >
              <Sidebar isCollapsed={false} onToggle={() => setMobileMenuOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <motion.div
        className={cn(
          'flex flex-col min-h-screen transition-all duration-300 ease-out',
          // CSS fallbacks: tablet (md) = collapsed 64px, desktop (lg) = expanded 256px
          sidebarCollapsed ? 'md:ml-16' : 'md:ml-16 lg:ml-64',
        )}
        initial={false}
        animate={{
          // Mobile: no margin (sidebar hidden); md+: respect collapsed state
          marginLeft: isAboveMd ? (sidebarCollapsed ? 64 : 256) : 0,
        }}
        transition={springs.smooth}
      >
        {/* Top Bar */}
        <TopBar
          showMenuButton
          onMenuClick={() => setMobileMenuOpen(true)}
          onSearchClick={commandPalette.open}
        />

        {/* Page Content with Error Boundary */}
        <main className="flex-1 p-4 pb-20 md:p-6 md:pb-6" id="main-content">
          <ErrorBoundary>
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springs.smooth}
            >
              <Outlet />
            </motion.div>
          </ErrorBoundary>
        </main>
      </motion.div>

      {/* Mobile Bottom Navigation */}
      <MobileNav />

      {/* Floating AI Chat Widget — bottom-right on every page */}
      <ChatWidget />

      {/* Global Keyboard Shortcuts Panel (toggled by ?) */}
      <KeyboardShortcutsPanel />
    </div>
  );
}
