import { apiClient } from './client';
import type { ApiResponse, CityOption, AreaOption } from '@/types/api';

export async function getCities(): Promise<ApiResponse<CityOption[]>> {
  const { data } = await apiClient.get<ApiResponse<CityOption[]>>(
    '/api/v1/user-portal/geo/cities/',
  );
  return data;
}

export async function getAreas(cityId: string): Promise<ApiResponse<AreaOption[]>> {
  const { data } = await apiClient.get<ApiResponse<AreaOption[]>>(
    `/api/v1/user-portal/geo/cities/${cityId}/areas/`,
  );
  return data;
}
