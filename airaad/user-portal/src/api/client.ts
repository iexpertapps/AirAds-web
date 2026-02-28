import axios from 'axios';
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';

interface ExtendedConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

interface RefreshResponse {
  success: boolean;
  data: { access: string };
}

interface QueueItem {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
const failedQueue: QueueItem[] = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach((item) => {
    if (error !== null) item.reject(error);
    else if (token !== null) item.resolve(token);
  });
  failedQueue.length = 0;
}

function getStorageKey(): string {
  return 'airad-user-auth';
}

function getAccessToken(): string | null {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.accessToken ?? null;
  } catch {
    return null;
  }
}

function getRefreshToken(): string | null {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.refreshToken ?? null;
  } catch {
    return null;
  }
}

function getGuestToken(): string | null {
  try {
    return localStorage.getItem('airad-guest-token');
  } catch {
    return null;
  }
}

function setAccessToken(token: string): void {
  try {
    const raw = localStorage.getItem(getStorageKey());
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed?.state) {
      parsed.state.accessToken = token;
      localStorage.setItem(getStorageKey(), JSON.stringify(parsed));
    }
  } catch {
    // ignore
  }
}

function clearAuth(): void {
  localStorage.removeItem(getStorageKey());
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  } else {
    const guestToken = getGuestToken();
    if (guestToken) {
      config.headers['X-Guest-Token'] = guestToken;
    }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) return Promise.reject(error);

    const original = error.config as ExtendedConfig | undefined;

    if (error.response?.status === 401 && original && !original._retry) {
      const refreshToken = getRefreshToken();
      if (!refreshToken) return Promise.reject(error);

      original._retry = true;

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (original.headers) original.headers.Authorization = `Bearer ${token}`;
          return apiClient(original);
        });
      }

      isRefreshing = true;
      try {
        const { data } = await axios.post<RefreshResponse>(
          `${import.meta.env.VITE_API_BASE_URL}/api/v1/user-portal/auth/refresh/`,
          { refresh: refreshToken },
        );
        const newAccess = data.data.access;
        setAccessToken(newAccess);
        if (original.headers) original.headers.Authorization = `Bearer ${newAccess}`;
        processQueue(null, newAccess);
        return apiClient(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearAuth();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const event = new CustomEvent('airad:rate-limit', {
        detail: { retryAfter: retryAfter ? parseInt(retryAfter, 10) : 60 },
      });
      window.dispatchEvent(event);
    }

    return Promise.reject(error);
  },
);
