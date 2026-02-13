/**
 * ErrorState — Displays a calm, professional error message with retry.
 * Used when API calls fail or data cannot be loaded.
 */

import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springs } from '@/lib/animations';

interface ErrorStateProps {
  /** The error object. Stack traces are NOT shown to users. */
  error?: Error | unknown;
  /** Called when user clicks "Retry". */
  onRetry?: () => void;
  /** Custom title. Default: "Something went wrong". */
  title?: string;
  /** Custom description. */
  description?: string;
  /** Inline (within page) or fullPage. */
  variant?: 'inline' | 'fullPage';
}

export function ErrorState({
  error,
  onRetry,
  title = 'Something went wrong',
  description,
  variant = 'inline',
}: ErrorStateProps) {
  const errorMessage =
    description ??
    (error instanceof Error ? error.message : 'An unexpected error occurred. Please try again.');

  if (variant === 'fullPage') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-4">
        <ErrorContent title={title} message={errorMessage} onRetry={onRetry} />
      </div>
    );
  }

  return (
    <motion.div
      className="rounded-xl bg-card border border-border p-12 shadow-sm"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={springs.smooth}
    >
      <ErrorContent title={title} message={errorMessage} onRetry={onRetry} />
    </motion.div>
  );
}

function ErrorContent({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center max-w-md mx-auto">
      <div className={cn('p-3 rounded-lg bg-error/10 border border-error/20 mb-4')}>
        <AlertTriangle className="h-8 w-8 text-error" />
      </div>
      <p className="text-base font-semibold text-foreground mb-1">{title}</p>
      <p className="text-xs text-muted-foreground font-mono mb-4">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} className="gap-2">
          <RefreshCw className="h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
