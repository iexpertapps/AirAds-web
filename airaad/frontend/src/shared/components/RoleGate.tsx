import type { Role } from '@/features/auth/store/authStore';
import { useUser } from '@/features/auth/store/authStore';

export function RoleGate({
  allowedRoles,
  fallback = null,
  children,
}: {
  allowedRoles: Role[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}) {
  const user = useUser();
  if (!user || !allowedRoles.includes(user.role)) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
