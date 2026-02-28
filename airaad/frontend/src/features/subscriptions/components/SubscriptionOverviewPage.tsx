import { useMemo } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { CreditCard } from 'lucide-react';
import { useChartColors } from '@/shared/hooks/useChartColors';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useSubscriptionDistribution } from '../queries/useSubscriptions';
import styles from './SubscriptionOverviewPage.module.css';

const TIER_ORDER = ['SILVER', 'GOLD', 'DIAMOND', 'PLATINUM'] as const;

const TIER_COLORS: Record<string, string> = {
  SILVER: '#A8A29E',
  GOLD: '#F97316',
  DIAMOND: '#0D9488',
  PLATINUM: '#DC2626',
};

const TIER_LABELS: Record<string, string> = {
  SILVER: 'Silver',
  GOLD: 'Gold',
  DIAMOND: 'Diamond',
  PLATINUM: 'Platinum',
};

export default function SubscriptionOverviewPage() {
  const chartColors = useChartColors();
  const { data, isLoading, error, refetch } = useSubscriptionDistribution();

  const pieData = useMemo(() => {
    if (!data?.distribution) return [];
    return TIER_ORDER
      .filter((tier) => tier in data.distribution)
      .map((tier) => ({
        name: TIER_LABELS[tier] ?? tier,
        value: data.distribution[tier]?.count ?? 0,
        tier,
      }));
  }, [data]);

  const paidVendors = useMemo(() => {
    if (!data?.distribution) return 0;
    return TIER_ORDER
      .filter((t) => t !== 'SILVER')
      .reduce((sum, t) => sum + (data.distribution[t]?.count ?? 0), 0);
  }, [data]);

  const conversionRate = useMemo(() => {
    if (!data?.total_vendors || data.total_vendors === 0) return 0;
    return ((paidVendors / data.total_vendors) * 100).toFixed(1);
  }, [data, paidVendors]);

  if (error) {
    return (
      <AdminLayout title="Subscriptions">
        <PageHeader heading="Subscription overview" subheading="Vendor tier distribution" />
        <EmptyState
          illustration={<CreditCard size={32} strokeWidth={1.5} />}
          heading="Failed to load subscription data"
          subheading="Something went wrong while fetching subscription distribution."
          ctaLabel="Retry"
          onCta={() => refetch()}
        />
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Subscriptions">
      <PageHeader
        heading="Subscription overview"
        subheading={`${data?.total_vendors?.toLocaleString() ?? '...'} total vendors`}
      />

      {isLoading ? (
        <SkeletonTable rows={3} columns={4} showHeader={false} />
      ) : (
        <>
          <div className={styles.summaryRow}>
            <div className={styles.summaryCard}>
              <span className={styles.summaryValue}>{data?.total_vendors?.toLocaleString() ?? 0}</span>
              <span className={styles.summaryLabel}>Total vendors</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={styles.summaryValue}>{paidVendors.toLocaleString()}</span>
              <span className={styles.summaryLabel}>Paid vendors</span>
            </div>
            <div className={styles.summaryCard}>
              <span className={[styles.summaryValue, styles.conversionHighlight].join(' ')}>
                {conversionRate}%
              </span>
              <span className={styles.summaryLabel}>Conversion rate</span>
            </div>
          </div>

          <div className={styles.grid}>
            {TIER_ORDER.map((tier) => {
              const tierData = data?.distribution?.[tier];
              return (
                <div key={tier} className={[styles.tierCard, styles[`tierCard--${tier}`]].join(' ')}>
                  <span className={styles.tierName}>{TIER_LABELS[tier]}</span>
                  <span className={styles.tierCount}>{tierData?.count?.toLocaleString() ?? 0}</span>
                  <span className={styles.tierPercent}>{tierData?.percentage ?? 0}%</span>
                </div>
              );
            })}
          </div>

          {pieData.length > 0 && (
            <section className={styles.chartSection} aria-label="Tier distribution chart">
              <h2 className={styles.sectionHeading}>Tier distribution</h2>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                  >
                    {pieData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={TIER_COLORS[entry.tier] ?? chartColors.fallback}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: chartColors.tooltipBg,
                      border: `1px solid ${chartColors.tooltipBorder}`,
                      borderRadius: '8px',
                      fontSize: 12,
                      color: chartColors.tickFill,
                    }}
                    formatter={(value: number, name: string) => [value.toLocaleString(), name]}
                  />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </section>
          )}
        </>
      )}
    </AdminLayout>
  );
}
