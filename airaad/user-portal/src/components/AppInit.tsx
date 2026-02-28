import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import { getGuestToken } from '@/api/auth';
import { startSession } from '@/api/analytics';

export function AppInit() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const guestToken = useAuthStore((s) => s.guestToken);
  const setGuestToken = useAuthStore((s) => s.setGuestToken);

  useEffect(() => {
    if (!isAuthenticated && !guestToken) {
      getGuestToken()
        .then((res) => {
          if (res.success && res.data.guest_token) {
            setGuestToken(res.data.guest_token);
          }
        })
        .catch(() => {
          // silent — guest can still browse without token
        });
    }
  }, [isAuthenticated, guestToken, setGuestToken]);

  useEffect(() => {
    startSession();
  }, []);

  return null;
}
