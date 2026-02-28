import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import type { SubscriptionDistributionResponse } from '../types/subscription';

export function useSubscriptionDistribution() {
  return useQuery({
    queryKey: queryKeys.subscriptions.overview(),
    queryFn: async () => {
      const { data } = await apiClient.get<SubscriptionDistributionResponse>(
        '/api/v1/analytics/admin/subscription-distribution/',
      );
      return data.data;
    },
    staleTime: 60_000,
  });
}
