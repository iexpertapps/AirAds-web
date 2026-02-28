import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

const LandingPage = lazy(() => import('@/pages/landing/LandingPage'));
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'));
const DiscoveryPage = lazy(() => import('@/pages/discovery/DiscoveryPage'));
const VendorProfilePage = lazy(() => import('@/pages/vendor/VendorProfilePage'));
const DealsPage = lazy(() => import('@/pages/deals/DealsPage'));
const ReelsPage = lazy(() => import('@/pages/reels/ReelsPage'));
const NavigationPage = lazy(() => import('@/pages/navigation/NavigationPage'));
const PreferencesPage = lazy(() => import('@/pages/preferences/PreferencesPage'));
const NotFoundPage = lazy(() => import('@/pages/error/NotFoundPage'));

function PublicOnlyRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/discover" replace />;
  return <Outlet />;
}

// Kept for future auth-gated routes
function AuthOnlyRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}
void AuthOnlyRoute;

const Loading = () => (
  <div className="loading-fallback">
    <img src="/airad_icon.png" alt="AirAd" className="loading-fallback-logo" />
    Loading…
  </div>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <Suspense fallback={<Loading />}>
        <LandingPage />
      </Suspense>
    ),
  },
  {
    element: <PublicOnlyRoute />,
    children: [
      {
        path: '/login',
        element: (
          <Suspense fallback={<Loading />}>
            <LoginPage />
          </Suspense>
        ),
      },
      {
        path: '/register',
        element: (
          <Suspense fallback={<Loading />}>
            <RegisterPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '/discover',
    element: (
      <Suspense fallback={<Loading />}>
        <DiscoveryPage />
      </Suspense>
    ),
  },
  {
    path: '/vendor/:vendorId',
    element: (
      <Suspense fallback={<Loading />}>
        <VendorProfilePage />
      </Suspense>
    ),
  },
  {
    path: '/deals',
    element: (
      <Suspense fallback={<Loading />}>
        <DealsPage />
      </Suspense>
    ),
  },
  {
    path: '/reels',
    element: (
      <Suspense fallback={<Loading />}>
        <ReelsPage />
      </Suspense>
    ),
  },
  {
    path: '/navigate/:vendorId',
    element: (
      <Suspense fallback={<Loading />}>
        <NavigationPage />
      </Suspense>
    ),
  },
  {
    path: '/preferences',
    element: (
      <Suspense fallback={<Loading />}>
        <PreferencesPage />
      </Suspense>
    ),
  },
  {
    path: '*',
    element: (
      <Suspense fallback={<Loading />}>
        <NotFoundPage />
      </Suspense>
    ),
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
