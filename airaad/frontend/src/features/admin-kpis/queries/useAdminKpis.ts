import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import type { AcquisitionKPIs, EngagementKPIs, MonetizationKPIs, PlatformHealthKPIs } from '../types/kpi';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export function useAcquisitionKpis() {
  return useQuery({
    queryKey: queryKeys.adminKpis.acquisition(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<AcquisitionKPIs>>(
        '/api/v1/analytics/admin/kpi/acquisition/',
      );
      return data.data;
    },
    staleTime: 60_000,
  });
}

export function useEngagementKpis() {
  return useQuery({
    queryKey: queryKeys.adminKpis.engagement(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<EngagementKPIs>>(
        '/api/v1/analytics/admin/kpi/engagement/',
      );
      return data.data;
    },
    staleTime: 60_000,
  });
}

export function useMonetizationKpis() {
  return useQuery({
    queryKey: queryKeys.adminKpis.monetization(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<MonetizationKPIs>>(
        '/api/v1/analytics/admin/kpi/monetization/',
      );
      return data.data;
    },
    staleTime: 60_000,
  });
}

export function usePlatformHealthKpis() {
  return useQuery({
    queryKey: queryKeys.adminKpis.platformHealth(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<PlatformHealthKPIs>>(
        '/api/v1/analytics/admin/kpi/platform-health/',
      );
      return data.data;
    },
    staleTime: 30_000,
  });
}
