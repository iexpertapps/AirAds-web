import { apiClient } from './client';
import type { ApiResponse, VendorReel } from '@/types/api';

export async function getReelsFeed(
  lat: number,
  lng: number,
  page: number = 1,
): Promise<ApiResponse<VendorReel[]>> {
  const { data } = await apiClient.get<ApiResponse<VendorReel[]>>(
    '/api/v1/user-portal/reels/feed/',
    { params: { lat, lng, page } },
  );
  return data;
}

export async function recordReelView(reelId: string): Promise<void> {
  await apiClient.post(`/api/v1/user-portal/reels/${reelId}/view/`);
}
