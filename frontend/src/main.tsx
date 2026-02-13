import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';
import { I18nProvider } from '@/lib/i18n/provider';
import { ToastProvider } from '@/components/ui/toast';
import { ThemeProvider } from '@/components/ui/theme-provider';
import { UserProvider } from '@/contexts/user-context';
import { PlanProvider } from '@/contexts/plan-context';
import { AuthProvider } from '@/lib/auth';
import { router } from './router';
import './index.css';

// ─── Global Error Handlers ──────────────────────────────────
// Catch JS runtime errors that escape React's ErrorBoundary
// (e.g. async errors, third-party script failures, event handler throws)

window.addEventListener('error', (event) => {
  // Ignore ResizeObserver loop errors (benign, caused by rapid layout changes)
  if (event.message?.includes('ResizeObserver')) return;

  console.error('[RiskCast] Uncaught error:', {
    message: event.message,
    filename: event.filename,
    line: event.lineno,
    col: event.colno,
  });

  // Production: forward to Sentry/Datadog here
  // e.g. Sentry.captureException(event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('[RiskCast] Unhandled promise rejection:', event.reason);

  // Prevent default browser logging to keep console clean in production
  // (we already logged it above with structured context)
  if (import.meta.env.PROD) {
    event.preventDefault();
  }

  // Production: forward to Sentry/Datadog here
  // e.g. Sentry.captureException(event.reason);
});

// Create a client — smart retry: don't retry when backend is offline
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: (failureCount, error) => {
        // Don't retry if backend is offline (status 0) or server error (5xx)
        if (error instanceof ApiError && (error.status === 0 || error.status >= 500)) {
          return false;
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <ThemeProvider>
          <AuthProvider>
            <PlanProvider>
              <UserProvider>
                  <ToastProvider>
                  <RouterProvider router={router} />
                </ToastProvider>
              </UserProvider>
            </PlanProvider>
          </AuthProvider>
        </ThemeProvider>
      </I18nProvider>
    </QueryClientProvider>
  </StrictMode>,
);
