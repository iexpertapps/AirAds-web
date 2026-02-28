import { apiClient } from './client';

interface SendOTPResponse {
  success: boolean;
  data: { message: string };
}

interface VerifyOTPResponse {
  success: boolean;
  data: {
    access: string;
    refresh: string;
    user: {
      id: string;
      phone: string;
      full_name: string;
      vendor_id: string | null;
      activation_stage: 'UNCLAIMED' | 'CLAIM_PENDING' | 'CLAIMED' | 'PROFILE_COMPLETE';
      subscription_level: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
    };
  };
}

export async function sendOTP(phone: string): Promise<SendOTPResponse> {
  const { data } = await apiClient.post<SendOTPResponse>(
    '/api/v1/vendor-portal/auth/send-otp/',
    { phone },
  );
  return data;
}

export async function verifyOTP(phone: string, code: string): Promise<VerifyOTPResponse> {
  const { data } = await apiClient.post<VerifyOTPResponse>(
    '/api/v1/vendor-portal/auth/verify-otp/',
    { phone, otp: code },
  );
  return data;
}
