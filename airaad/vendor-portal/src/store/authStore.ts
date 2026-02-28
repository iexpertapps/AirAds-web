import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface VendorUser {
  id: string;
  phone: string;
  full_name: string;
  vendor_id: string | null;
  activation_stage: 'UNCLAIMED' | 'CLAIM_PENDING' | 'CLAIMED' | 'PROFILE_COMPLETE';
  subscription_level: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
}

interface AuthState {
  user: VendorUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  login: (user: VendorUser, access: string, refresh: string) => void;
  logout: () => void;
  setUser: (user: VendorUser) => void;
  setAccessToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: (user, access, refresh) => {
        set({ user, accessToken: access, refreshToken: refresh, isAuthenticated: true });
      },

      logout: () => {
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      setUser: (user) => {
        set({ user });
      },

      setAccessToken: (token) => {
        set({ accessToken: token });
      },
    }),
    {
      name: 'airad-vendor-auth',
      storage: {
        getItem: (name) => {
          const str = sessionStorage.getItem(name);
          return str ? JSON.parse(str) : null;
        },
        setItem: (name, value) => {
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          sessionStorage.removeItem(name);
        },
      },
    },
  ),
);

export type { VendorUser };
