import { Percent, Zap } from 'lucide-react';
import styles from './PromotionBadge.module.css';

interface PromotionBadgeProps {
  headline: string;
  isFlash?: boolean;
  className?: string;
}

export function PromotionBadge({ headline, isFlash = false, className = '' }: PromotionBadgeProps) {
  return (
    <span className={`${styles.badge} ${isFlash ? styles.flash : ''} ${className}`}>
      {isFlash ? <Zap size={12} /> : <Percent size={12} />}
      {headline}
    </span>
  );
}
