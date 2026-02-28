import { Link } from 'react-router-dom';
import { Star, MapPin, Clock } from 'lucide-react';
import { formatDistance, formatRating } from '@/utils/formatters';
import { TIER_COLORS } from '@/utils/constants';
import type { VendorSummary } from '@/types/api';
import styles from './VendorCard.module.css';

interface VendorCardProps {
  vendor: VendorSummary;
}

export function VendorCard({ vendor }: VendorCardProps) {
  return (
    <Link to={`/vendor/${vendor.id}`} className={styles.card}>
      <div className={styles.imageWrap}>
        {vendor.cover_url ? (
          <img
            src={vendor.cover_url}
            alt={vendor.business_name}
            className={styles.coverImage}
            loading="lazy"
          />
        ) : (
          <div className={styles.coverPlaceholder}>
            <MapPin size={32} />
          </div>
        )}
        {vendor.has_active_promotion && vendor.active_promotion_headline && (
          <span className={styles.promoBadge}>
            {vendor.active_promotion_headline}
          </span>
        )}
        <span
          className={styles.tierDot}
          style={{ '--tier-color': TIER_COLORS[vendor.subscription_tier] } as React.CSSProperties}
          aria-label={`${vendor.subscription_tier} tier`}
        />
      </div>
      <div className={styles.body}>
        <div className={styles.header}>
          <div className={styles.logoWrap}>
            {vendor.logo_url ? (
              <img src={vendor.logo_url} alt="" className={styles.logo} loading="lazy" />
            ) : (
              <div className={styles.logoFallback}>
                {vendor.business_name.charAt(0)}
              </div>
            )}
          </div>
          <div className={styles.info}>
            <h3 className={styles.name}>{vendor.business_name}</h3>
            <p className={styles.category}>{vendor.category}</p>
          </div>
        </div>
        <div className={styles.meta}>
          <span className={styles.metaItem}>
            <Star size={14} />
            {formatRating(vendor.average_rating)} ({vendor.review_count})
          </span>
          <span className={styles.metaItem}>
            <MapPin size={14} />
            {formatDistance(vendor.distance_km)}
          </span>
          <span className={`${styles.metaItem} ${vendor.is_open ? styles.open : styles.closed}`}>
            <Clock size={14} />
            {vendor.is_open ? 'Open' : 'Closed'}
          </span>
        </div>
        {vendor.tags.length > 0 && (
          <div className={styles.tags}>
            {vendor.tags.slice(0, 3).map((tag) => (
              <span key={tag} className={styles.tag}>{tag}</span>
            ))}
          </div>
        )}
      </div>
    </Link>
  );
}
