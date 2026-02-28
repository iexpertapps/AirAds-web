import '@/styles/dls-tokens.css';
import '@/styles/shared.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { GlobalErrorBoundary } from '@/components/ErrorBoundary';
import { AppInit } from '@/components/AppInit';
import { router } from '@/router';

if (!import.meta.env.VITE_API_BASE_URL) {
  throw new Error('[AirAd User Portal] Missing required env variable: VITE_API_BASE_URL. Check .env file.');
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

const rootElement = document.getElementById('root');
if (!rootElement) throw new Error('[AirAd User Portal] Root element not found');

createRoot(rootElement).render(
  <StrictMode>
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppInit />
        <RouterProvider router={router} future={{ v7_startTransition: true }} />
        <Toaster
        position="top-center"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'var(--surface-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-lg)',
            font: 'var(--text-body-md)',
          },
        }}
      />
      </QueryClientProvider>
    </GlobalErrorBoundary>
  </StrictMode>,
);
