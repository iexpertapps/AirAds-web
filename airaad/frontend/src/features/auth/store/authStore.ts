import { create } from 'zustand';
import { subscribeWithSelector, persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

export type Role =
  | 'SUPER_ADMIN'
  | 'CITY_MANAGER'
  | 'DATA_ENTRY'
  | 'QA_REVIEWER'
  | 'FIELD_AGENT'
  | 'ANALYST'
  | 'SUPPORT'
  | 'OPERATIONS_MANAGER'
  | 'CONTENT_MODERATOR'
  | 'DATA_QUALITY_ANALYST'
  | 'ANALYTICS_OBSERVER';

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  full_name?: string;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  _hasHydrated: boolean;
  _isInitialized: boolean;
  login: (tokens: { access: string; refresh: string }, user: AuthUser) => void;
  logout: () => void;
  setAccessToken: (token: string) => void;
  setHasHydrated: (value: boolean) => void;
  setInitialized: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  subscribeWithSelector(
    persist(
      immer((set) => ({
        user: null,
        accessToken: null,
        refreshToken: null,
        _hasHydrated: false,
        _isInitialized: false,

        login: (tokens, user) => {
          set((state) => {
            state.user = user;
            state.accessToken = tokens.access;
            state.refreshToken = tokens.refresh;
            state._isInitialized = true;
          });
        },

        logout: () => {
          set((state) => {
            state.user = null;
            state.accessToken = null;
            state.refreshToken = null;
            state._isInitialized = false;
          });
        },

        setAccessToken: (token) => {
          set((state) => {
            state.accessToken = token;
          });
        },

        setHasHydrated: (value) => {
          set((state) => {
            state._hasHydrated = value;
          });
        },

        setInitialized: (value) => {
          set((state) => {
            state._isInitialized = value;
          });
        },
      })),
      {
        name: 'airaad-auth',
        storage: createJSONStorage(() => sessionStorage),
        // Persist user, accessToken, and refreshToken to sessionStorage.
        // accessToken is short-lived (15 min) — the Axios response interceptor
        // handles 401s by refreshing via refreshToken if it expires.
        partialize: (state) => ({
          user: state.user,
          accessToken: state.accessToken,
          refreshToken: state.refreshToken,
        }),
        onRehydrateStorage: () => (state) => {
          if (!state) return;
          state.setHasHydrated(true);
          if (state.user && state.refreshToken) {
            state.setInitialized(true);
          }
        },
      },
    ),
  ),
);

// React Hooks for components
export const useUser = () => useAuthStore((s) => s.user);
export const useAccessToken = () => useAuthStore((s) => s.accessToken);
export const useRefreshToken = () => useAuthStore((s) => s.refreshToken);
export const useIsAuthenticated = () => useAuthStore((s) => s._isInitialized && s.user !== null);
export const useIsHydrated = () => useAuthStore((s) => s._hasHydrated);
export const useUserRole = () => useAuthStore((s) => s.user?.role);

// Unified state access layer
export class AuthStateManager {

  // Non-reactive access for interceptors and utilities
  static getCurrentUser() {
    return useAuthStore.getState().user;
  }

  static getCurrentAccessToken() {
    return useAuthStore.getState().accessToken;
  }

  static getCurrentRefreshToken() {
    return useAuthStore.getState().refreshToken;
  }

  static isAuthenticated() {
    const state = useAuthStore.getState();
    return state._isInitialized && state.user !== null;
  }

  static isHydrated() {
    return useAuthStore.getState()._hasHydrated;
  }

  // State mutations
  static login(tokens: { access: string; refresh: string }, user: AuthUser) {
    useAuthStore.getState().login(tokens, user);
  }

  static logout() {
    useAuthStore.getState().logout();
  }

  static setAccessToken(token: string) {
    useAuthStore.getState().setAccessToken(token);
  }

  // State synchronization utilities
  static waitForHydration(timeout = 5000): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isHydrated()) {
        resolve();
        return;
      }

      const unsubscribe = useAuthStore.subscribe(
        (state) => state._hasHydrated,
        (hasHydrated) => {
          if (hasHydrated) {
            unsubscribe();
            resolve();
          }
        }
      );

      setTimeout(() => {
        unsubscribe();
        reject(new Error('Auth hydration timeout'));
      }, timeout);
    });
  }

  static waitForAuthentication(timeout = 5000): Promise<AuthUser> {
    return new Promise((resolve, reject) => {
      if (this.isAuthenticated()) {
        const user = this.getCurrentUser();
        if (user) {
          resolve(user);
        } else {
          reject(new Error('User not available'));
        }
        return;
      }

      const unsubscribe = useAuthStore.subscribe(
        (state) => state._isInitialized,
        (isInitialized) => {
          if (isInitialized) {
            unsubscribe();
            const user = this.getCurrentUser();
            if (user) {
              resolve(user);
            } else {
              reject(new Error('User not available after initialization'));
            }
          }
        }
      );

      setTimeout(() => {
        unsubscribe();
        reject(new Error('Auth initialization timeout'));
      }, timeout);
    });
  }
}
