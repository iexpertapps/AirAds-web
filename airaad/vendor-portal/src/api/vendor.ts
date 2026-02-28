import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface NearbyVendor {
  id: string;
  business_name: string;
  address_text: string;
  area_name: string;
  gps_point: { latitude: number; longitude: number } | null;
  claimed_status: 'UNCLAIMED' | 'CLAIM_PENDING' | 'CLAIMED' | 'CLAIM_REJECTED';
  distance_meters: number | null;
}

export interface VendorProfile {
  id: string;
  business_name: string;
  slug: string;
  description: string;
  gps_point: { latitude: number; longitude: number } | null;
  address_text: string;
  city_name: string;
  area_name: string;
  landmark_name: string;
  phone_masked: string;
  business_hours: string | Record<string, { open: string; close: string; is_closed: boolean }> | null;
  claimed_status: string;
  claimed_at: string | null;
  is_verified: boolean;
  subscription_level: string;
  subscription_valid_until: string | null;
  offers_delivery: boolean;
  offers_pickup: boolean;
  activation_stage: string;
  total_views: number;
  total_profile_taps: number;
  logo_url: string;
  cover_photo_url: string;
  storefront_photo_url: string;
}

export async function searchVendors(query: string): Promise<NearbyVendor[]> {
  const { data } = await apiClient.get<ApiResponse<NearbyVendor[]>>(
    '/api/v1/vendor-portal/claim/search/',
    { params: { q: query } },
  );
  return data.data ?? [];
}

export async function getNearbyVendors(lat: number, lng: number): Promise<NearbyVendor[]> {
  const { data } = await apiClient.get<ApiResponse<NearbyVendor[]>>(
    '/api/v1/vendor-portal/claim/search/',
    { params: { lat, lng } },
  );
  return data.data ?? [];
}

export async function submitClaim(vendorId: string): Promise<{ vendor_id: string; message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ vendor_id: string; message: string }>>(
    '/api/v1/vendor-portal/claim/submit/',
    { vendor_id: vendorId },
  );
  return data.data;
}

export async function updateVendorProfile(
  _vendorId: string,
  payload: {
    business_name?: string;
    description?: string;
    address_text?: string;
  },
): Promise<{ updated_fields: string[]; vendor_id: string }> {
  const { data } = await apiClient.patch<ApiResponse<{ updated_fields: string[]; vendor_id: string }>>(
    '/api/v1/vendor-portal/profile/',
    payload,
  );
  return data.data;
}

export async function updateBusinessHours(
  hours: Record<string, unknown>,
): Promise<unknown> {
  const { data } = await apiClient.patch<ApiResponse<unknown>>(
    '/api/v1/vendor-portal/profile/hours/',
    hours,
  );
  return data.data;
}
