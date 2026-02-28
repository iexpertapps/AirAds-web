import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface VendorAnalytics {
  vendor_id: string;
  business_name: string;
  total_views: number;
  total_profile_taps: number;
  subscription_level: string;
  active_discounts: number;
  daily_views: Array<{ date: string; count: number }>;
}

export async function getVendorAnalytics(vendorId: string, days: number = 30): Promise<VendorAnalytics> {
  const { data } = await apiClient.get<ApiResponse<VendorAnalytics>>(
    `/api/v1/analytics/vendors/${vendorId}/summary/`,
    { params: { days } },
  );
  return data.data;
}
