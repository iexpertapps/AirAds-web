import { TIER_COLORS, TIER_LABELS } from '@/utils/constants';
import styles from './TierBadge.module.css';

interface TierBadgeProps {
  tier: 'SILVER' | 'GOLD' | 'DIAMOND' | 'PLATINUM';
  size?: 'sm' | 'md';
}

export function TierBadge({ tier, size = 'sm' }: TierBadgeProps) {
  return (
    <span
      className={`${styles.badge} ${styles[size]}`}
      style={{ '--tier-color': TIER_COLORS[tier] } as React.CSSProperties}
    >
      {TIER_LABELS[tier]}
    </span>
  );
}
