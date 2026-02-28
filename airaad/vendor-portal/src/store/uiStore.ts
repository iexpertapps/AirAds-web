import { create } from 'zustand';

type Theme = 'light' | 'dark';

function readPersistedTheme(): Theme {
  try {
    const stored = localStorage.getItem('airad-vendor-theme');
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // ignore
  }
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

function applyThemeToDOM(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
}

interface UIState {
  sidebarCollapsed: boolean;
  theme: Theme;
  toggleSidebar: () => void;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarCollapsed: false,
  theme: (() => {
    const t = readPersistedTheme();
    applyThemeToDOM(t);
    return t;
  })(),

  toggleSidebar: () => {
    set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }));
  },

  toggleTheme: () => {
    set((state) => {
      const next = state.theme === 'light' ? 'dark' : 'light';
      try { localStorage.setItem('airad-vendor-theme', next); } catch { /* ignore */ }
      applyThemeToDOM(next);
      return { theme: next };
    });
  },

  setTheme: (theme) => {
    try { localStorage.setItem('airad-vendor-theme', theme); } catch { /* ignore */ }
    applyThemeToDOM(theme);
    set({ theme });
  },
}));
