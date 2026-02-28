import styles from './SkeletonLoader.module.css';

interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
}

export function Skeleton({
  width = '100%',
  height = '16px',
  borderRadius = 'var(--radius-md)',
  className = '',
}: SkeletonProps) {
  return (
    <div
      className={`${styles.skeleton} ${className}`}
      style={{ width, height, borderRadius }}
      role="presentation"
      aria-hidden="true"
    />
  );
}

export function VendorCardSkeleton() {
  return (
    <div className={styles.vendorCard}>
      <Skeleton height="180px" borderRadius="var(--radius-lg)" />
      <div className={styles.vendorCardBody}>
        <div className={styles.vendorCardRow}>
          <Skeleton width="48px" height="48px" borderRadius="var(--radius-full)" />
          <div className={styles.vendorCardInfo}>
            <Skeleton width="70%" height="16px" />
            <Skeleton width="50%" height="12px" />
          </div>
        </div>
        <Skeleton width="40%" height="14px" />
      </div>
    </div>
  );
}

export function VendorListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className={styles.vendorList}>
      {Array.from({ length: count }).map((_, i) => (
        <VendorCardSkeleton key={i} />
      ))}
    </div>
  );
}
