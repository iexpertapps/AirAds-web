import { apiClient } from './client';
import type {
  ApiResponse,
  PaginatedResponse,
  VendorSummary,
  ARMarker,
  MapPin,
  SearchSuggestion,
  PromotionStrip,
  VoiceSearchResult,
  TagGroup,
} from '@/types/api';

interface NearbyParams {
  lat: number;
  lng: number;
  radius_km?: number;
  tags?: string[];
  q?: string;
  sort_by?: 'relevance' | 'distance' | 'rating';
  page?: number;
  page_size?: number;
}

export async function getNearbyVendors(params: NearbyParams): Promise<PaginatedResponse<VendorSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<VendorSummary>>(
    '/api/v1/user-portal/discovery/nearby/',
    { params },
  );
  return data;
}

export async function getARMarkers(
  lat: number,
  lng: number,
  radius_km: number = 1,
): Promise<ApiResponse<ARMarker[]>> {
  const { data } = await apiClient.get<ApiResponse<ARMarker[]>>(
    '/api/v1/user-portal/discovery/ar-markers/',
    { params: { lat, lng, radius_km } },
  );
  return data;
}

export async function getMapPins(
  lat: number,
  lng: number,
  radius_km: number = 2,
): Promise<ApiResponse<MapPin[]>> {
  const { data } = await apiClient.get<ApiResponse<MapPin[]>>(
    '/api/v1/user-portal/discovery/map-pins/',
    { params: { lat, lng, radius_km } },
  );
  return data;
}

export async function searchVendors(q: string): Promise<PaginatedResponse<VendorSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<VendorSummary>>(
    '/api/v1/user-portal/discovery/search/',
    { params: { q } },
  );
  return data;
}

export async function getSearchSuggestions(q: string): Promise<ApiResponse<SearchSuggestion[]>> {
  const { data } = await apiClient.get<ApiResponse<SearchSuggestion[]>>(
    '/api/v1/user-portal/discovery/suggestions/',
    { params: { q } },
  );
  return data;
}

export async function voiceSearch(transcript: string): Promise<ApiResponse<VoiceSearchResult>> {
  const { data } = await apiClient.post<ApiResponse<VoiceSearchResult>>(
    '/api/v1/user-portal/discovery/voice-search/',
    { transcript },
  );
  return data;
}

export async function getTagBrowser(
  lat: number,
  lng: number,
): Promise<ApiResponse<TagGroup[]>> {
  const { data } = await apiClient.get<ApiResponse<TagGroup[]>>(
    '/api/v1/user-portal/discovery/tags/',
    { params: { lat, lng } },
  );
  return data;
}

export async function getTagCount(
  tags: string[],
  lat: number,
  lng: number,
): Promise<ApiResponse<{ count: number }>> {
  const { data } = await apiClient.get<ApiResponse<{ count: number }>>(
    '/api/v1/user-portal/discovery/tags/count/',
    { params: { tags: tags.join(','), lat, lng } },
  );
  return data;
}

export async function getPromotionsStrip(
  lat: number,
  lng: number,
): Promise<ApiResponse<PromotionStrip[]>> {
  const { data } = await apiClient.get<ApiResponse<PromotionStrip[]>>(
    '/api/v1/user-portal/discovery/promotions-strip/',
    { params: { lat, lng } },
  );
  return data;
}
