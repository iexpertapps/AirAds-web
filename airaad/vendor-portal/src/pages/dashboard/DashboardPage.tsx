import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tag, Film, BarChart3, CreditCard, ArrowUpRight } from 'lucide-react';
import { getVendorDashboard } from '@/api/dashboard';
import { queryKeys } from '@/queryKeys';
import { formatDateTime } from '@/utils/formatters';
import styles from './DashboardPage.module.css';

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.dashboard.overview(),
    queryFn: getVendorDashboard,
    staleTime: 30_000,
  });

  if (isLoading) {
    return <div className={styles.loading}>Loading dashboard…</div>;
  }

  if (error || !data) {
    return <div className={styles.error}>Failed to load dashboard. Please refresh.</div>;
  }

  const completenessScore = data.profile_completeness.score;

  return (
    <>
      <h1 className={styles.heading}>{data.business_name}</h1>
      <p className={styles.subtext}>
        {data.subscription.name} plan &middot; Here&apos;s how your business is performing
      </p>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.weekly_stats.views.toLocaleString()}</span>
          <span className={styles.statLabel}>Views (7 days)</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.weekly_stats.taps.toLocaleString()}</span>
          <span className={styles.statLabel}>Profile taps</span>
        </div>
        <div className={styles.statCard}>
          <span className={[styles.statValue, styles['statValue--highlight']].join(' ')}>
            {data.weekly_stats.navigation_clicks.toLocaleString()}
          </span>
          <span className={styles.statLabel}>Navigation clicks</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.active_discounts_count}</span>
          <span className={styles.statLabel}>Active discounts</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statValue}>{data.reels.count}/{data.reels.limit}</span>
          <span className={styles.statLabel}>Reels uploaded</span>
        </div>
      </div>

      <div className={styles.sections}>
        <div className={styles.sectionCard}>
          <h2 className={styles.sectionHeading}>Profile completeness</h2>
          <div className={styles.progressWrap}>
            <div className={styles.progressBar}>
              <div
                className={styles.progressFill}
                role="progressbar"
                aria-valuenow={completenessScore}
                aria-valuemin={0}
                aria-valuemax={100}
                style={{ '--progress': `${completenessScore}%` } as React.CSSProperties}
              />
            </div>
            <span className={styles.progressLabel}>{completenessScore}% complete</span>
          </div>
          {data.profile_completeness.missing.length > 0 && (
            <p className={styles.missingHint}>
              Missing: {data.profile_completeness.missing.join(', ').replace(/_/g, ' ')}
            </p>
          )}

          <h2 className={styles.sectionHeading}>Quick actions</h2>
          <div className={styles.quickActions}>
            <Link to="/portal/discounts" className={styles.quickAction}>
              <Tag size={14} strokeWidth={1.5} /> Create discount
            </Link>
            <Link to="/portal/reels" className={styles.quickAction}>
              <Film size={14} strokeWidth={1.5} /> Upload reel
            </Link>
            <Link to="/portal/analytics" className={styles.quickAction}>
              <BarChart3 size={14} strokeWidth={1.5} /> View analytics
            </Link>
            <Link to="/portal/subscription" className={styles.quickAction}>
              <CreditCard size={14} strokeWidth={1.5} /> Manage plan
            </Link>
          </div>
        </div>

        <div className={styles.sectionCard}>
          <h2 className={styles.sectionHeading}>Upcoming discounts</h2>
          {data.upcoming_discounts.length === 0 ? (
            <p className={styles.emptyActivity}>No upcoming discounts scheduled.</p>
          ) : (
            <ul className={styles.activityList}>
              {data.upcoming_discounts.slice(0, 5).map((item) => (
                <li key={item.id} className={styles.activityItem}>
                  <span className={styles.activityDot} />
                  <div>
                    <span className={styles.activityText}>{item.title} ({item.discount_value}% {item.discount_type.toLowerCase()})</span>
                    <span className={styles.activityTime}>Starts {formatDateTime(item.start_time)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {data.upgrade_prompt && (
            <div className={styles.upgradePrompt}>
              <p className={styles.upgradeText}>
                <ArrowUpRight size={14} strokeWidth={1.5} />
                Upgrade to {data.upgrade_prompt.next_tier_name}: {data.upgrade_prompt.key_benefit}
              </p>
              <Link to="/portal/subscription" className={styles.upgradeLink}>
                View plans
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
