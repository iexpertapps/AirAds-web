import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import type { NotificationTemplate, NotificationLog } from '../types/notification';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export function useNotificationTemplates() {
  return useQuery({
    queryKey: queryKeys.notifications.templates(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<NotificationTemplate[]>>(
        '/api/v1/notifications/templates/',
      );
      return data.data;
    },
    staleTime: 120_000,
  });
}

export function useNotificationHistory() {
  return useQuery({
    queryKey: queryKeys.notifications.history(),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<{ results: NotificationLog[]; count: number }>>(
        '/api/v1/notifications/logs/',
      );
      return data.data;
    },
    staleTime: 30_000,
  });
}
