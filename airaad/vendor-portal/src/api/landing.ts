import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface LandingStats {
  total_active_vendors: number;
  claimed_vendors: number;
  total_cities: number;
  avg_views_after_claim: number;
}

export interface Testimonial {
  id: string;
  vendor_name: string;
  business_name: string;
  location: string;
  quote: string;
  photo_url: string | null;
}

export async function getLandingStats(): Promise<LandingStats> {
  const { data } = await apiClient.get<ApiResponse<LandingStats>>(
    '/api/v1/vendor-portal/landing/stats/',
  );
  return data.data;
}

export async function getTestimonials(): Promise<Testimonial[]> {
  const { data } = await apiClient.get<ApiResponse<Testimonial[]>>(
    '/api/v1/vendor-portal/landing/testimonials/',
  );
  return data.data;
}
