import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { useUIStore } from '@/shared/store/uiStore';
import type { ClaimListResponse } from '../types/claim';

interface ClaimFilters {
  status?: string;
  search?: string | undefined;
  page?: number;
  page_size?: number;
}

export function useClaimsList(filters?: ClaimFilters) {
  return useQuery({
    queryKey: queryKeys.claims.list(filters),
    queryFn: async () => {
      const params: Record<string, string | number> = {
        claimed_status: filters?.status || 'CLAIM_PENDING',
        page_size: filters?.page_size || 25,
      };
      if (filters?.search) params.search = filters.search;
      if (filters?.page) params.page = filters.page;
      const { data } = await apiClient.get<ClaimListResponse>('/api/v1/vendors/', { params });
      return data.data;
    },
    staleTime: 30_000,
  });
}

export function useApproveClaim() {
  const queryClient = useQueryClient();
  const addToast = useUIStore.getState().addToast;

  return useMutation({
    mutationFn: async (vendorId: string) => {
      const { data } = await apiClient.post(`/api/v1/admin/vendors/${vendorId}/approve-claim/`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.claims.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.moderation.queue() });
      addToast({ type: 'success', message: 'Claim approved' });
    },
  });
}

export function useRejectClaim() {
  const queryClient = useQueryClient();
  const addToast = useUIStore.getState().addToast;

  return useMutation({
    mutationFn: async ({ vendorId, reason }: { vendorId: string; reason: string }) => {
      const { data } = await apiClient.post(`/api/v1/admin/vendors/${vendorId}/reject-claim/`, { reason });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.claims.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.moderation.queue() });
      addToast({ type: 'success', message: 'Claim rejected' });
    },
  });
}
