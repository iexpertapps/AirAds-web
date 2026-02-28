import { apiClient } from './client';
import type { ApiResponse, AuthTokens, GuestToken } from '@/types/api';

export async function getGuestToken(): Promise<ApiResponse<GuestToken>> {
  const { data } = await apiClient.post<ApiResponse<GuestToken>>(
    '/api/v1/user-portal/auth/guest/',
  );
  return data;
}

export async function sendOTP(phone: string): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/auth/send-otp/',
    { phone },
  );
  return data;
}

export async function verifyOTP(phone: string, code: string): Promise<ApiResponse<AuthTokens>> {
  const { data } = await apiClient.post<ApiResponse<AuthTokens>>(
    '/api/v1/user-portal/auth/verify-otp/',
    { phone, otp: code },
  );
  return data;
}

export async function registerUser(payload: {
  phone: string;
  full_name: string;
  email?: string;
}): Promise<ApiResponse<{ message: string }>> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/user-portal/auth/register/',
    payload,
  );
  return data;
}
