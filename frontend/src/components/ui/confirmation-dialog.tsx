/**
 * ConfirmationDialog — Modal dialog for confirming high-stakes actions.
 *
 * Used before: Accept Decision, Override, Escalate, Approve/Reject Escalation, Dismiss Signal.
 * Supports: focus trapping, Escape to close, backdrop blur, loading state, custom content.
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

export interface ConfirmationDialogProps {
  /** Whether the dialog is open. */
  isOpen: boolean;
  /** Called when the user confirms the action. */
  onConfirm: () => void;
  /** Called when the user cancels (or presses Escape). */
  onCancel: () => void;
  /** Dialog title. */
  title: string;
  /** Dialog description text. */
  description?: string;
  /** Label for the confirm button. Default: "Confirm". */
  confirmLabel?: string;
  /** Label for the cancel button. Default: "Cancel". */
  cancelLabel?: string;
  /** Visual variant controlling confirm button styling. */
  variant?: 'default' | 'warning' | 'danger';
  /** Shows a loading spinner on the confirm button. */
  isLoading?: boolean;
  /** Whether the confirm button should be disabled (e.g. form validation). */
  confirmDisabled?: boolean;
  /** Optional custom content rendered between description and action buttons. */
  children?: ReactNode;
}

const VARIANT_STYLES = {
  default: {
    icon: 'text-accent bg-accent/10 border-accent/20',
    confirm: 'bg-accent hover:bg-accent/90 text-white',
  },
  warning: {
    icon: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    confirm: 'bg-amber-600 hover:bg-amber-500 text-white',
  },
  danger: {
    icon: 'text-red-500 bg-red-500/10 border-red-500/20',
    confirm: 'bg-red-600 hover:bg-red-500 text-white',
  },
} as const;

export function ConfirmationDialog({
  isOpen,
  onConfirm,
  onCancel,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  isLoading = false,
  confirmDisabled = false,
  children,
}: ConfirmationDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);
  const styles = VARIANT_STYLES[variant];

  // Focus trap + Escape handler
  useEffect(() => {
    if (!isOpen) return;

    // Focus the cancel button on open (safer default than confirm for dangerous actions)
    const timer = setTimeout(() => {
      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable && focusable.length > 0) {
        focusable[focusable.length - 1].focus(); // Focus cancel (last button)
      }
    }, 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        if (!isLoading) onCancel();
        return;
      }

      // Trap focus inside dialog
      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isLoading, onCancel]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !isLoading && onCancel()}
          />

          {/* Dialog */}
          <motion.div
            ref={dialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-desc"
            className={cn(
              'relative z-10 w-full max-w-md',
              'bg-card border border-border rounded-xl shadow-2xl',
              'overflow-hidden',
            )}
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={springs.smooth}
          >
            {/* Close button */}
            <button
              onClick={() => !isLoading && onCancel()}
              className="absolute top-3 right-3 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Close dialog"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="p-6">
              {/* Icon + Title */}
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border',
                    styles.icon,
                  )}
                >
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 id="confirm-dialog-title" className="text-lg font-semibold text-foreground">
                    {title}
                  </h2>
                  {description && (
                    <p id="confirm-dialog-desc" className="text-sm text-muted-foreground mt-1">
                      {description}
                    </p>
                  )}
                </div>
              </div>

              {/* Custom content (form fields, selectors, etc.) */}
              {children && <div className="mt-4">{children}</div>}

              {/* Actions */}
              <div className="flex gap-3 mt-6">
                <Button
                  ref={confirmBtnRef}
                  onClick={onConfirm}
                  disabled={isLoading || confirmDisabled}
                  isLoading={isLoading}
                  loadingText="Processing..."
                  className={cn('flex-1', styles.confirm)}
                >
                  {confirmLabel}
                </Button>
                <Button
                  variant="outline"
                  onClick={onCancel}
                  disabled={isLoading}
                  className="flex-1"
                >
                  {cancelLabel}
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
