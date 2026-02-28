import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface Reel {
  id: string;
  title: string;
  video_url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number;
  status: string;
  moderation_status: string;
  view_count: number;
  completion_count: number;
  display_order: number;
  created_at: string;
}

export interface CreateReelPayload {
  title: string;
  s3_key: string;
  duration_seconds: number;
  thumbnail_s3_key?: string;
}

export async function getReels(_vendorId: string): Promise<Reel[]> {
  const { data } = await apiClient.get<ApiResponse<Reel[]>>(
    '/api/v1/vendor-portal/reels/',
  );
  return data.data;
}

export async function createReel(_vendorId: string, payload: CreateReelPayload): Promise<Reel> {
  const { data } = await apiClient.post<ApiResponse<Reel>>(
    '/api/v1/vendor-portal/reels/',
    payload,
  );
  return data.data;
}

export async function deleteReel(_vendorId: string, reelId: string): Promise<void> {
  await apiClient.delete(`/api/v1/vendor-portal/reels/${reelId}/`);
}
