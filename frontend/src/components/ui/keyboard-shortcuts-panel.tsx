import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Keyboard } from 'lucide-react';
import { useShortcutsPanelVisible } from '@/hooks/useKeyboardShortcuts';
import type { ShortcutDefinition } from '@/hooks/useKeyboardShortcuts';
import { cn } from '@/lib/utils';

// ---------------------------------------------------------------------------
// Default global shortcuts (display-only for the panel)
// ---------------------------------------------------------------------------
const DISPLAY_SHORTCUTS: ShortcutDefinition[] = [
  // Navigation
  { keys: 'g d', label: 'Go to Dashboard', category: 'navigation', action: () => {} },
  { keys: 'g s', label: 'Go to Signals', category: 'navigation', action: () => {} },
  { keys: 'g e', label: 'Go to Decisions', category: 'navigation', action: () => {} },
  { keys: 'g c', label: 'Go to Customers', category: 'navigation', action: () => {} },
  { keys: 'g r', label: 'Go to Human Review', category: 'navigation', action: () => {} },
  { keys: 'g a', label: 'Go to Analytics', category: 'navigation', action: () => {} },
  { keys: 'g o', label: 'Go to Oracle Reality', category: 'navigation', action: () => {} },
  { keys: 'g t', label: 'Go to Settings', category: 'navigation', action: () => {} },

  // List actions
  { keys: 'j', label: 'Next item', category: 'list', action: () => {} },
  { keys: 'k', label: 'Previous item', category: 'list', action: () => {} },
  { keys: 'Enter', label: 'Open selected item', category: 'list', action: () => {} },
  { keys: 'a', label: 'Acknowledge / Approve', category: 'list', action: () => {} },
  { keys: 'e', label: 'Escalate selected', category: 'list', action: () => {} },

  // UI
  { keys: '/', label: 'Focus search', category: 'ui', action: () => {} },
  { keys: '?', label: 'Toggle this panel', category: 'ui', action: () => {} },
  { keys: 'Escape', label: 'Close modal / panel', category: 'ui', action: () => {} },
];

const CATEGORY_LABELS: Record<string, string> = {
  navigation: 'Navigation',
  list: 'List Actions',
  actions: 'Decision Actions',
  ui: 'UI Controls',
};

const CATEGORY_ORDER = ['navigation', 'list', 'actions', 'ui'];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function KeyboardShortcutsPanel() {
  const { visible, close } = useShortcutsPanelVisible();
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!visible) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [visible, close]);

  // Close on click outside
  useEffect(() => {
    if (!visible) return;
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        close();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [visible, close]);

  // Group shortcuts by category
  const grouped = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    label: CATEGORY_LABELS[cat] || cat,
    shortcuts: DISPLAY_SHORTCUTS.filter((s) => s.category === cat),
  })).filter((g) => g.shortcuts.length > 0);

  return (
    <AnimatePresence>
      {visible && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm"
            onClick={close}
          />

          {/* Panel */}
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 400, damping: 30 }}
            className="fixed inset-x-4 top-[10%] z-[61] mx-auto max-w-lg rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Keyboard className="h-4 w-4 text-accent" />
                <h2 className="text-sm font-semibold text-foreground">Keyboard Shortcuts</h2>
              </div>
              <button
                onClick={close}
                className="h-7 w-7 rounded-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label="Close shortcuts panel"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Body */}
            <div className="max-h-[60vh] overflow-y-auto px-5 py-4 space-y-5">
              {grouped.map(({ category, label, shortcuts }) => (
                <div key={category}>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    {label}
                  </h3>
                  <div className="space-y-1">
                    {shortcuts.map((shortcut) => (
                      <div
                        key={shortcut.keys}
                        className="flex items-center justify-between py-1.5"
                      >
                        <span className="text-xs text-foreground/80">{shortcut.label}</span>
                        <ShortcutKeys keys={shortcut.keys} />
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Cmd+K hint */}
              <div className="pt-2 border-t border-border">
                <div className="flex items-center justify-between py-1.5">
                  <span className="text-xs text-foreground/80">Command Palette</span>
                  <div className="flex items-center gap-1">
                    <kbd className={kbdClass}>
                      {navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}
                    </kbd>
                    <kbd className={kbdClass}>K</kbd>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-border bg-muted/30">
              <p className="text-[10px] text-muted-foreground text-center">
                Press <kbd className={cn(kbdClass, 'text-[9px]')}>?</kbd> to toggle this panel
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const kbdClass =
  'inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded border border-border bg-muted text-[10px] font-mono text-muted-foreground';

function ShortcutKeys({ keys }: { keys: string }) {
  const parts = keys.split(' ');
  return (
    <div className="flex items-center gap-1">
      {parts.map((part, i) => (
        <span key={i} className="flex items-center gap-0.5">
          {i > 0 && <span className="text-muted-foreground/40 text-[9px] mx-0.5">then</span>}
          <kbd className={kbdClass}>{part}</kbd>
        </span>
      ))}
    </div>
  );
}

export default KeyboardShortcutsPanel;
