export interface TierDistribution {
  count: number;
  percentage: number;
}

export interface SubscriptionDistribution {
  total_vendors: number;
  distribution: Record<string, TierDistribution>;
}

export interface SubscriptionDistributionResponse {
  success: boolean;
  data: SubscriptionDistribution;
}
