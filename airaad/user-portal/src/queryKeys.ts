export const queryKeys = {
  auth: {
    guest: () => ['guest-token'] as const,
    session: () => ['auth-session'] as const,
  },
  discovery: {
    nearby: (lat: number, lng: number, radius: number, tags: string[], q: string) =>
      ['discovery-nearby', lat, lng, radius, tags, q] as const,
    arMarkers: (lat: number, lng: number, radius: number) =>
      ['ar-markers', lat, lng, radius] as const,
    mapPins: (lat: number, lng: number, radius: number) =>
      ['map-pins', lat, lng, radius] as const,
    search: (q: string) => ['discovery-search', q] as const,
    suggestions: (q: string) => ['search-suggestions', q] as const,
    promotionsStrip: (lat: number, lng: number) =>
      ['promotions-strip', lat, lng] as const,
  },
  tags: {
    browser: (lat: number, lng: number) => ['tag-browser', lat, lng] as const,
    count: (tags: string[], lat: number, lng: number) =>
      ['tag-count', tags, lat, lng] as const,
  },
  vendor: {
    detail: (id: string) => ['vendor-detail', id] as const,
    reels: (id: string) => ['vendor-reels', id] as const,
    similar: (id: string) => ['vendor-similar', id] as const,
    voicebot: (id: string) => ['vendor-voicebot', id] as const,
  },
  deals: {
    nearby: (lat: number, lng: number) => ['deals-nearby', lat, lng] as const,
    detail: (id: string) => ['deal-detail', id] as const,
    flash: (lat: number, lng: number) => ['flash-deals', lat, lng] as const,
  },
  reels: {
    feed: (lat: number, lng: number) => ['reels-feed', lat, lng] as const,
  },
  preferences: {
    get: () => ['user-preferences'] as const,
    history: () => ['search-history'] as const,
  },
  geo: {
    cities: () => ['cities'] as const,
    areas: (cityId: string) => ['areas', cityId] as const,
  },
} as const;
