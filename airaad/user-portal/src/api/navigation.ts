import { apiClient } from './client';
import type { ApiResponse } from '@/types/api';

export async function recordArrival(vendorId: string): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    `/api/v1/user-portal/navigation/arrival/`,
    { vendor_id: vendorId },
  );
  return data;
}

export async function recordInteraction(
  vendorId: string,
  interactionType: string,
): Promise<void> {
  try {
    await apiClient.post('/api/v1/user-portal/analytics/interaction/', {
      vendor_id: vendorId,
      interaction_type: interactionType,
    });
  } catch {
    // fire-and-forget
  }
}
