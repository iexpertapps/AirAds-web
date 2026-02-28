/* ============================================================
   API Response Types — mirrors backend response shapes exactly
   ============================================================ */

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: {
    results: T[];
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface GeoPoint {
  type: 'Point';
  coordinates: [number, number]; // [lng, lat]
}

export interface VendorSummary {
  id: string;
  business_name: string;
  slug: string;
  category: string;
  subcategory: string | null;
  address: string;
  city: string;
  area: string;
  location: GeoPoint;
  distance_km: number;
  phone: string | null;
  logo_url: string | null;
  cover_url: string | null;
  subscription_tier: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
  average_rating: number;
  review_count: number;
  is_open: boolean;
  tags: string[];
  has_active_promotion: boolean;
  active_promotion_headline: string | null;
  ranking_score: number;
}

export interface VendorDetail extends VendorSummary {
  description: string;
  website: string | null;
  email: string | null;
  business_hours: Record<string, { open: string; close: string }>;
  social_links: Record<string, string>;
  gallery_urls: string[];
  voice_intro_url: string | null;
  reel_count: number;
  founded_year: number | null;
  features: string[];
}

export interface Promotion {
  id: string;
  vendor_id: string;
  vendor_name: string;
  vendor_logo_url: string | null;
  title: string;
  description: string;
  discount_type: 'PERCENTAGE' | 'FIXED' | 'BOGO';
  discount_value: number;
  original_price: number | null;
  discounted_price: number | null;
  start_date: string;
  end_date: string;
  is_flash_deal: boolean;
  is_active: boolean;
  terms_conditions: string | null;
  image_url: string | null;
  redemption_count: number;
  max_redemptions: number | null;
}

export interface VendorReel {
  id: string;
  vendor_id: string;
  vendor_name: string;
  vendor_logo_url: string | null;
  vendor_tier: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
  title: string;
  video_url: string;
  thumbnail_url: string | null;
  duration_seconds: number;
  view_count: number;
  created_at: string;
}

export interface ARMarker {
  vendor_id: string;
  business_name: string;
  category: string;
  logo_url: string | null;
  subscription_tier: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
  location: GeoPoint;
  distance_m: number;
  bearing: number;
  has_active_promotion: boolean;
  promotion_headline: string | null;
  ranking_score: number;
}

export interface MapPin {
  vendor_id: string;
  business_name: string;
  category: string;
  logo_url: string | null;
  subscription_tier: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
  location: GeoPoint;
  has_active_promotion: boolean;
  is_open: boolean;
}

export interface TagGroup {
  section: 'hot' | 'intent' | 'category' | 'distance';
  label: string;
  tags: TagItem[];
}

export interface TagItem {
  slug: string;
  label: string;
  icon: string | null;
  count: number;
}

export interface SearchSuggestion {
  type: 'vendor' | 'tag' | 'category';
  label: string;
  slug: string;
  vendor_id?: string;
}

export interface VoiceSearchResult {
  transcript: string;
  intent: string;
  filters: Record<string, string>;
  vendors: VendorSummary[];
}

export interface PromotionStrip {
  id: string;
  vendor_name: string;
  headline: string;
  vendor_id: string;
  ends_at: string;
}

export interface CityOption {
  id: string;
  name: string;
  slug: string;
}

export interface AreaOption {
  id: string;
  name: string;
  slug: string;
  city_id: string;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  notifications_enabled: boolean;
  distance_unit: 'km' | 'mi';
  preferred_categories: string[];
  preferred_city: string | null;
  preferred_area: string | null;
}

export interface GuestToken {
  guest_token: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
  user: CustomerUser;
}

export interface CustomerUser {
  id: string;
  phone: string;
  full_name: string;
  email: string | null;
}

export interface NavigationRoute {
  vendor_id: string;
  vendor_name: string;
  destination: GeoPoint;
  estimated_duration_min: number;
  estimated_distance_km: number;
}
