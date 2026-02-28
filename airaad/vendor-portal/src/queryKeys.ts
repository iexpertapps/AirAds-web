export const queryKeys = {
  auth: {
    session: () => ['auth-session'] as const,
  },
  vendor: {
    search: (q: string) => ['claim-search', q] as const,
    nearby: (lat: number, lng: number) => ['claim-nearby', lat, lng] as const,
    profile: (vendorId: string) => ['vendor-profile', vendorId] as const,
  },
  dashboard: {
    overview: () => ['vendor-dashboard'] as const,
  },
  discounts: {
    list: (vendorId: string) => ['vendor-discounts', vendorId] as const,
  },
  reels: {
    list: (vendorId: string) => ['vendor-reels', vendorId] as const,
  },
  analytics: {
    overview: (vendorId: string) => ['vendor-analytics', vendorId] as const,
  },
  voicebot: {
    config: (vendorId: string) => ['voicebot-config', vendorId] as const,
  },
  subscription: {
    status: () => ['subscription-status'] as const,
    invoices: () => ['subscription-invoices'] as const,
  },
} as const;
