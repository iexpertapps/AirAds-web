import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { ChevronDown, ChevronRight, Download } from 'lucide-react';
import Papa from 'papaparse';
import ReactDiffViewer from 'react-diff-viewer-continued';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { FiltersBar } from '@/shared/components/dls/FiltersBar';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useToast } from '@/shared/hooks/useToast';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { formatLabel } from '@/shared/utils/formatters';
import styles from './AuditLogPage.module.css';

interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  actor_label: string;
  target_type: string;
  target_id: string;
  request_id?: string;
  ip_address?: string;
  before_state?: Record<string, unknown>;
  after_state?: Record<string, unknown>;
}

interface AuditResponse {
  count: number;
  data: AuditEntry[];
}

const TARGET_TYPE_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'vendor', label: 'Vendor' },
  { value: 'tag', label: 'Tag' },
  { value: 'city', label: 'City' },
  { value: 'area', label: 'Area' },
  { value: 'user', label: 'User' },
  { value: 'import', label: 'Import' },
];

const MAX_EXPORT_RECORDS = 10_000;

export default function AuditLogPage() {
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const action = searchParams.get('action') ?? '';
  const actorLabel = searchParams.get('actor_label') ?? '';
  const targetType = searchParams.get('target_type') ?? '';
  const page = parseInt(searchParams.get('page') ?? '1', 10);

  const debouncedAction = useDebounce(action);
  const debouncedActor = useDebounce(actorLabel);

  function updateParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) { next.set(key, value); } else { next.delete(key); }
      next.set('page', '1');
      return next;
    });
  }

  const filters = {
    action: debouncedAction || undefined,
    actor_label: debouncedActor || undefined,
    target_type: targetType || undefined,
    page,
    page_size: 50,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.audit.list(filters),
    queryFn: () =>
      apiClient
        .get<AuditResponse>('/api/v1/audit/', { params: filters })
        .then((r) => r.data),
  });

  async function handleExportCSV() {
    setExporting(true);
    try {
      const allEntries: AuditEntry[] = [];
      let currentPage = 1;
      const pageSize = 200;

      while (allEntries.length < MAX_EXPORT_RECORDS) {
        const resp = await apiClient.get<AuditResponse>('/api/v1/audit/', {
          params: { ...filters, page: currentPage, page_size: pageSize },
        });
        const batch = resp.data.data;
        allEntries.push(...batch);
        if (batch.length < pageSize || allEntries.length >= MAX_EXPORT_RECORDS) break;
        currentPage++;
      }

      const csv = Papa.unparse(
        allEntries.slice(0, MAX_EXPORT_RECORDS).map((e) => ({
          timestamp: e.timestamp,
          action: e.action,
          actor: e.actor_label,
          target_type: e.target_type,
          target_id: e.target_id,
          request_id: e.request_id ?? '',
          ip_address: e.ip_address ?? '',
        })),
      );

      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported ${Math.min(allEntries.length, MAX_EXPORT_RECORDS).toLocaleString()} records`);
    } catch {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  }

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  const columns: ColumnDef<AuditEntry>[] = [
    {
      key: 'expand',
      header: '',
      width: '40px',
      render: (e) => (
        <button
          className={styles.expandBtn}
          onClick={() => toggleExpand(e.id)}
          aria-label={expandedId === e.id ? 'Collapse row' : 'Expand row'}
          aria-expanded={expandedId === e.id}
        >
          {expandedId === e.id
            ? <ChevronDown size={14} aria-hidden="true" />
            : <ChevronRight size={14} aria-hidden="true" />}
        </button>
      ),
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      sortable: true,
      render: (e) => (
        <span className={styles.timestamp}>
          {new Date(e.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (e) => <span className={styles.action}>{formatLabel(e.action)}</span>,
    },
    {
      key: 'actor_label',
      header: 'Actor',
      render: (e) => <span className={styles.actor}>{e.actor_label}</span>,
    },
    {
      key: 'target_type',
      header: 'Target Type',
      render: (e) => <span>{formatLabel(e.target_type)}</span>,
    },
    {
      key: 'target_id',
      header: 'Target ID',
      render: (e) => <code className={styles.targetId}>{e.target_id.slice(0, 8)}…</code>,
    },
    {
      key: 'request_id',
      header: 'Request ID',
      render: (e) => (
        <code className={styles.requestId}>{e.request_id ? e.request_id.slice(0, 8) + '…' : '—'}</code>
      ),
    },
    {
      key: 'ip_address',
      header: 'IP',
      render: (e) => <span className={styles.ip}>{e.ip_address ?? '—'}</span>,
    },
  ];

  const activeFilterCount = [action, actorLabel, targetType].filter(Boolean).length;

  return (
    <AdminLayout title="Audit Log">
      <PageHeader
        heading="Audit Log"
        subheading="Immutable record of all system mutations"
        actions={
          <Button
            variant="secondary"
            leftIcon={<Download size={16} />}
            loading={exporting}
            onClick={() => void handleExportCSV()}
          >
            Export CSV
          </Button>
        }
      />

      <FiltersBar
        activeFilterCount={activeFilterCount}
        onClearFilters={() => {
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete('action');
            next.delete('actor_label');
            next.delete('target_type');
            next.set('page', '1');
            return next;
          });
        }}
        filters={
          <div className={styles.filterRow}>
            <Input
              id="filter-action"
              label="Action"
              value={action}
              onChange={(e) => updateParam('action', e.target.value)}
              placeholder="e.g. VENDOR_APPROVED"
            />
            <Input
              id="filter-actor"
              label="Actor email"
              value={actorLabel}
              onChange={(e) => updateParam('actor_label', e.target.value)}
              placeholder="user@example.com"
            />
            <Select
              id="filter-target-type"
              label="Target type"
              options={TARGET_TYPE_OPTIONS}
              value={targetType}
              onChange={(e) => updateParam('target_type', e.target.value)}
            />
          </div>
        }
      />

      <div className={styles.tableWrapper}>
        <Table
          aria-label="Audit log table"
          columns={columns}
          data={data?.data ?? []}
          isLoading={isLoading}
          isEmpty={!isLoading && (data?.data ?? []).length === 0}
          emptyState={
            <EmptyState
              heading="No audit entries found"
              subheading="Try adjusting your filters."
            />
          }
          pagination={
            data
              ? {
                  page,
                  pageSize: 50,
                  total: data.count,
                  onPageChange: (p) => updateParam('page', String(p)),
                }
              : undefined
          }
        />

        {/* Inline row expansion for diff view */}
        {expandedId && (() => {
          const entry = (data?.data ?? []).find((e) => e.id === expandedId);
          if (!entry) return null;
          return (
            <div className={styles.diffPanel} aria-label="Before/after diff">
              <ReactDiffViewer
                oldValue={JSON.stringify(entry.before_state ?? {}, null, 2)}
                newValue={JSON.stringify(entry.after_state ?? {}, null, 2)}
                splitView
                leftTitle="Before"
                rightTitle="After"
                useDarkTheme={false}
              />
            </div>
          );
        })()}
      </div>
    </AdminLayout>
  );
}
