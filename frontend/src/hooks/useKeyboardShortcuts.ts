import { useEffect, useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ShortcutDefinition {
  /** Key sequence, e.g. 'g d' for go-to-dashboard, or single key like '/' */
  keys: string;
  /** Human-readable label */
  label: string;
  /** Category for grouping in shortcuts panel */
  category: 'navigation' | 'actions' | 'ui' | 'list';
  /** Handler function */
  action: () => void;
  /** Whether this shortcut requires a modifier (Ctrl/Cmd) */
  requiresModifier?: boolean;
}

interface KeyboardShortcutsOptions {
  /** Whether shortcuts are enabled (respects settings) */
  enabled?: boolean;
  /** Additional page-specific shortcuts */
  extraShortcuts?: ShortcutDefinition[];
}

// ---------------------------------------------------------------------------
// Global state for shortcut panel visibility
// ---------------------------------------------------------------------------
let showShortcutsPanelGlobal = false;
const listeners = new Set<(v: boolean) => void>();

export function useShortcutsPanelVisible() {
  const [visible, setVisible] = useState(showShortcutsPanelGlobal);

  useEffect(() => {
    const handler = (v: boolean) => setVisible(v);
    listeners.add(handler);
    return () => { listeners.delete(handler); };
  }, []);

  const toggle = useCallback(() => {
    showShortcutsPanelGlobal = !showShortcutsPanelGlobal;
    listeners.forEach((fn) => fn(showShortcutsPanelGlobal));
  }, []);

  const close = useCallback(() => {
    showShortcutsPanelGlobal = false;
    listeners.forEach((fn) => fn(false));
  }, []);

  return { visible, toggle, close };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useKeyboardShortcuts(options: KeyboardShortcutsOptions = {}) {
  const { enabled = true, extraShortcuts = [] } = options;
  const navigate = useNavigate();
  const sequenceRef = useRef('');
  const sequenceTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const { toggle: togglePanel } = useShortcutsPanelVisible();

  // Build global shortcuts
  const globalShortcuts: ShortcutDefinition[] = [
    // Navigation (g + key sequences)
    { keys: 'g d', label: 'Go to Dashboard', category: 'navigation', action: () => navigate('/dashboard') },
    { keys: 'g s', label: 'Go to Signals', category: 'navigation', action: () => navigate('/signals') },
    { keys: 'g c', label: 'Go to Customers', category: 'navigation', action: () => navigate('/customers') },
    { keys: 'g r', label: 'Go to Human Review', category: 'navigation', action: () => navigate('/human-review') },
    { keys: 'g e', label: 'Go to Decisions', category: 'navigation', action: () => navigate('/decisions') },
    { keys: 'g a', label: 'Go to Analytics', category: 'navigation', action: () => navigate('/analytics') },
    { keys: 'g o', label: 'Go to Oracle Reality', category: 'navigation', action: () => navigate('/reality') },
    { keys: 'g t', label: 'Go to Settings', category: 'navigation', action: () => navigate('/settings') },

    // UI controls
    { keys: '?', label: 'Toggle Keyboard Shortcuts', category: 'ui', action: togglePanel },
    { keys: 'Escape', label: 'Close modal / panel', category: 'ui', action: () => {
      // Dispatches a custom event that modals/panels can listen to
      document.dispatchEvent(new CustomEvent('riskcast:escape'));
    }},
  ];

  const allShortcuts = [...globalShortcuts, ...extraShortcuts];

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Ignore when typing in inputs/textareas/contenteditable
      const target = e.target as HTMLElement;
      const tagName = target.tagName.toLowerCase();
      if (
        tagName === 'input' ||
        tagName === 'textarea' ||
        tagName === 'select' ||
        target.isContentEditable
      ) {
        // Exception: Escape should always work
        if (e.key !== 'Escape') return;
      }

      // Don't intercept Cmd/Ctrl+K (command palette)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') return;

      const key = e.key;

      // Build sequence
      if (sequenceTimerRef.current) {
        clearTimeout(sequenceTimerRef.current);
      }

      if (sequenceRef.current) {
        sequenceRef.current += ' ' + key;
      } else {
        sequenceRef.current = key;
      }

      const currentSequence = sequenceRef.current;

      // Check for exact match
      const match = allShortcuts.find((s) => s.keys === currentSequence);
      if (match) {
        e.preventDefault();
        match.action();
        sequenceRef.current = '';
        return;
      }

      // Check if any shortcut starts with current sequence (partial match)
      const hasPartial = allShortcuts.some((s) => s.keys.startsWith(currentSequence + ' '));
      if (hasPartial) {
        // Wait for next key
        sequenceTimerRef.current = setTimeout(() => {
          sequenceRef.current = '';
        }, 1000);
        return;
      }

      // No match — reset
      sequenceRef.current = '';
    },
    [enabled, allShortcuts],
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return { shortcuts: allShortcuts };
}

export default useKeyboardShortcuts;
