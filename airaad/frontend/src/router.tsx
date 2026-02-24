/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useUser, useIsAuthenticated, useIsHydrated } from '@/features/auth/store/authStore';
import type { Role } from '@/features/auth/store/authStore';
import { useUIStore } from '@/shared/store/uiStore';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';

const LoginPage = lazy(() => import('@/features/auth/components/LoginPage'));
const PlatformHealthPage = lazy(() => import('@/features/dashboard/components/PlatformHealthPage'));
const GeoPage = lazy(() => import('@/features/geo/components/GeoPage'));
const TagsPage = lazy(() => import('@/features/tags/components/TagsPage'));
const VendorListPage = lazy(() => import('@/features/vendors/components/VendorListPage'));
const VendorDetailPage = lazy(() => import('@/features/vendors/components/VendorDetailPage'));
const ImportsPage = lazy(() => import('@/features/imports/components/ImportsPage'));
const FieldOpsPage = lazy(() => import('@/features/field-ops/components/FieldOpsPage'));
const QAPage = lazy(() => import('@/features/qa/components/QAPage'));
const AuditLogPage = lazy(() => import('@/features/audit/components/AuditLogPage'));
const UsersPage = lazy(() => import('@/features/system/components/UsersPage'));
const GovernancePage = lazy(() => import('@/features/governance/components/GovernancePage'));
const NotFoundPage = lazy(() => import('@/features/auth/components/NotFoundPage'));

function RequireRole({ allowedRoles }: { allowedRoles: Role[] }) {
  const user = useUser();
  if (!user || !allowedRoles.includes(user.role)) {
    useUIStore.getState().addToast({ type: 'error', message: 'You do not have permission to access this page.' });
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

function ProtectedRoute() {
  const isHydrated = useIsHydrated();
  const isAuthenticated = useIsAuthenticated();
  const location = useLocation();

  if (!isHydrated) {
    return <SkeletonTable />;
  }

  if (!isAuthenticated) {
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  return (
    <Suspense fallback={<SkeletonTable />}>
      <Outlet />
    </Suspense>
  );
}

function PublicOnlyRoute() {
  const isHydrated = useIsHydrated();
  const isAuthenticated = useIsAuthenticated();

  if (!isHydrated) {
    return <SkeletonTable />;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return (
    <Suspense fallback={<SkeletonTable />}>
      <Outlet />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/', element: <PlatformHealthPage /> },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY']} />,
        children: [{ path: '/geo', element: <GeoPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'DATA_QUALITY_ANALYST']} />,
        children: [{ path: '/tags', element: <TagsPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER', 'SUPPORT']} />,
        children: [{ path: '/vendors', element: <VendorListPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER', 'SUPPORT']} />,
        children: [{ path: '/vendors/:id', element: <VendorDetailPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'OPERATIONS_MANAGER']} />,
        children: [{ path: '/imports', element: <ImportsPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'FIELD_AGENT']} />,
        children: [{ path: '/field-ops', element: <FieldOpsPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER']} />,
        children: [{ path: '/qa', element: <QAPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'ANALYST', 'OPERATIONS_MANAGER']} />,
        children: [{ path: '/system/audit', element: <AuditLogPage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN', 'OPERATIONS_MANAGER', 'CONTENT_MODERATOR']} />,
        children: [{ path: '/governance', element: <GovernancePage /> }],
      },
      {
        element: <RequireRole allowedRoles={['SUPER_ADMIN']} />,
        children: [{ path: '/system/users', element: <UsersPage /> }],
      },
    ],
  },
  {
    path: '*',
    element: (
      <Suspense fallback={<SkeletonTable />}>
        <NotFoundPage />
      </Suspense>
    ),
  },
]);
