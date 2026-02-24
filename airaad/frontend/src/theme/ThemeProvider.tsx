import { useEffect } from 'react';
import { useUIStore } from '@/shared/store/uiStore';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useUIStore((s) => s.theme);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem('airad-theme', theme);
    } catch {
      // ignore storage errors
    }
  }, [theme]);

  return <>{children}</>;
}
