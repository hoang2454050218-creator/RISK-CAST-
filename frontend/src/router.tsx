import { createBrowserRouter } from 'react-router';
import { AppLayout } from '@/components/domain/layout';
import { ProtectedRoute } from '@/lib/auth';

// Lazy load pages for better performance
import { lazy, Suspense } from 'react';

const LandingPage = lazy(() => import('@/app/home/page'));
const LoginPage = lazy(() => import('@/app/auth/login/page'));
const RegisterPage = lazy(() => import('@/app/auth/register/page'));
const DashboardPage = lazy(() => import('@/app/dashboard/page'));
const DecisionsPage = lazy(() => import('@/app/decisions/page'));
const DecisionDetailPage = lazy(() => import('@/app/decisions/[id]/page'));
const SignalsPage = lazy(() => import('@/app/signals/page'));
const SignalDetailPage = lazy(() => import('@/app/signals/[id]/page'));
const CustomersPage = lazy(() => import('@/app/customers/page'));
const CustomerDetailPage = lazy(() => import('@/app/customers/[id]/page'));
const HumanReviewPage = lazy(() => import('@/app/human-review/page'));
const EscalationDetailPage = lazy(() => import('@/app/human-review/[id]/page'));
const AnalyticsPage = lazy(() => import('@/app/analytics/page'));
const AuditPage = lazy(() => import('@/app/audit/page'));
const RealityPage = lazy(() => import('@/app/reality/page'));
const SettingsPage = lazy(() => import('@/app/settings/page'));
const OnboardingPage = lazy(() => import('@/app/onboarding/page'));
const UnauthorizedPage = lazy(() => import('@/app/unauthorized/page'));
const NotFoundPage = lazy(() => import('@/app/not-found/page'));

// Loading component
function PageLoader() {
  return (
    <div className="flex h-[50vh] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent" />
        <p className="text-sm text-muted-foreground font-mono">Loading...</p>
      </div>
    </div>
  );
}

// Wrap lazy components with Suspense
function withSuspense(Component: React.ComponentType) {
  return function SuspenseWrapper() {
    return (
      <Suspense fallback={<PageLoader />}>
        <Component />
      </Suspense>
    );
  };
}

export const router = createBrowserRouter([
  // ─── Public routes ──────────────────────────────────────
  {
    path: '/',
    element: (
      <Suspense fallback={<PageLoader />}>
        <LandingPage />
      </Suspense>
    ),
  },
  {
    path: '/auth/login',
    element: (
      <Suspense fallback={<PageLoader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: '/auth/register',
    element: (
      <Suspense fallback={<PageLoader />}>
        <RegisterPage />
      </Suspense>
    ),
  },

  // ─── Protected app routes ─────────────────────────────
  {
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: '/dashboard',
        element: withSuspense(DashboardPage)(),
      },
      {
        path: '/decisions',
        children: [
          {
            index: true,
            element: withSuspense(DecisionsPage)(),
          },
          {
            path: ':id',
            element: withSuspense(DecisionDetailPage)(),
          },
        ],
      },
      {
        path: '/signals',
        children: [
          {
            index: true,
            element: withSuspense(SignalsPage)(),
          },
          {
            path: ':id',
            element: withSuspense(SignalDetailPage)(),
          },
        ],
      },
      {
        path: '/customers',
        children: [
          {
            index: true,
            element: withSuspense(CustomersPage)(),
          },
          {
            path: ':id',
            element: withSuspense(CustomerDetailPage)(),
          },
        ],
      },
      {
        path: '/human-review',
        children: [
          {
            index: true,
            element: withSuspense(HumanReviewPage)(),
          },
          {
            path: ':id',
            element: withSuspense(EscalationDetailPage)(),
          },
        ],
      },
      {
        path: '/analytics',
        element: withSuspense(AnalyticsPage)(),
      },
      {
        path: '/audit',
        element: withSuspense(AuditPage)(),
      },
      {
        path: '/reality',
        element: withSuspense(RealityPage)(),
      },
      // Chat is now a floating widget (ChatWidget) on every page — no dedicated route needed
      {
        path: '/onboarding',
        element: withSuspense(OnboardingPage)(),
      },
      {
        path: '/settings',
        element: withSuspense(SettingsPage)(),
      },
      {
        path: '/unauthorized',
        element: withSuspense(UnauthorizedPage)(),
      },
    ],
  },

  // ─── 404 catch-all ────────────────────────────────────
  {
    path: '*',
    element: (
      <Suspense fallback={<PageLoader />}>
        <NotFoundPage />
      </Suspense>
    ),
  },
]);
