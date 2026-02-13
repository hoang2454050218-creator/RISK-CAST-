/**
 * ActiveFilterChip — Shows an active filter value with a remove button.
 *
 * Extracted from decisions/page.tsx for reuse across all filter UIs.
 */

import { motion } from 'framer-motion';
import { X } from 'lucide-react';

export interface ActiveFilterChipProps {
  /** Display label for the active filter. */
  label: string;
  /** Callback fired when the chip's remove button is clicked. */
  onRemove: () => void;
}

export function ActiveFilterChip({ label, onRemove }: ActiveFilterChipProps) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      className="inline-flex items-center gap-1.5 pl-3 pr-1 py-1.5 sm:px-2 sm:py-1 text-[11px] sm:text-[10px] font-mono rounded bg-muted text-foreground border border-border min-h-[44px] sm:min-h-0"
    >
      {label}
      <button
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
        className="rounded hover:bg-muted-foreground/10 p-2 sm:p-0.5 -mr-0.5 sm:mr-0"
      >
        <X className="h-3 w-3 sm:h-2.5 sm:w-2.5" />
      </button>
    </motion.span>
  );
}
