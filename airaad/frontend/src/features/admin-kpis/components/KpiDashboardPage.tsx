import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Users, DollarSign, Activity } from 'lucide-react';
import { useChartColors } from '@/shared/hooks/useChartColors';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import {
  useAcquisitionKpis,
  useEngagementKpis,
  useMonetizationKpis,
  usePlatformHealthKpis,
} from '../queries/useAdminKpis';
import styles from './KpiDashboardPage.module.css';

function SectionLoading() {
  return <div className={styles.loadingSection}>Loading…</div>;
}

function SectionError({ message }: { message: string }) {
  return <div className={styles.errorSection}>{message}</div>;
}

export default function KpiDashboardPage() {
  const chartColors = useChartColors();
  const acquisition = useAcquisitionKpis();
  const engagement = useEngagementKpis();
  const monetization = useMonetizationKpis();
  const platformHealth = usePlatformHealthKpis();

  const anyLoading = acquisition.isLoading || engagement.isLoading || monetization.isLoading || platformHealth.isLoading;

  return (
    <AdminLayout title="KPI dashboard">
      <PageHeader
        heading="KPI dashboard"
        subheading="Acquisition, engagement, and monetization metrics"
      />

      {anyLoading ? (
        <SkeletonTable rows={4} columns={3} showHeader={false} />
      ) : (
        <div className={styles.sections}>
          {/* Acquisition */}
          <section className={styles.sectionCard} aria-label="Acquisition KPIs">
            <h2 className={styles.sectionHeading}>
              <TrendingUp size={18} strokeWidth={1.5} aria-hidden="true" />
              Acquisition — Last 30 days
            </h2>
            {acquisition.error ? (
              <SectionError message="Failed to load acquisition data" />
            ) : acquisition.data ? (
              <>
                <div className={styles.metricsGrid}>
                  <div className={styles.metricCard}>
                    <span className={styles.metricValue}>{(acquisition.data.new_vendors_30d || 0).toLocaleString()}</span>
                    <span className={styles.metricLabel}>New vendors</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricValue}>{(acquisition.data.new_claims_30d || 0).toLocaleString()}</span>
                    <span className={styles.metricLabel}>Claims approved</span>
                  </div>
                  <div className={styles.metricCard}>
                    <span className={styles.metricValue}>{(acquisition.data.new_customers_30d || 0).toLocaleString()}</span>
                    <span className={styles.metricLabel}>New customers</span>
                  </div>
                </div>
                {acquisition.data.daily_signups.length > 0 && (
                  <div className={styles.chartWrap}>
                    <ResponsiveContainer width="100%" height={180}>
                      <BarChart data={acquisition.data.daily_signups} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridStroke} />
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: chartColors.tickFill }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 10, fill: chartColors.tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
                        <Tooltip contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: '8px', fontSize: 12, color: chartColors.tickFill }} />
                        <Bar dataKey="count" fill={chartColors.barOrange} radius={[3, 3, 0, 0]} name="Signups" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            ) : (
              <SectionLoading />
            )}
          </section>

          {/* Engagement */}
          <section className={styles.sectionCard} aria-label="Engagement KPIs">
            <h2 className={styles.sectionHeading}>
              <Users size={18} strokeWidth={1.5} aria-hidden="true" />
              Engagement — Last 7 days
            </h2>
            {engagement.error ? (
              <SectionError message="Failed to load engagement data" />
            ) : engagement.data ? (
              <div className={styles.metricsGrid}>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(engagement.data.active_customers_7d || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Active customers</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(engagement.data.searches_7d || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Searches</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(engagement.data.views_7d || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Vendor views</span>
                </div>
              </div>
            ) : (
              <SectionLoading />
            )}
          </section>

          {/* Monetization */}
          <section className={styles.sectionCard} aria-label="Monetization KPIs">
            <h2 className={styles.sectionHeading}>
              <DollarSign size={18} strokeWidth={1.5} aria-hidden="true" />
              Monetization
            </h2>
            {monetization.error ? (
              <SectionError message="Failed to load monetization data" />
            ) : monetization.data ? (
              <div className={styles.metricsGrid}>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(monetization.data.paid_vendors || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Paid vendors</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(monetization.data.total_vendors || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Total vendors</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={[styles.metricValue, styles['metricValue--highlight']].join(' ')}>
                    {monetization.data.conversion_rate}%
                  </span>
                  <span className={styles.metricLabel}>Conversion rate</span>
                </div>
              </div>
            ) : (
              <SectionLoading />
            )}
          </section>

          {/* Platform Health */}
          <section className={styles.sectionCard} aria-label="Platform health KPIs">
            <h2 className={styles.sectionHeading}>
              <Activity size={18} strokeWidth={1.5} aria-hidden="true" />
              Platform health
            </h2>
            {platformHealth.error ? (
              <SectionError message="Failed to load platform health data" />
            ) : platformHealth.data ? (
              <div className={styles.metricsGrid}>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(platformHealth.data.active_vendors_7d || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Active vendors (7d)</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(platformHealth.data.total_reels || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Total reels</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(platformHealth.data.pending_reels_moderation || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Reels pending moderation</span>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricValue}>{(platformHealth.data.active_discounts || 0).toLocaleString()}</span>
                  <span className={styles.metricLabel}>Active discounts</span>
                </div>
              </div>
            ) : (
              <SectionLoading />
            )}
          </section>
        </div>
      )}
    </AdminLayout>
  );
}
