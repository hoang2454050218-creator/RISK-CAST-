/**
 * FilterDropdown — Shared dropdown filter component used across list pages.
 *
 * Replaces local reimplementations in:
 *   - decisions/page.tsx (with keyboard navigation)
 *   - signals/page.tsx (without keyboard navigation)
 *
 * This unified version includes full keyboard navigation and ARIA roles.
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Types ─────────────────────────────────────────────────────

export interface FilterOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

export interface FilterDropdownProps {
  /** Label displayed before the selected value (e.g. "Status"). */
  label: string;
  /** Currently selected value. */
  value: string;
  /** List of selectable options. */
  options: FilterOption[];
  /** Callback fired when an option is selected. */
  onChange: (value: string) => void;
  /** Accent color for the active state. Default: 'blue'. */
  accentColor?: 'blue' | 'amber' | 'red' | 'emerald' | 'purple' | 'accent';
  /** Additional classes on the root element. */
  className?: string;
}

// ─── Accent color mappings ─────────────────────────────────────

const ACCENT_MAP = {
  blue: {
    trigger: 'bg-info/10 text-info border-info/40',
    selected: 'bg-info/10 text-info',
  },
  amber: {
    trigger: 'bg-warning/10 text-warning border-warning/40',
    selected: 'bg-warning/10 text-warning',
  },
  red: {
    trigger: 'bg-error/10 text-error border-error/40',
    selected: 'bg-error/10 text-error',
  },
  emerald: {
    trigger: 'bg-success/10 text-success border-success/40',
    selected: 'bg-success/10 text-success',
  },
  purple: {
    trigger: 'bg-action-reroute/10 text-action-reroute border-action-reroute/40',
    selected: 'bg-action-reroute/10 text-action-reroute',
  },
  accent: {
    trigger: 'bg-accent/10 text-accent border-accent/40',
    selected: 'bg-accent/10 text-accent',
  },
} as const;

// ─── Component ─────────────────────────────────────────────────

export function FilterDropdown({
  label,
  value,
  options,
  onChange,
  accentColor = 'blue',
  className,
}: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value);
  const isActive = value !== 'ALL' && value !== options[0]?.value;
  const colors = ACCENT_MAP[accentColor];

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev + 1) % options.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) => (prev - 1 + options.length) % options.length);
          break;
        case 'Enter':
          e.preventDefault();
          onChange(options[highlightedIndex].value);
          setIsOpen(false);
          triggerRef.current?.focus();
          break;
        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          triggerRef.current?.focus();
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, highlightedIndex, options, onChange]);

  // Sync highlighted index to current value when opening
  useEffect(() => {
    if (isOpen) {
      const idx = options.findIndex((o) => o.value === value);
      setHighlightedIndex(idx >= 0 ? idx : 0);
    }
  }, [isOpen, value, options]);

  return (
    <div className={cn('relative', className)}>
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={cn(
          'flex items-center gap-2 px-3 py-2.5 sm:px-2.5 sm:py-1.5 min-h-[44px] sm:min-h-0 text-xs font-mono rounded-md border transition-all',
          isActive
            ? colors.trigger
            : 'bg-muted/50 text-muted-foreground border-border hover:border-border',
        )}
      >
        <span className="text-muted-foreground">{label}:</span>
        <span>{selectedOption?.label}</span>
        <ChevronDown className={cn('h-3 w-3 transition-transform', isOpen && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Click-outside backdrop */}
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              ref={listRef}
              role="listbox"
              aria-label={`${label} filter`}
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
              className="absolute left-0 top-full z-50 mt-1 w-44 rounded-md border border-border bg-card shadow-xl overflow-hidden"
            >
              <div className="p-1">
                {options.map((option, index) => (
                  <button
                    key={option.value}
                    role="option"
                    aria-selected={option.value === value}
                    onClick={() => {
                      onChange(option.value);
                      setIsOpen(false);
                    }}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={cn(
                      'flex w-full items-center gap-2 px-2.5 py-3 sm:py-2 min-h-[44px] sm:min-h-0 text-xs font-mono rounded transition-colors',
                      highlightedIndex === index && 'bg-muted',
                      option.value === value
                        ? colors.selected
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {option.value === value && <Check className="h-3 w-3" />}
                    <span className={option.value !== value ? 'ml-5' : ''}>
                      {option.icon}
                      {option.label}
                    </span>
                  </button>
                ))}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
