import { create } from 'zustand';

type Theme = 'light' | 'dark';

function readPersistedTheme(): Theme {
  try {
    const stored = localStorage.getItem('airad-user-theme');
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // ignore
  }
  return 'dark';
}

function applyThemeToDOM(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
}

interface UIState {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  isVoiceSearchOpen: boolean;
  setVoiceSearchOpen: (open: boolean) => void;
  isTagBrowserOpen: boolean;
  setTagBrowserOpen: (open: boolean) => void;
  rateLimitUntil: number | null;
  setRateLimitUntil: (until: number | null) => void;
}

export const useUIStore = create<UIState>()((set) => ({
  theme: (() => {
    const t = readPersistedTheme();
    applyThemeToDOM(t);
    return t;
  })(),

  toggleTheme: () => {
    set((state) => {
      const next = state.theme === 'light' ? 'dark' : 'light';
      try { localStorage.setItem('airad-user-theme', next); } catch { /* ignore */ }
      applyThemeToDOM(next);
      return { theme: next };
    });
  },

  setTheme: (theme) => {
    try { localStorage.setItem('airad-user-theme', theme); } catch { /* ignore */ }
    applyThemeToDOM(theme);
    set({ theme });
  },

  isVoiceSearchOpen: false,
  setVoiceSearchOpen: (open) => set({ isVoiceSearchOpen: open }),

  isTagBrowserOpen: false,
  setTagBrowserOpen: (open) => set({ isTagBrowserOpen: open }),

  rateLimitUntil: null,
  setRateLimitUntil: (until) => set({ rateLimitUntil: until }),
}));
