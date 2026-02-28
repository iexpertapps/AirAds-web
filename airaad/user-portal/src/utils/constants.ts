export const TIER_COLORS: Record<string, string> = {
  SILVER: 'var(--color-grey-400)',
  GOLD: 'var(--brand-orange)',
  DIAMOND: 'var(--brand-teal)',
  PLATINUM: 'var(--brand-crimson)',
};

export const TIER_LABELS: Record<string, string> = {
  SILVER: 'Silver',
  GOLD: 'Gold',
  DIAMOND: 'Diamond',
  PLATINUM: 'Platinum',
};

export const BREAKPOINTS = {
  mobile: 375,
  tablet: 768,
  desktop: 1024,
  wide: 1280,
} as const;

export const MAP_DEFAULTS = {
  zoom: 14,
  maxZoom: 18,
  minZoom: 10,
  style: 'mapbox://styles/mapbox/dark-v11',
  styleLight: 'mapbox://styles/mapbox/light-v11',
} as const;

export const AR_DEFAULTS = {
  maxRadius: 2000,
  minRadius: 50,
  defaultRadius: 500,
  clusterThreshold: 30,
  markerMinSize: 40,
  markerMaxSize: 80,
} as const;

export const DISCOVERY_DEFAULTS = {
  radiusKm: 2,
  pageSize: 20,
  maxRadius: 10,
  minRadius: 0.5,
} as const;

export const ANIMATION = {
  spring: { type: 'spring' as const, stiffness: 300, damping: 30 },
  fadeIn: { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } },
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
  },
  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  },
} as const;
