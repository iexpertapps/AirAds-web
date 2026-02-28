import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line,
} from 'recharts';
import { Lock } from 'lucide-react';
import { getVendorAnalytics } from '@/api/analytics';
import { queryKeys } from '@/queryKeys';
import { useAuthStore } from '@/store/authStore';
import styles from './AnalyticsPage.module.css';

const TIER_RANK: Record<string, number> = { SILVER: 0, GOLD: 1, DIAMOND: 2, PLATINUM: 3 };

function hasAccess(userTier: string, requiredTier: string): boolean {
  return (TIER_RANK[userTier] ?? 0) >= (TIER_RANK[requiredTier] ?? 0);
}

function FeatureGate({ requiredTier, userTier, label, children }: {
  requiredTier: string;
  userTier: string;
  label: string;
  children: React.ReactNode;
}) {
  if (hasAccess(userTier, requiredTier)) return <>{children}</>;
  return (
    <div className={styles.gateOverlay}>
      <div className={styles.gateContent}>
        <Lock size={32} strokeWidth={1.5} className={styles.gateIcon} />
        <h3 className={styles.gateHeading}>{label}</h3>
        <p className={styles.gateText}>
          Upgrade to {requiredTier} or higher to unlock this feature.
        </p>
        <Link to="/portal/subscription" className={styles.upgradeBtn}>Upgrade now</Link>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const user = useAuthStore((s) => s.user);
  const vendorId = user?.vendor_id ?? '';
  const tier = user?.subscription_level ?? 'SILVER';

  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.analytics.overview(vendorId),
    queryFn: () => getVendorAnalytics(vendorId, 30),
    enabled: !!vendorId,
    staleTime: 60_000,
  });

  if (isLoading) return <div className={styles.loading}>Loading analytics…</div>;
  if (error || !data) return <div className={styles.error}>Failed to load analytics.</div>;

  return (
    <>
      <h1 className={styles.heading}>Analytics</h1>
      <p className={styles.subtext}>{data.business_name} &middot; Last 14 days</p>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.total_views.toLocaleString()}</span>
          <span className={styles.statLabel}>Total views</span>
        </div>
        <div className={styles.statCard}>
          <span className={[styles.statValue, styles['statValue--highlight']].join(' ')}>
            {data.total_profile_taps.toLocaleString()}
          </span>
          <span className={styles.statLabel}>Profile taps</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.active_discounts}</span>
          <span className={styles.statLabel}>Active discounts</span>
        </div>
      </div>

      {/* Views chart — available to all tiers */}
      <section className={styles.chartSection} aria-label="Views over time">
        <h2 className={styles.sectionHeading}>Daily views</h2>
        {data.daily_views.length === 0 ? (
          <p className={styles.emptyChart}>No view data available yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.daily_views} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ background: 'var(--surface-card)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="count" stroke="var(--brand-orange)" strokeWidth={2} dot={false} name="Views" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>

      {/* Advanced analytics — Gold+ (placeholder for future backend enrichment) */}
      <FeatureGate requiredTier="GOLD" userTier={tier} label="Advanced Analytics">
        <div className={styles.sections}>
          <div className={styles.listCard}>
            <h2 className={styles.sectionHeading}>Discovery sources &amp; Peak hours</h2>
            <p className={styles.comingSoon}>Detailed discovery source tracking and peak hour heatmaps coming soon with Gold+ analytics.</p>
          </div>
        </div>
      </FeatureGate>
    </>
  );
}
