import { QueryClient } from '@tanstack/react-query';
import axios from 'axios';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      // Only retry on 5xx server errors — never on 4xx client errors.
      // 401s are handled by the Axios interceptor (token refresh + re-request).
      // Retrying 4xx responses causes double-requests and masks real errors.
      retry: (failureCount, error) => {
        if (axios.isAxiosError(error) && error.response && error.response.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      onError: () => {
        // Global mutation errors handled by Axios interceptor toast
      },
    },
  },
});
