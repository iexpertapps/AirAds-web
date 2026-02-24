import axios from 'axios';
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { AuthStateManager } from '@/features/auth/store/authStore';
import { useUIStore } from '@/shared/store/uiStore';
import { queryClient } from '@/lib/queryClient';

interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

interface RefreshResponse {
  access: string;
}

interface QueueItem {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
const failedQueue: QueueItem[] = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach((item) => {
    if (error !== null) {
      item.reject(error);
    } else if (token !== null) {
      item.resolve(token);
    }
  });
  failedQueue.length = 0;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

let proactiveRefreshPromise: Promise<string | null> | null = null;

async function ensureAccessToken(): Promise<string | null> {
  const current = AuthStateManager.getCurrentAccessToken();
  if (current) return current;

  const refreshToken = AuthStateManager.getCurrentRefreshToken();
  if (!refreshToken) return null;

  if (proactiveRefreshPromise) return proactiveRefreshPromise;

  proactiveRefreshPromise = (async () => {
    try {
      const { data } = await axios.post<RefreshResponse>(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/refresh/`,
        { refresh: refreshToken },
      );
      const newToken = data.access;
      AuthStateManager.setAccessToken(newToken);
      return newToken;
    } catch {
      return null;
    } finally {
      proactiveRefreshPromise = null;
    }
  })();

  return proactiveRefreshPromise;
}

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await ensureAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(error);
    }

    const original = error.config as ExtendedAxiosRequestConfig | undefined;

    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (original.headers) {
            original.headers.Authorization = `Bearer ${token}`;
          }
          return apiClient(original);
        });
      }

      isRefreshing = true;

      try {
        const refreshToken = AuthStateManager.getCurrentRefreshToken();
        const { data } = await axios.post<RefreshResponse>(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/auth/refresh/`,
          { refresh: refreshToken },
        );
        // SimpleJWT returns { access } directly — no data wrapper
        const newToken = data.access;
        AuthStateManager.setAccessToken(newToken);
        if (original.headers) {
          original.headers.Authorization = `Bearer ${newToken}`;
        }
        processQueue(null, newToken);
        return apiClient(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        AuthStateManager.logout();
        queryClient.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status !== 401) {
      const responseData = error.response?.data as Record<string, unknown> | undefined;
      const message =
        typeof responseData?.['message'] === 'string'
          ? responseData['message']
          : 'Something went wrong. Please try again.';
      useUIStore.getState().addToast({ type: 'error', message });
    }

    return Promise.reject(error);
  },
);
