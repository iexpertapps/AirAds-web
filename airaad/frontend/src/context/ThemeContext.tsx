import React, { useEffect, useState } from 'react';
import { ThemeContext } from './ThemeContextDefinition';
import type { Theme } from './ThemeContextDefinition';

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first
    const saved = localStorage.getItem('airad-theme') as Theme | null;
    if (saved) return saved;
    
    // Fall back to system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    
    // Default fallback: dark (the app looks more premium in dark mode)
    return 'dark';
  });

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    localStorage.setItem('airad-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setThemeState(prev => prev === 'light' ? 'dark' : 'light');
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
