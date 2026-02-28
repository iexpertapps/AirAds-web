import { apiClient } from './client';
import type { ApiResponse, UserPreferences } from '@/types/api';

export async function getUserPreferences(): Promise<ApiResponse<UserPreferences>> {
  const { data } = await apiClient.get<ApiResponse<UserPreferences>>(
    '/api/v1/user-portal/preferences/',
  );
  return data;
}

export async function updateUserPreferences(
  prefs: Partial<UserPreferences>,
): Promise<ApiResponse<UserPreferences>> {
  const { data } = await apiClient.patch<ApiResponse<UserPreferences>>(
    '/api/v1/user-portal/preferences/',
    prefs,
  );
  return data;
}

export async function getSearchHistory(): Promise<ApiResponse<{ queries: string[] }>> {
  const { data } = await apiClient.get<ApiResponse<{ queries: string[] }>>(
    '/api/v1/user-portal/preferences/search-history/',
  );
  return data;
}

export async function clearSearchHistory(): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.delete<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/preferences/search-history/',
  );
  return data;
}

export async function requestDataExport(): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/preferences/data-export/',
  );
  return data;
}

export async function requestAccountDeletion(code: string): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/preferences/delete-account/',
    { code },
  );
  return data;
}

export async function requestDeletionCode(): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/preferences/delete-account/code/',
  );
  return data;
}
