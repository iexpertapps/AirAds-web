export const TIER_NAMES: Record<string, string> = {
  SILVER: 'Silver',
  GOLD: 'Gold',
  DIAMOND: 'Diamond',
  PLATINUM: 'Platinum',
};

export const TIER_RANK: Record<string, number> = {
  SILVER: 0,
  GOLD: 1,
  DIAMOND: 2,
  PLATINUM: 3,
};

export const TIER_PRICES: Record<string, number> = {
  SILVER: 0,
  GOLD: 3000,
  DIAMOND: 7000,
  PLATINUM: 15000,
};

export const TIER_FEATURES: Record<string, string[]> = {
  SILVER: ['1 reel upload', 'Basic AR visibility', 'Basic metrics'],
  GOLD: ['3 reel uploads', 'Boosted AR', 'Voice introduction', 'Verified badge', '1 happy hour/day'],
  DIAMOND: ['6 reel uploads', 'High priority AR', 'Dynamic voice bot', 'Premium badge', '3 happy hours/day', 'Advanced analytics'],
  PLATINUM: ['Unlimited reels', 'Dominant zone AR', 'Advanced voice bot', 'Elite crown', 'Smart automation', 'Competitor insights'],
};

export const DISCOUNT_TYPES = [
  { value: 'PERCENTAGE', label: 'Percentage' },
  { value: 'FIXED', label: 'Fixed amount (PKR)' },
  { value: 'BOGO', label: 'Buy One Get One' },
] as const;

export const VOICE_STYLES = [
  { value: 'PROFESSIONAL', label: 'Professional' },
  { value: 'FRIENDLY', label: 'Friendly' },
  { value: 'CASUAL', label: 'Casual' },
] as const;

export const ACTIVATION_STAGES = [
  'CLAIM',
  'ENGAGEMENT',
  'MONETIZATION',
  'GROWTH',
  'RETENTION',
] as const;

export const MODERATION_STATUSES = {
  PENDING: 'Pending',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
} as const;
