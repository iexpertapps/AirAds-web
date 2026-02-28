import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface VoiceBotConfig {
  id: string;
  vendor_id: string;
  menu_items: unknown[];
  opening_hours_summary: string;
  delivery_info: Record<string, unknown>;
  discount_summary: string;
  custom_qa_pairs: unknown[];
  intro_message: string;
  pickup_available: boolean;
  is_active: boolean;
  completeness_score: number;
  last_updated_at: string | null;
}

export interface UpdateVoiceBotPayload {
  menu_items?: unknown[];
  opening_hours_summary?: string;
  delivery_info?: Record<string, unknown>;
  custom_qa_pairs?: unknown[];
  intro_message?: string;
  pickup_available?: boolean;
  is_active?: boolean;
}

export async function getVoiceBotConfig(_vendorId: string): Promise<VoiceBotConfig> {
  const { data } = await apiClient.get<ApiResponse<VoiceBotConfig>>(
    '/api/v1/vendor-portal/voice-bot/',
  );
  return data.data;
}

export async function updateVoiceBotConfig(_vendorId: string, payload: UpdateVoiceBotPayload): Promise<VoiceBotConfig> {
  const { data } = await apiClient.put<ApiResponse<VoiceBotConfig>>(
    '/api/v1/vendor-portal/voice-bot/',
    payload,
  );
  return data.data;
}
