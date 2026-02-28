import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { useUIStore } from '@/shared/store/uiStore';
import type { ModerationQueueResponse } from '../types/moderation';

export function useModerationQueue() {
  return useQuery({
    queryKey: queryKeys.moderation.queue(),
    queryFn: async () => {
      const { data } = await apiClient.get<ModerationQueueResponse>('/api/v1/admin/moderation/queue/');
      return data.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useApproveReel() {
  const queryClient = useQueryClient();
  const addToast = useUIStore.getState().addToast;

  return useMutation({
    mutationFn: async ({ reelId, notes }: { reelId: string; notes?: string }) => {
      const { data } = await apiClient.post(`/api/v1/admin/moderation/reels/${reelId}/approve/`, notes ? { notes } : {});
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderation.queue() });
      addToast({ type: 'success', message: 'Reel approved' });
    },
  });
}

export function useRejectReel() {
  const queryClient = useQueryClient();
  const addToast = useUIStore.getState().addToast;

  return useMutation({
    mutationFn: async ({ reelId, reason }: { reelId: string; reason: string }) => {
      const { data } = await apiClient.post(`/api/v1/admin/moderation/reels/${reelId}/reject/`, { reason });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderation.queue() });
      addToast({ type: 'success', message: 'Reel rejected' });
    },
  });
}

export function useRemoveDiscount() {
  const queryClient = useQueryClient();
  const addToast = useUIStore.getState().addToast;

  return useMutation({
    mutationFn: async ({ discountId, reason }: { discountId: string; reason: string }) => {
      const { data } = await apiClient.post(`/api/v1/admin/moderation/discounts/${discountId}/remove/`, { reason });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.moderation.queue() });
      addToast({ type: 'success', message: 'Discount removed' });
    },
  });
}
