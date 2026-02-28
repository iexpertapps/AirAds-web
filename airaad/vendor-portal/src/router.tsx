import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { LandingLayout } from '@/layouts/LandingLayout';
import { PortalLayout } from '@/layouts/PortalLayout';
import { useAuthStore } from '@/store/authStore';

const LandingPage = lazy(() => import('@/pages/landing/LandingPage'));
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const VerifyOTPPage = lazy(() => import('@/pages/auth/VerifyOTPPage'));
const ClaimSearchPage = lazy(() => import('@/pages/onboarding/ClaimSearchPage'));
const ClaimVerifyPage = lazy(() => import('@/pages/onboarding/ClaimVerifyPage'));
const ProfileSetupPage = lazy(() => import('@/pages/onboarding/ProfileSetupPage'));
const WelcomePage = lazy(() => import('@/pages/onboarding/WelcomePage'));
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'));
const ProfileEditPage = lazy(() => import('@/pages/profile/ProfileEditPage'));
const DiscountsPage = lazy(() => import('@/pages/discounts/DiscountsPage'));
const ReelsPage = lazy(() => import('@/pages/reels/ReelsPage'));
const AnalyticsPage = lazy(() => import('@/pages/analytics/AnalyticsPage'));
const VoiceBotPage = lazy(() => import('@/pages/voicebot/VoiceBotPage'));
const SubscriptionPage = lazy(() => import('@/pages/subscription/SubscriptionPage'));
const NotFoundPage = lazy(() => import('@/pages/error/NotFoundPage'));

function PublicOnlyRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  if (isAuthenticated && user?.vendor_id) {
    return <Navigate to="/portal/dashboard" replace />;
  }
  if (isAuthenticated && !user?.vendor_id) {
    return <Navigate to="/onboarding/search" replace />;
  }
  return <Outlet />;
}

function PortalRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!user?.vendor_id) return <Navigate to="/onboarding/search" replace />;
  return <Outlet />;
}

function OnboardingRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (user?.vendor_id && user.activation_stage === 'PROFILE_COMPLETE') {
    return <Navigate to="/portal/dashboard" replace />;
  }
  return <Outlet />;
}

const Loading = () => (
  <div className="loading-fallback">
    <img src="/airad_icon.png" alt="AirAd" className="loading-fallback-logo" />
    Loading…
  </div>
);

export const router = createBrowserRouter([
  {
    element: <LandingLayout />,
    children: [
      {
        path: '/',
        element: (
          <Suspense fallback={<Loading />}>
            <LandingPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <Suspense fallback={<Loading />}><LoginPage /></Suspense> },
      { path: '/verify', element: <Suspense fallback={<Loading />}><VerifyOTPPage /></Suspense> },
    ],
  },
  {
    element: <OnboardingRoute />,
    children: [
      { path: '/onboarding/search', element: <Suspense fallback={<Loading />}><ClaimSearchPage /></Suspense> },
      { path: '/onboarding/verify/:vendorId', element: <Suspense fallback={<Loading />}><ClaimVerifyPage /></Suspense> },
      { path: '/onboarding/setup', element: <Suspense fallback={<Loading />}><ProfileSetupPage /></Suspense> },
      { path: '/onboarding/welcome', element: <Suspense fallback={<Loading />}><WelcomePage /></Suspense> },
    ],
  },
  {
    element: <PortalRoute />,
    children: [
      {
        element: <PortalLayout />,
        children: [
          { path: '/portal/dashboard', element: <Suspense fallback={<Loading />}><DashboardPage /></Suspense> },
          { path: '/portal/profile', element: <Suspense fallback={<Loading />}><ProfileEditPage /></Suspense> },
          { path: '/portal/discounts', element: <Suspense fallback={<Loading />}><DiscountsPage /></Suspense> },
          { path: '/portal/reels', element: <Suspense fallback={<Loading />}><ReelsPage /></Suspense> },
          { path: '/portal/analytics', element: <Suspense fallback={<Loading />}><AnalyticsPage /></Suspense> },
          { path: '/portal/voice-bot', element: <Suspense fallback={<Loading />}><VoiceBotPage /></Suspense> },
          { path: '/portal/subscription', element: <Suspense fallback={<Loading />}><SubscriptionPage /></Suspense> },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Suspense fallback={<Loading />}><NotFoundPage /></Suspense>,
  },
], {
  future: {
    v7_fetcherPersist: true,
    v7_normalizeFormMethod: true,
    v7_partialHydration: true,
    v7_relativeSplatPath: true,
    v7_skipActionErrorRevalidation: true,
  },
});
