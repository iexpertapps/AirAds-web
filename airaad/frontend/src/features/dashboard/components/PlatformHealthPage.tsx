import { useQuery } from '@tanstack/react-query';
import { useChartColors } from '@/shared/hooks/useChartColors';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import {
  Store, MapPin, Tag, CheckCircle, Clock,
  Upload, Activity, Search, Bell,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Badge } from '@/shared/components/dls/Badge';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { RoleGate } from '@/shared/components/RoleGate';
import { formatStatus, formatLabel, formatDateTime } from '@/shared/utils/formatters';
import styles from './PlatformHealthPage.module.css';

const QC_COLORS: Record<string, string> = {
  APPROVED: '#0D9488',
  PENDING_QC: '#F97316',
  REJECTED: '#DC2626',
  NEEDS_REVISIT: '#F97316',
  DRAFT: '#A8A29E',
};

interface SystemAlert {
  level: 'error' | 'warning' | 'info';
  message: string;
}

interface RecentActivity {
  action: string;
  actor: string;
  target_type: string;
  created_at: string;
}

interface KPIData {
  total_vendors: number;
  vendors_pending_qa: number;
  vendors_approved_today: number;
  total_areas: number;
  total_tags: number;
  imports_processing: number;
  daily_vendor_counts: Array<{ date: string; count: number }>;
  qc_status_breakdown: Record<string, number>;
  import_activity: Array<{ date: string; total: number }>;
  top_search_terms: Array<{ query: string; count: number }>;
  system_alerts: SystemAlert[];
  recent_activity: RecentActivity[];
}

interface KPIResponse {
  success: boolean;
  data: KPIData;
}

interface HealthStatus {
  status: 'ok' | 'degraded' | 'down';
  db: string;
  cache: string;
  version?: string | undefined;
}

interface HealthResponse {
  status: string;
  db: string;
  cache: string;
  version?: string | undefined;
}

interface MetricCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  variant?: 'default' | 'warning' | 'success';
}


const ALERT_VARIANT: Record<string, 'error' | 'warning' | 'neutral'> = {
  error: 'error',
  warning: 'warning',
  info: 'neutral',
};

function MetricCard({ label, value, icon, variant = 'default' }: MetricCardProps) {
  return (
    <div className={[styles.metricCard, styles[`metricCard--${variant}`]].join(' ')}>
      <span className={styles.metricIcon} aria-hidden="true">{icon}</span>
      <div>
        <p className={styles.metricValue}>{typeof value === 'number' ? value.toLocaleString() : value}</p>
        <p className={styles.metricLabel}>{label}</p>
      </div>
    </div>
  );
}

const HEALTH_VARIANT: Record<string, 'success' | 'warning' | 'error'> = {
  ok: 'success',
  degraded: 'warning',
  down: 'error',
};

export default function PlatformHealthPage() {
  const chartColors = useChartColors();
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.analytics.kpis(),
    queryFn: () =>
      apiClient.get<KPIResponse>('/api/v1/analytics/kpis/').then((r) => r.data.data),
    refetchInterval: 60_000,
  });

  const { data: health } = useQuery<HealthStatus>({
    queryKey: queryKeys.health.status(),
    queryFn: (): Promise<HealthStatus> =>
      apiClient.get<HealthResponse>('/api/v1/health/').then((r) => {
        const rawStatus = r.data.status;
        const status: 'ok' | 'degraded' | 'down' =
          (rawStatus === 'ok' || rawStatus === 'healthy') ? 'ok' : rawStatus === 'degraded' ? 'degraded' : 'down';
        const result: HealthStatus = { status, db: r.data.db, cache: r.data.cache };
        if (r.data.version !== undefined) {
          result.version = r.data.version;
        }
        return result;
      }),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });

  return (
    <AdminLayout title="Dashboard">
      <PageHeader
        heading="Dashboard"
        subheading="Real-time platform health and data collection overview"
        actions={
          health ? (
            <Badge
              variant={HEALTH_VARIANT[health.status] ?? 'neutral'}
              label={`System: ${formatStatus(health.status)}`}
            />
          ) : undefined
        }
      />

      {isLoading ? (
        <SkeletonTable rows={3} columns={4} showHeader={false} />
      ) : (
        <>
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'ANALYST']}>
          {/* ── KPI Cards ── */}
          <div className={styles.metricsGrid} role="list" aria-label="Platform metrics">
            <div key="total-vendors" role="listitem">
              <MetricCard
                label="Total Vendors"
                value={data?.total_vendors ?? 0}
                icon={<Store size={20} strokeWidth={1.5} />}
              />
            </div>
            <div key="pending-qa" role="listitem">
              <MetricCard
                label="Pending QA"
                value={data?.vendors_pending_qa ?? 0}
                icon={<Clock size={20} strokeWidth={1.5} />}
                variant={data && data.vendors_pending_qa > 50 ? 'warning' : 'default'}
              />
            </div>
            <div key="approved-today" role="listitem">
              <MetricCard
                label="Approved Today"
                value={data?.vendors_approved_today ?? 0}
                icon={<CheckCircle size={20} strokeWidth={1.5} />}
                variant="success"
              />
            </div>
            <div key="total-areas" role="listitem">
              <MetricCard
                label="Total Areas"
                value={data?.total_areas ?? 0}
                icon={<MapPin size={20} strokeWidth={1.5} />}
              />
            </div>
            <div key="total-tags" role="listitem">
              <MetricCard
                label="Total Tags"
                value={data?.total_tags ?? 0}
                icon={<Tag size={20} strokeWidth={1.5} />}
              />
            </div>
            <div key="imports-processing" role="listitem">
              <MetricCard
                label="Imports Processing"
                value={data?.imports_processing ?? 0}
                icon={<Upload size={20} strokeWidth={1.5} />}
                variant={data && data.imports_processing > 0 ? 'warning' : 'default'}
              />
            </div>
          </div>

          {/* ── Charts row ── */}
          <div className={styles.chartsRow}>
            {/* Vendors Added bar chart */}
            {data?.daily_vendor_counts && data.daily_vendor_counts.length > 0 && (
              <section className={styles.chartSection} aria-label="Daily vendor additions">
                <h2 className={styles.sectionHeading}>Vendors Added — Last 14 Days</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.daily_vendor_counts} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridStroke} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: '8px', fontSize: 12, color: chartColors.tickFill }} />
                    <Bar dataKey="count" fill={chartColors.barOrange} radius={[4, 4, 0, 0]} name="Vendors" />
                  </BarChart>
                </ResponsiveContainer>
              </section>
            )}

            {/* QC Status donut */}
            {data?.qc_status_breakdown && Object.keys(data.qc_status_breakdown).length > 0 && (
              <section className={styles.chartSection} aria-label="QC status breakdown">
                <h2 className={styles.sectionHeading}>QC Status Breakdown</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={Object.entries(data.qc_status_breakdown).map(([status, count]) => ({ status, count }))}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={2}
                    >
                      {Object.entries(data.qc_status_breakdown).map(([status], index) => (
                        <Cell
                          key={`${status}-${index}`}
                          fill={QC_COLORS[status] ?? chartColors.fallback}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: '8px', fontSize: 12, color: chartColors.tickFill }}
                      formatter={(value: number, name: string) => [value.toLocaleString(), name]}
                    />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </section>
            )}
          </div>

          {/* ── Import Activity chart ── */}
          {data?.import_activity && data.import_activity.length > 0 && (
            <section className={styles.chartSection} aria-label="Import activity">
              <h2 className={styles.sectionHeading}>
                <Upload size={16} strokeWidth={1.5} aria-hidden="true" />
                Import Activity — Last 7 Days
              </h2>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={data.import_activity} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridStroke} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: '8px', fontSize: 12, color: chartColors.tickFill }} />
                  <Bar dataKey="total" fill={chartColors.barTeal} radius={[3, 3, 0, 0]} name="Imports" />
                </BarChart>
              </ResponsiveContainer>
            </section>
          )}
          </RoleGate>
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'ANALYST']}>
          {/* ── Bottom row: Search Terms + Alerts + Activity ── */}
          <div className={styles.bottomRow}>
            {/* Top Search Terms */}
            {data?.top_search_terms && data.top_search_terms.length > 0 && (
              <section className={styles.listSection} aria-label="Top search terms">
                <h2 className={styles.sectionHeading}>
                  <Search size={16} strokeWidth={1.5} aria-hidden="true" />
                  Top Search Terms
                </h2>
                <ol className={styles.searchList}>
                  {data.top_search_terms.slice(0, 10).map((t, i) => (
                    <li key={`search-${i}-${t.query}`} className={styles.searchItem}>
                      <span className={styles.searchRank}>{i + 1}</span>
                      <span className={styles.searchTerm}>{t.query}</span>
                      <span className={styles.searchCount}>{t.count.toLocaleString()}</span>
                      <div
                        className={styles.searchBar}
                        style={{ ['--search-bar-width' as string]: `${(t.count / (data.top_search_terms[0]?.count || 1)) * 100}%` } as React.CSSProperties}
                        aria-hidden="true"
                      />
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {/* System Alerts */}
            {data?.system_alerts && data.system_alerts.length > 0 && (
              <section className={styles.listSection} aria-label="System alerts">
                <h2 className={styles.sectionHeading}>
                  <Bell size={16} strokeWidth={1.5} aria-hidden="true" />
                  System Alerts
                </h2>
                <ul className={styles.alertList}>
                  {data.system_alerts.map((alert, i) => (
                    <li key={`alert-${i}`} className={[styles.alertItem, styles[`alertItem--${alert.level === 'error' ? 'high' : alert.level === 'warning' ? 'med' : 'low'}`]].join(' ')}>
                      <div className={styles.alertTop}>
                        <Badge
                          variant={ALERT_VARIANT[alert.level] ?? 'neutral'}
                          label={formatLabel(alert.level)}
                          size="sm"
                        />
                        <p className={styles.alertMessage}>{alert.message}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Recent Activity */}
            {data?.recent_activity && data.recent_activity.length > 0 && (
              <section className={styles.listSection} aria-label="Recent activity">
                <h2 className={styles.sectionHeading}>
                  <Activity size={16} strokeWidth={1.5} aria-hidden="true" />
                  Recent Activity
                </h2>
                <ul className={styles.activityList}>
                  {data.recent_activity.slice(0, 10).map((entry, i) => (
                    <li key={`activity-${i}`} className={styles.activityItem}>
                      <div className={styles.activityDot} aria-hidden="true" />
                      <div className={styles.activityContent}>
                        <span className={styles.activityAction}>{formatLabel(entry.action)}</span>
                        <span className={styles.activityMeta}>
                          {entry.actor} · {entry.target_type} · {formatDateTime(entry.created_at)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
                <Link to="/system/audit" className={styles.viewAllLink}>
                  View full audit log →
                </Link>
              </section>
            )}
          </div>
          </RoleGate>
        </>
      )}
    </AdminLayout>
  );
}
