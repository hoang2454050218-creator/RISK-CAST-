/**
 * Shared UI states: Loading, Empty, Error, Offline.
 * Used across all components for consistent UX.
 *
 * All text goes through i18n — no hardcoded language strings.
 * All colors use semantic CSS-variable-backed tokens.
 */

import { AlertCircle, Inbox, Loader2, RefreshCw, WifiOff } from 'lucide-react';
import { useTranslations } from '@/lib/i18n';

// ── Loading State ────────────────────────────────────────────────────────

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message, className = '' }: LoadingStateProps) {
  const t = useTranslations();
  return (
    <div className={`flex flex-col items-center justify-center py-12 ${className}`}>
      <Loader2 className="h-8 w-8 animate-spin text-accent mb-3" />
      <p className="text-sm text-muted-foreground font-mono">{message || t.common.loading}</p>
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: typeof Inbox;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-16 px-4 ${className}`}>
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-muted-foreground text-center max-w-xs">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 text-xs font-medium text-accent hover:text-accent-hover transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// ── Error State ──────────────────────────────────────────────────────────

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  variant?: 'inline' | 'full';
  className?: string;
  title?: string;
  error?: unknown;
  description?: string;
}

export function ErrorState({
  message,
  onRetry,
  variant = 'full',
  className = '',
  title,
  error,
  description,
}: ErrorStateProps) {
  const t = useTranslations();
  const displayMessage = message
    || description
    || (error instanceof Error ? error.message : null)
    || t.common.errorDescription;
  const displayTitle = title || t.common.errorTitle;

  if (variant === 'inline') {
    return (
      <div role="alert" className={`flex items-center gap-2 rounded-lg border border-error/20 bg-error-light px-4 py-3 ${className}`}>
        <AlertCircle className="h-4 w-4 text-error shrink-0" />
        <span className="text-sm text-error flex-1">{displayMessage}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="text-xs font-medium text-error hover:text-error/80 transition-colors"
          >
            {t.common.retry}
          </button>
        )}
      </div>
    );
  }

  return (
    <div role="alert" className={`flex flex-col items-center justify-center py-16 px-4 ${className}`}>
      <div className="rounded-full bg-error-light p-4 mb-4">
        <AlertCircle className="h-8 w-8 text-error" />
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{displayTitle}</h3>
      <p className="text-xs text-muted-foreground text-center max-w-xs mb-4">{displayMessage}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent-hover transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" /> {t.common.retry}
        </button>
      )}
    </div>
  );
}

// ── Offline State ────────────────────────────────────────────────────────

export function OfflineState({ className = '' }: { className?: string }) {
  const t = useTranslations();
  return (
    <div role="alert" className={`flex items-center gap-2 rounded-lg border border-warning/20 bg-warning-light px-4 py-3 ${className}`}>
      <WifiOff className="h-4 w-4 text-warning shrink-0" />
      <span className="text-sm text-warning">
        {t.common.offline}
      </span>
    </div>
  );
}
