export interface AcquisitionKPIs {
  new_vendors_30d: number;
  new_claims_30d: number;
  new_customers_30d: number;
  daily_signups: Array<{ date: string; count: number }>;
}

export interface EngagementKPIs {
  active_customers_7d: number;
  searches_7d: number;
  views_7d: number;
}

export interface MonetizationKPIs {
  tier_distribution: Record<string, number>;
  paid_vendors: number;
  total_vendors: number;
  conversion_rate: number;
}

export interface PlatformHealthKPIs {
  system_status: string;
  db_status: string;
  cache_status: string;
  active_vendors_7d: number;
  total_vendors: number;
  total_reels: number;
  pending_reels_moderation: number;
  active_discounts: number;
}
