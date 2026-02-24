import './theme/dls-tokens.css';

if (!import.meta.env.VITE_API_BASE_URL) {
  throw new Error('[AirAd] VITE_API_BASE_URL is not set. Check your .env file.');
}

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/queryClient';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { ToastProvider } from '@/shared/components/dls/ToastProvider';
import { router } from '@/router';

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('[AirAd] Root element not found');

const app = (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <RouterProvider router={router} />
      <ToastProvider />
    </ThemeProvider>
    {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
  </QueryClientProvider>
);

createRoot(rootElement).render(
  import.meta.env.VITE_E2E === 'true' ? app : <StrictMode>{app}</StrictMode>,
);
