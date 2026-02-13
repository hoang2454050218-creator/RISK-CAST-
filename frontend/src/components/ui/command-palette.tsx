/**
 * CommandPalette - Global search and quick actions (Cmd+K / Ctrl+K)
 *
 * Features:
 * - Fuzzy search across decisions, signals, customers
 * - Quick navigation to any page
 * - Quick actions (acknowledge, override, escalate)
 * - Keyboard-first design
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import {
  Search,
  FileText,
  AlertTriangle,
  Users,
  BarChart3,
  Settings,
  ArrowRight,
  Command,
  CornerDownLeft,
  Clock,
  XCircle,
  Globe,
  Sparkles,
  History,
} from 'lucide-react';

interface CommandItem {
  id: string;
  title: string;
  subtitle?: string;
  icon: React.ElementType;
  action: () => void;
  keywords?: string[];
  section: 'navigation' | 'decisions' | 'actions' | 'recent' | 'data' | 'ai';
  shortcutHint?: string;
}

/**
 * Calculate fuzzy match score (higher is better)
 */
function fuzzyScore(text: string, query: string): number {
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();

  // Exact match gets highest score
  if (lowerText === lowerQuery) return 100;

  // Start of string match
  if (lowerText.startsWith(lowerQuery)) return 80;

  // Contains match
  if (lowerText.includes(lowerQuery)) return 60;

  // Word boundary match (e.g., "go" matches "Go to Dashboard")
  const words = lowerText.split(/\s+/);
  if (words.some((word) => word.startsWith(lowerQuery))) return 50;

  // Fuzzy character-by-character match
  let score = 0;
  let queryIndex = 0;
  let consecutiveBonus = 0;

  for (let i = 0; i < lowerText.length && queryIndex < lowerQuery.length; i++) {
    if (lowerText[i] === lowerQuery[queryIndex]) {
      score += 10 + consecutiveBonus;
      consecutiveBonus += 5; // Reward consecutive matches
      queryIndex++;
    } else {
      consecutiveBonus = 0;
    }
  }

  // Only count as match if we found all query characters
  return queryIndex === lowerQuery.length ? Math.min(score, 40) : 0;
}

/**
 * Highlight matched text in search results with multi-match support
 */
function highlightMatch(text: string, query: string): ReactNode {
  if (!query.trim()) return text;

  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();

  // Simple substring match
  const index = lowerText.indexOf(lowerQuery);
  if (index !== -1) {
    const before = text.slice(0, index);
    const match = text.slice(index, index + query.length);
    const after = text.slice(index + query.length);

    return (
      <>
        {before}
        <mark className="bg-accent/30 text-accent-foreground rounded px-0.5 font-medium">
          {match}
        </mark>
        {after}
      </>
    );
  }

  // Fuzzy highlight - highlight individual matched characters
  const result: ReactNode[] = [];
  let queryIndex = 0;

  for (let i = 0; i < text.length; i++) {
    if (queryIndex < lowerQuery.length && text[i].toLowerCase() === lowerQuery[queryIndex]) {
      result.push(
        <mark key={i} className="bg-accent/20 text-accent rounded-sm px-px font-medium">
          {text[i]}
        </mark>,
      );
      queryIndex++;
    } else {
      result.push(text[i]);
    }
  }

  return <>{result}</>;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Recent Searches (persisted in localStorage)
// ---------------------------------------------------------------------------
const RECENT_KEY = 'riskcast:recent-searches';
const MAX_RECENT = 5;

function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch {
    return [];
  }
}

function addRecentSearch(query: string) {
  const recent = getRecentSearches().filter((s) => s !== query);
  recent.unshift(query);
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [inputValue, setInputValue] = useState('');
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Build data items from React Query cache
  const dataItems: CommandItem[] = useMemo(() => {
    if (!query.trim()) return [];
    const items: CommandItem[] = [];
    const lowerQuery = query.toLowerCase();

    // Search decisions from cache
    const decisionsData = queryClient.getQueryData<Array<{ decision_id: string; q1_what: { event_summary: string }; status: string }>>(['decisions', 'list']);
    if (decisionsData) {
      for (const d of decisionsData) {
        const summary = d.q1_what?.event_summary || '';
        if (summary.toLowerCase().includes(lowerQuery) || d.decision_id.toLowerCase().includes(lowerQuery)) {
          items.push({
            id: `data-decision-${d.decision_id}`,
            title: summary || d.decision_id,
            subtitle: `Decision · ${d.status}`,
            icon: FileText,
            action: () => navigate(`/decisions/${d.decision_id}`),
            section: 'data',
          });
        }
        if (items.length >= 5) break;
      }
    }

    // Search signals from cache
    const signalsData = queryClient.getQueryData<Array<{ signal_id: string; title: string; source: string }>>(['signals', 'list']);
    if (signalsData) {
      for (const s of signalsData) {
        const title = s.title || '';
        if (title.toLowerCase().includes(lowerQuery) || s.signal_id?.toLowerCase().includes(lowerQuery)) {
          items.push({
            id: `data-signal-${s.signal_id}`,
            title: title || s.signal_id,
            subtitle: `Signal · ${s.source || 'Unknown'}`,
            icon: AlertTriangle,
            action: () => navigate(`/signals/${s.signal_id}`),
            section: 'data',
          });
        }
        if (items.length >= 8) break;
      }
    }

    // Search customers from cache
    const customersData = queryClient.getQueryData<Array<{ customer_id: string; name: string }>>(['customers', 'list']);
    if (customersData) {
      for (const c of customersData) {
        if (c.name?.toLowerCase().includes(lowerQuery) || c.customer_id?.toLowerCase().includes(lowerQuery)) {
          items.push({
            id: `data-customer-${c.customer_id}`,
            title: c.name || c.customer_id,
            subtitle: 'Customer',
            icon: Users,
            action: () => navigate(`/customers/${c.customer_id}`),
            section: 'data',
          });
        }
        if (items.length >= 10) break;
      }
    }

    return items;
  }, [query, queryClient, navigate]);

  // Recent search items
  const recentItems: CommandItem[] = useMemo(() => {
    if (query.trim()) return [];
    return getRecentSearches().map((s, i) => ({
      id: `recent-${i}`,
      title: s,
      icon: History,
      action: () => {
        setInputValue(s);
        clearTimeout(debounceRef.current);
        setQuery(s);
      },
      section: 'recent' as const,
    }));
  }, [query]);

  // Define command items
  const commandItems: CommandItem[] = useMemo(
    () => [
      // Navigation
      {
        id: 'nav-dashboard',
        title: 'Go to Dashboard',
        icon: BarChart3,
        action: () => navigate('/dashboard'),
        keywords: ['home', 'overview', 'stats'],
        section: 'navigation',
        shortcutHint: 'g d',
      },
      {
        id: 'nav-decisions',
        title: 'Go to Decisions',
        icon: FileText,
        action: () => navigate('/decisions'),
        keywords: ['list', 'all', 'view'],
        section: 'navigation',
        shortcutHint: 'g e',
      },
      {
        id: 'nav-signals',
        title: 'Go to Signals',
        icon: AlertTriangle,
        action: () => navigate('/signals'),
        keywords: ['omen', 'alerts', 'warnings'],
        section: 'navigation',
        shortcutHint: 'g s',
      },
      {
        id: 'nav-customers',
        title: 'Go to Customers',
        icon: Users,
        action: () => navigate('/customers'),
        keywords: ['clients', 'profiles'],
        section: 'navigation',
        shortcutHint: 'g c',
      },
      {
        id: 'nav-human-review',
        title: 'Go to Human Review',
        icon: Clock,
        action: () => navigate('/human-review'),
        keywords: ['escalations', 'queue', 'pending'],
        section: 'navigation',
        shortcutHint: 'g r',
      },
      {
        id: 'nav-analytics',
        title: 'Go to Analytics',
        icon: BarChart3,
        action: () => navigate('/analytics'),
        keywords: ['charts', 'metrics', 'reports'],
        section: 'navigation',
        shortcutHint: 'g a',
      },
      {
        id: 'nav-reality',
        title: 'Go to Oracle Reality',
        icon: Globe,
        action: () => navigate('/reality'),
        keywords: ['shipping', 'chokepoints', 'global'],
        section: 'navigation',
        shortcutHint: 'g o',
      },
      {
        id: 'nav-settings',
        title: 'Go to Settings',
        icon: Settings,
        action: () => navigate('/settings'),
        keywords: ['preferences', 'config'],
        section: 'navigation',
        shortcutHint: 'g t',
      },

      // Quick Actions
      {
        id: 'action-refresh',
        title: 'Refresh Data',
        subtitle: 'Fetch latest decisions and signals',
        icon: ArrowRight,
        action: () => {
          queryClient.invalidateQueries();
        },
        keywords: ['reload', 'update', 'sync'],
        section: 'actions',
      },
    ],
    [navigate, queryClient],
  );

  // Build "Ask AI" item when there's a query
  const aiItem: CommandItem | null = useMemo(() => {
    if (!query.trim()) return null;
    return {
      id: 'ai-ask',
      title: `Ask AI: "${query}"`,
      subtitle: 'Open chat with this question',
      icon: Sparkles,
      action: () => {
        // Dispatch event to open chat with pre-filled query
        document.dispatchEvent(new CustomEvent('riskcast:open-chat', { detail: { message: query } }));
      },
      section: 'ai' as const,
    };
  }, [query]);

  // Filter and score items based on query
  const filteredItems = useMemo(() => {
    // No query: show recent + all commands
    if (!query.trim()) {
      return [...recentItems, ...commandItems];
    }

    const lowerQuery = query.toLowerCase();

    // Score each command item
    const scoredItems = commandItems.map((item) => {
      const titleScore = fuzzyScore(item.title, lowerQuery);
      const subtitleScore = item.subtitle ? fuzzyScore(item.subtitle, lowerQuery) * 0.8 : 0;
      const keywordScore = item.keywords
        ? Math.max(...item.keywords.map((k) => fuzzyScore(k, lowerQuery))) * 0.6
        : 0;

      const totalScore = Math.max(titleScore, subtitleScore, keywordScore);

      return { item, score: totalScore };
    });

    // Filter out items with no match and sort by score
    const matchedCommands = scoredItems
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ item }) => item);

    // Combine: data results first, then commands, then AI at the bottom
    const result = [...dataItems, ...matchedCommands];
    if (aiItem) result.push(aiItem);

    // Save search to recents
    if (query.trim().length >= 2) {
      addRecentSearch(query.trim());
    }

    return result;
  }, [query, commandItems, dataItems, recentItems, aiItem]);

  // Group items by section
  const groupedItems = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredItems.forEach((item) => {
      if (!groups[item.section]) groups[item.section] = [];
      groups[item.section].push(item);
    });
    return groups;
  }, [filteredItems]);

  // Dynamic suggestions from command items for empty state
  const suggestions = useMemo(
    () =>
      commandItems
        .filter((item) => item.section === 'navigation')
        .slice(0, 4)
        .map((item) => item.title.replace(/^Go to /, '').toLowerCase()),
    [commandItems],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((i) => Math.min(i + 1, filteredItems.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((i) => Math.max(i - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredItems[selectedIndex]) {
            filteredItems[selectedIndex].action();
            onClose();
          }
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'Tab': {
          const dialog = dialogRef.current;
          if (!dialog) break;
          const focusableEls = dialog.querySelectorAll<HTMLElement>(
            'input, button, [tabindex]:not([tabindex="-1"])',
          );
          if (focusableEls.length === 0) break;
          const first = focusableEls[0];
          const last = focusableEls[focusableEls.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
          break;
        }
      }
    },
    [isOpen, filteredItems, selectedIndex, onClose],
  );

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setInputValue('');
      setQuery('');
      setSelectedIndex(0);
      inputRef.current?.focus();
    }
    return () => clearTimeout(debounceRef.current);
  }, [isOpen]);

  // Add keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  const sectionLabels: Record<string, string> = {
    recent: 'Recent Searches',
    data: 'Search Results',
    navigation: 'Navigation',
    decisions: 'Decisions',
    actions: 'Quick Actions',
    ai: 'AI Assistant',
  };

  let globalIndex = -1;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm backdrop-blur-2xl"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Command Palette */}
      <div
        ref={dialogRef}
        className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2 rounded-xl border bg-background shadow-2xl elevation-3 card-glass"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 border-b border-border/60 px-4 py-4">
          <Search className="h-5 w-5 text-muted-foreground" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Type a command or search..."
            value={inputValue}
            onChange={(e) => {
              const value = e.target.value;
              setInputValue(value);
              clearTimeout(debounceRef.current);
              debounceRef.current = setTimeout(() => setQuery(value), 150);
            }}
            maxLength={200}
            className="flex-1 min-h-[2.5rem] bg-transparent text-base text-lg py-2.5 outline-none placeholder:text-muted-foreground"
            aria-label="Search commands"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded border bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            <span className="text-[10px]">ESC</span>
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-[300px] overflow-y-auto p-2" role="listbox">
          {filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <XCircle className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No results for "{inputValue}"</p>
              <p className="text-xs mt-1">Try searching for:</p>
              <div className="flex flex-wrap justify-center gap-2 mt-2">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInputValue(suggestion);
                      clearTimeout(debounceRef.current);
                      setQuery(suggestion);
                    }}
                    className="px-2 py-1 text-xs bg-muted hover:bg-muted/80 rounded transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            Object.entries(groupedItems).map(([section, items]) => (
              <div key={section} className="mb-2">
                <p className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {sectionLabels[section] || section}
                </p>
                {items.map((item) => {
                  globalIndex++;
                  const isSelected = globalIndex === selectedIndex;
                  const Icon = item.icon;

                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        item.action();
                        onClose();
                      }}
                      className={cn(
                        'w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors',
                        isSelected ? 'bg-accent text-accent-foreground' : 'hover:bg-muted',
                      )}
                      role="option"
                      aria-selected={isSelected}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {highlightMatch(item.title, query)}
                        </p>
                        {item.subtitle && (
                          <p className="text-xs text-muted-foreground truncate">
                            {highlightMatch(item.subtitle, query)}
                          </p>
                        )}
                      </div>
                      {item.shortcutHint && !isSelected && (
                        <span className="hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono text-muted-foreground/60">
                          {item.shortcutHint.split(' ').map((k, i) => (
                            <kbd key={i} className="rounded border border-border bg-muted px-1 py-0.5 text-[9px]">{k}</kbd>
                          ))}
                        </span>
                      )}
                      {isSelected && (
                        <CornerDownLeft className="h-4 w-4 shrink-0 text-muted-foreground" />
                      )}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="rounded border bg-muted px-1.5 py-0.5">↑</kbd>
              <kbd className="rounded border bg-muted px-1.5 py-0.5">↓</kbd>
              <span>Navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="rounded border bg-muted px-1.5 py-0.5">↵</kbd>
              <span>Select</span>
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Command className="h-3 w-3" />
            <span>K to open</span>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * Hook to manage command palette state with Cmd+K shortcut
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}

export default CommandPalette;
