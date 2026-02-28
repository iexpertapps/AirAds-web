import { apiClient } from './client';
import type { ApiResponse, Promotion } from '@/types/api';

export async function getNearbyDeals(
  lat: number,
  lng: number,
): Promise<ApiResponse<Promotion[]>> {
  const { data } = await apiClient.get<ApiResponse<Promotion[]>>(
    '/api/v1/user-portal/deals/nearby/',
    { params: { lat, lng } },
  );
  return data;
}

export async function getDealDetail(dealId: string): Promise<ApiResponse<Promotion>> {
  const { data } = await apiClient.get<ApiResponse<Promotion>>(
    `/api/v1/user-portal/deals/${dealId}/`,
  );
  return data;
}

export async function getFlashDeals(
  lat: number,
  lng: number,
): Promise<ApiResponse<Promotion[]>> {
  const { data } = await apiClient.get<ApiResponse<Promotion[]>>(
    '/api/v1/user-portal/deals/flash/',
    { params: { lat, lng } },
  );
  return data;
}
