import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CustomerUser } from '@/types/api';

interface AuthState {
  user: CustomerUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  guestToken: string | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  login: (user: CustomerUser, access: string, refresh: string) => void;
  logout: () => void;
  setUser: (user: CustomerUser) => void;
  setAccessToken: (token: string) => void;
  setGuestToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      guestToken: null,
      isAuthenticated: false,
      isGuest: true,

      login: (user, access, refresh) => {
        localStorage.removeItem('airad-guest-token');
        set({
          user,
          accessToken: access,
          refreshToken: refresh,
          isAuthenticated: true,
          isGuest: false,
        });
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          isGuest: true,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      setAccessToken: (token) => {
        set({ accessToken: token });
      },

      setGuestToken: (token) => {
        localStorage.setItem('airad-guest-token', token);
        set({ guestToken: token, isGuest: true });
      },
    }),
    {
      name: 'airad-user-auth',
    },
  ),
);
