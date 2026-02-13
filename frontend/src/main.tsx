import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nProvider } from '@/lib/i18n/provider';
import { ToastProvider } from '@/components/ui/toast';
import { ThemeProvider } from '@/components/ui/theme-provider';
import { UserProvider } from '@/contexts/user-context';
import { PlanProvider } from '@/contexts/plan-context';
import { AuthProvider } from '@/lib/auth';
import { router } from './router';
import './index.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
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
