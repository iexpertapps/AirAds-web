import { apiClient } from './client';
import type {
  ApiResponse,
  VendorDetail,
  VendorReel,
  VendorSummary,
} from '@/types/api';

export async function getVendorDetail(vendorId: string): Promise<ApiResponse<VendorDetail>> {
  const { data } = await apiClient.get<ApiResponse<VendorDetail>>(
    `/api/v1/user-portal/vendors/${vendorId}/`,
  );
  return data;
}

export async function getVendorReels(vendorId: string): Promise<ApiResponse<VendorReel[]>> {
  const { data } = await apiClient.get<ApiResponse<VendorReel[]>>(
    `/api/v1/user-portal/vendors/${vendorId}/reels/`,
  );
  return data;
}

export async function getSimilarVendors(vendorId: string): Promise<ApiResponse<VendorSummary[]>> {
  const { data } = await apiClient.get<ApiResponse<VendorSummary[]>>(
    `/api/v1/user-portal/vendors/${vendorId}/similar/`,
  );
  return data;
}

export async function getVendorVoiceBot(
  vendorId: string,
  question: string,
): Promise<ApiResponse<{ answer: string; suggestions: string[] }>> {
  const { data } = await apiClient.post<ApiResponse<{ answer: string; suggestions: string[] }>>(
    `/api/v1/user-portal/vendors/${vendorId}/voice-bot/`,
    { question },
  );
  return data;
}
