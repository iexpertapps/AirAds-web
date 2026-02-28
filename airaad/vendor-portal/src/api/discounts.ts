import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface Discount {
  id: string;
  title: string;
  discount_type: string;
  value: string;
  applies_to: string;
  item_description: string;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
  recurrence_days: number[];
  is_active: boolean;
  min_order_value: string;
  ar_badge_text: string;
  delivery_radius_m: number | null;
  free_delivery_distance_m: number | null;
  views_during_campaign: number;
  taps_during_campaign: number;
  navigation_clicks_during_campaign: number;
  created_at: string;
}

export interface CreateDiscountPayload {
  title: string;
  discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT' | 'BUY_ONE_GET_ONE' | 'HAPPY_HOUR';
  value: number;
  applies_to?: string;
  item_description?: string;
  start_time: string;
  end_time: string;
  is_recurring?: boolean;
  recurrence_days?: number[];
  min_order_value?: number;
  ar_badge_text?: string;
}

export async function getDiscounts(_vendorId: string): Promise<Discount[]> {
  const { data } = await apiClient.get<ApiResponse<Discount[]>>(
    '/api/v1/vendor-portal/discounts/',
  );
  return data.data;
}

export async function createDiscount(_vendorId: string, payload: CreateDiscountPayload): Promise<Discount> {
  const { data } = await apiClient.post<ApiResponse<Discount>>(
    '/api/v1/vendor-portal/discounts/',
    payload,
  );
  return data.data;
}

export async function deleteDiscount(_vendorId: string, discountId: string): Promise<void> {
  await apiClient.delete(`/api/v1/vendor-portal/discounts/${discountId}/`);
}
