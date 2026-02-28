import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

interface UIState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark';
  toasts: Toast[];
  toggleSidebar: () => void;
  toggleTheme: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

const timers = new Map<string, ReturnType<typeof setTimeout>>();

function readPersistedTheme(): 'light' | 'dark' {
  try {
    const stored = localStorage.getItem('airad-theme');
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // ignore storage errors
  }
  // Fall back to system preference, then default to dark
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'dark'; // Default to dark for premium feel
}

export const useUIStore = create<UIState>()(
  immer((set) => ({
    sidebarCollapsed: false,
    theme: readPersistedTheme(),
    toasts: [],

    toggleSidebar: () => {
      set((state) => {
        state.sidebarCollapsed = !state.sidebarCollapsed;
      });
    },

    toggleTheme: () => {
      set((state) => {
        state.theme = state.theme === 'light' ? 'dark' : 'light';
      });
      try {
        const currentTheme = useUIStore.getState().theme;
        localStorage.setItem('airad-theme', currentTheme);
      } catch {
        // ignore storage errors
      }
    },

    setTheme: (theme) => {
      set((state) => {
        state.theme = theme;
      });
      try {
        localStorage.setItem('airad-theme', theme);
      } catch {
        // ignore storage errors
      }
    },

    addToast: (toast) => {
      const id = crypto.randomUUID();
      const duration = toast.duration ?? 4000;
      set((state) => {
        state.toasts.push({ ...toast, id, duration });
      });
      const timer = setTimeout(() => {
        set((state) => {
          state.toasts = state.toasts.filter((t) => t.id !== id);
        });
        timers.delete(id);
      }, duration);
      timers.set(id, timer);
    },

    removeToast: (id) => {
      const timer = timers.get(id);
      if (timer !== undefined) {
        clearTimeout(timer);
        timers.delete(id);
      }
      set((state) => {
        state.toasts = state.toasts.filter((t) => t.id !== id);
      });
    },
  })),
);
