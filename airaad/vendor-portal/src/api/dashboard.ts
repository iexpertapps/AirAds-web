import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface VendorDashboardData {
  business_name: string;
  profile_completeness: {
    score: number;
    total_checks: number;
    completed_count: number;
    completed: string[];
    missing: string[];
  };
  subscription: {
    level: string;
    name: string;
    valid_until: string | null;
    max_videos: number;
    daily_happy_hours_allowed: number;
    has_voice_bot: boolean;
    has_predictive_reports: boolean;
  };
  active_discounts_count: number;
  upcoming_discounts: Array<{
    id: string;
    title: string;
    discount_type: string;
    discount_value: number;
    start_time: string;
  }>;
  weekly_stats: {
    views: number;
    taps: number;
    navigation_clicks: number;
  };
  reels: {
    count: number;
    limit: number;
  };
  voicebot_completeness: number | null;
  upgrade_prompt: {
    next_tier: string;
    next_tier_name: string;
    price_monthly: string;
    key_benefit: string;
  } | null;
  activation_stage: string;
}

export async function getVendorDashboard(): Promise<VendorDashboardData> {
  const { data } = await apiClient.get<ApiResponse<VendorDashboardData>>(
    '/api/v1/vendor-portal/dashboard/',
  );
  return data.data;
}
