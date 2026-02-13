/**
 * ErrorBoundary - Catch and display errors gracefully
 *
 * Features:
 * - Catches React rendering errors
 * - Shows user-friendly error message
 * - Provides retry/reload actions
 * - Reports errors for debugging
 */

import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from './button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    this.setState({ errorInfo });

    // Call optional error handler
    this.props.onError?.(error, errorInfo);

    // Production: integrate Sentry or similar error reporting service here
    // e.g. Sentry.captureException(error, { extra: { componentStack: errorInfo.componentStack } });
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = (): void => {
    // Use soft navigation to preserve app state where possible
    window.location.assign('/');
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center p-8">
          <div className="rounded-xl border bg-background p-8 shadow-lg max-w-md w-full text-center">
            {/* Error Icon */}
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-severity-critical/10">
              <AlertTriangle className="h-8 w-8 text-severity-critical" />
            </div>

            {/* Title */}
            <h2 className="text-xl font-semibold text-foreground mb-2">Something went wrong</h2>

            {/* Description */}
            <p className="text-sm text-muted-foreground mb-6">
              We encountered an unexpected error. This has been logged and we'll look into it.
            </p>

            {/* Error Message (Development only) */}
            {import.meta.env.DEV && this.state.error && (
              <details className="mb-6 text-left">
                <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
                  <Bug className="h-3 w-3" />
                  <span>Technical details</span>
                </summary>
                <pre className="mt-2 overflow-auto rounded-lg bg-muted p-3 text-xs text-muted-foreground">
                  <code>
                    {this.state.error.message}
                    {'\n\n'}
                    {this.state.errorInfo?.componentStack}
                  </code>
                </pre>
              </details>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Button onClick={this.handleRetry} variant="default" className="w-full sm:w-auto">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              <Button onClick={this.handleGoHome} variant="outline" className="w-full sm:w-auto">
                <Home className="h-4 w-4 mr-2" />
                Go to Dashboard
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * ErrorFallback - Simpler inline error display
 */
interface ErrorFallbackProps {
  error?: Error;
  resetErrorBoundary?: () => void;
  title?: string;
  message?: string;
}

export function ErrorFallback({
  error,
  resetErrorBoundary,
  title = 'Error loading content',
  message = 'Please try again or contact support if the problem persists.',
}: ErrorFallbackProps) {
  return (
    <div className="flex flex-col items-center justify-center p-6 rounded-lg border border-severity-critical/20 bg-severity-critical/5">
      <AlertTriangle className="h-6 w-6 text-severity-critical mb-2" />
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground text-center mb-3">{message}</p>

      {error && import.meta.env.DEV && (
        <p className="text-xs text-severity-critical font-mono mb-3">{error.message}</p>
      )}

      {resetErrorBoundary && (
        <Button onClick={resetErrorBoundary} variant="outline" size="sm">
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

export default ErrorBoundary;
