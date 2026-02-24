import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';

/* ── Types ── */

interface GeoItem {
  id: string;
  name: string;
  slug?: string;
  is_active?: boolean;
}

interface CountryItem extends GeoItem {
  code: string;
}

interface CategoryTag {
  id: string;
  name: string;
  slug: string;
  display_label: string | null;
  display_order: number;
  icon_name: string | null;
}

interface SeedBatchItem {
  id: string;
  import_type: string;
  status: 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED';
  area_name: string;
  search_query: string;
  radius_m: number;
  total_rows: number;
  processed_rows: number;
  error_count: number;
  created_at: string;
  created_by_email: string;
}

interface SeedRequest {
  country_id: string;
  city_id: string;
  area_id: string;
  category_tags: string[];
  search_query: string;
  radius_m: number;
}

interface SeedResponse {
  batch_id: string;
  status: string;
  country: string;
  city: string;
  area: string;
  categories: string[];
  search_query: string;
  radius_m: number;
  poll_url: string;
}

interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
  errors: Record<string, string[]>;
}

/* ── Geo hierarchy queries ── */

export function useCountries() {
  return useQuery({
    queryKey: queryKeys.googlePlaces.countries(),
    queryFn: () =>
      apiClient
        .get<ApiEnvelope<CountryItem[]>>('/api/v1/imports/geo/countries/')
        .then((r) => r.data.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCities(countryId: string) {
  return useQuery({
    queryKey: queryKeys.googlePlaces.cities(countryId),
    queryFn: () =>
      apiClient
        .get<ApiEnvelope<GeoItem[]>>(`/api/v1/imports/geo/countries/${countryId}/cities/`)
        .then((r) => r.data.data),
    enabled: countryId !== '',
    staleTime: 5 * 60 * 1000,
  });
}

export function useAreas(cityId: string) {
  return useQuery({
    queryKey: queryKeys.googlePlaces.areas(cityId),
    queryFn: () =>
      apiClient
        .get<ApiEnvelope<GeoItem[]>>(`/api/v1/imports/geo/cities/${cityId}/areas/`)
        .then((r) => r.data.data),
    enabled: cityId !== '',
    staleTime: 5 * 60 * 1000,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.googlePlaces.categories(),
    queryFn: () =>
      apiClient
        .get<ApiEnvelope<CategoryTag[]>>('/api/v1/imports/tags/categories/')
        .then((r) => r.data.data),
    staleTime: 5 * 60 * 1000,
  });
}

/* ── Seed batches list (Google Places only) ── */

function hasActiveBatches(batches: SeedBatchItem[] | undefined): boolean {
  return (batches ?? []).some(
    (b) => b.status === 'QUEUED' || b.status === 'PROCESSING',
  );
}

export function useSeedBatches() {
  return useQuery({
    queryKey: queryKeys.googlePlaces.seedBatches(),
    queryFn: () =>
      apiClient
        .get<ApiEnvelope<SeedBatchItem[]>>('/api/v1/imports/')
        .then((r) =>
          (r.data.data ?? []).filter(
            (b: SeedBatchItem) =>
              b.import_type === 'GOOGLE_PLACES' || b.import_type === 'GOOGLE_PLACES_ENHANCED',
          ),
        ),
    refetchInterval: (query) =>
      hasActiveBatches(query.state.data as SeedBatchItem[] | undefined) ? 5_000 : false,
  });
}

/* ── Seed mutation ── */

export function useSeedMutation() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: SeedRequest) =>
      apiClient
        .post<ApiEnvelope<SeedResponse>>('/api/v1/imports/google-places/enhanced/', payload)
        .then((r) => r.data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.googlePlaces.seedBatches() });
      void qc.invalidateQueries({ queryKey: queryKeys.imports.list() });
    },
  });
}

/* ── Re-export types for component use ── */

export type { CountryItem, GeoItem, CategoryTag, SeedBatchItem, SeedRequest, SeedResponse };
