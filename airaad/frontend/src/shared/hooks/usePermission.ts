import { useUser } from '@/features/auth/store/authStore';
import type { Role } from '@/features/auth/store/authStore';

export function usePermission(allowedRoles: Role[]): boolean {
  const user = useUser();
  return user !== null && allowedRoles.includes(user.role);
}
