// All query key factories live here. Zero string literals elsewhere.

interface CityFilters {
  country?: string | undefined;
  search?: string | undefined;
}

interface AreaFilters {
  city?: string | undefined;
  search?: string | undefined;
}

interface LandmarkFilters {
  area?: string | undefined;
  search?: string | undefined;
}

interface TagFilters {
  tag_type?: string | undefined;
  is_active?: boolean | undefined;
  search?: string | undefined;
}

interface VendorFilters {
  area_id?: string | undefined;
  city_id?: string | undefined;
  data_source?: string | undefined;
  qc_status?: string | undefined;
  search?: string | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
  ordering?: string | undefined;
}

interface FieldOpsFilters {
  vendor_id?: string | undefined;
  agent?: string | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

interface AuditFilters {
  action?: string | undefined;
  actor_label?: string | undefined;
  target_type?: string | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

interface GovernanceFraudFilters {
  auto_suspended?: boolean | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

interface GovernanceBlacklistFilters {
  blacklist_type?: string | undefined;
  is_active?: boolean | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

interface GovernanceSuspensionFilters {
  vendor_id?: string | undefined;
  is_active?: boolean | undefined;
  action?: string | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

interface ClaimFilters {
  status?: string | undefined;
  search?: string | undefined;
  page?: number | undefined;
  page_size?: number | undefined;
}

export const queryKeys = {
  auth: {
    profile: () => ['auth', 'profile'] as const,
    users: () => ['auth', 'users'] as const,
  },
  analytics: {
    kpis: () => ['analytics', 'kpis'] as const,
  },
  health: {
    status: () => ['health', 'status'] as const,
  },
  geo: {
    countries: () => ['geo', 'countries'] as const,
    cities: (filters?: CityFilters) => ['geo', 'cities', filters] as const,
    city: (id: string) => ['geo', 'city', id] as const,
    areas: (filters?: AreaFilters) => ['geo', 'areas', filters] as const,
    landmarks: (filters?: LandmarkFilters) => ['geo', 'landmarks', filters] as const,
  },
  tags: {
    list: (filters?: TagFilters) => ['tags', 'list', filters] as const,
    detail: (id: string) => ['tags', 'detail', id] as const,
  },
  vendors: {
    list: (filters?: VendorFilters) => ['vendors', 'list', filters] as const,
    detail: (id: string) => ['vendors', 'detail', id] as const,
    photos: (id: string) => ['vendors', 'photos', id] as const,
    visits: (id: string) => ['vendors', 'visits', id] as const,
    tags: (id: string) => ['vendors', 'tags', id] as const,
    analytics: (id: string) => ['vendors', 'analytics', id] as const,
  },
  imports: {
    list: () => ['imports', 'list'] as const,
    detail: (id: string) => ['imports', 'detail', id] as const,
  },
  googlePlaces: {
    countries: () => ['googlePlaces', 'countries'] as const,
    cities: (countryId: string) => ['googlePlaces', 'cities', countryId] as const,
    areas: (cityId: string) => ['googlePlaces', 'areas', cityId] as const,
    categories: () => ['googlePlaces', 'categories'] as const,
    seedBatches: () => ['googlePlaces', 'seedBatches'] as const,
  },
  fieldOps: {
    list: (filters?: FieldOpsFilters) => ['fieldOps', 'list', filters] as const,
    detail: (id: string) => ['fieldOps', 'detail', id] as const,
    photos: (visitId: string) => ['fieldOps', 'photos', visitId] as const,
  },
  qa: {
    dashboard: () => ['qa', 'dashboard'] as const,
  },
  audit: {
    list: (filters?: AuditFilters) => ['audit', 'list', filters] as const,
  },
  system: {
    users: () => ['system', 'users'] as const,
  },
  governance: {
    fraudScores: (filters?: GovernanceFraudFilters) => ['governance', 'fraudScores', filters] as const,
    blacklist: (filters?: GovernanceBlacklistFilters) => ['governance', 'blacklist', filters] as const,
    suspensions: (filters?: GovernanceSuspensionFilters) => ['governance', 'suspensions', filters] as const,
  },
  claims: {
    list: (filters?: ClaimFilters) => ['claims', 'list', filters] as const,
  },
  moderation: {
    queue: () => ['moderation', 'queue'] as const,
  },
  subscriptions: {
    overview: () => ['subscriptions', 'overview'] as const,
  },
  notifications: {
    templates: () => ['notifications', 'templates'] as const,
    history: () => ['notifications', 'history'] as const,
  },
  adminKpis: {
    acquisition: () => ['adminKpis', 'acquisition'] as const,
    engagement: () => ['adminKpis', 'engagement'] as const,
    monetization: () => ['adminKpis', 'monetization'] as const,
    platformHealth: () => ['adminKpis', 'platformHealth'] as const,
  },
};
