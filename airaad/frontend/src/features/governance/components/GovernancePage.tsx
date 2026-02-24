import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Ban, ShieldOff, ShieldCheck, Flag } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { Button } from '@/shared/components/dls/Button';
import { Badge } from '@/shared/components/dls/Badge';
import { Modal } from '@/shared/components/dls/Modal';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { Textarea } from '@/shared/components/dls/Textarea';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { FiltersBar } from '@/shared/components/dls/FiltersBar';
import { useToast } from '@/shared/hooks/useToast';
import { useAuthStore } from '@/features/auth/store/authStore';
import { formatStatus, formatActiveStatus, formatLabel } from '@/shared/utils/formatters';
import styles from './GovernancePage.module.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FraudScore {
  id: string;
  vendor_id: string;
  vendor_name?: string;
  score: number;
  signals: string[];
  is_auto_suspended: boolean;
  updated_at: string;
}

interface BlacklistEntry {
  id: string;
  blacklist_type: 'PHONE_NUMBER' | 'DEVICE_ID' | 'GPS_COORDINATE';
  value: string;
  reason: string;
  is_active: boolean;
  added_by_email?: string;
  created_at: string;
}

interface VendorSuspension {
  id: string;
  vendor_id: string;
  vendor_name?: string;
  action: 'WARNING' | 'CONTENT_REMOVAL' | 'TEMPORARY_SUSPENSION' | 'PERMANENT_BAN';
  reason: string;
  policy_reference: string;
  is_active: boolean;
  appeal_status: 'NONE' | 'PENDING' | 'APPROVED' | 'REJECTED';
  suspension_ends_at: string | null;
  created_at: string;
}

interface PaginatedResponse<T> {
  count: number;
  results: T[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const WRITE_ROLES = ['SUPER_ADMIN', 'OPERATIONS_MANAGER'] as const;
type WriteRole = (typeof WRITE_ROLES)[number];

function useCanWrite(): boolean {
  const role = useAuthStore((s) => s.user?.role);
  return WRITE_ROLES.includes(role as WriteRole);
}

function ScoreCell({ score }: { score: number }) {
  const cls = score >= 6 ? styles.scoreHigh : score >= 3 ? styles.scoreMed : styles.scoreLow;
  return <span className={cls}>{score}</span>;
}

function SuspensionActionBadge({ action }: { action: VendorSuspension['action'] }) {
  const map: Record<VendorSuspension['action'], { variant: 'error' | 'warning' | 'info' | 'neutral'; label: string }> = {
    WARNING: { variant: 'warning', label: 'Warning' },
    CONTENT_REMOVAL: { variant: 'info', label: 'Content Removal' },
    TEMPORARY_SUSPENSION: { variant: 'warning', label: 'Temp Suspension' },
    PERMANENT_BAN: { variant: 'error', label: 'Permanent Ban' },
  };
  const cfg = map[action];
  return <Badge variant={cfg.variant} label={cfg.label} />;
}

function AppealStatusBadge({ status }: { status: VendorSuspension['appeal_status'] }) {
  const map: Record<VendorSuspension['appeal_status'], { variant: 'neutral' | 'info' | 'success' | 'error'; label: string }> = {
    NONE: { variant: 'neutral', label: 'No Appeal' },
    PENDING: { variant: 'info', label: formatStatus('PENDING') },
    APPROVED: { variant: 'success', label: formatStatus('APPROVED') },
    REJECTED: { variant: 'error', label: formatStatus('REJECTED') },
  };
  const cfg = map[status];
  return <Badge variant={cfg.variant} label={cfg.label} />;
}

// ---------------------------------------------------------------------------
// Tab: Fraud Scores
// ---------------------------------------------------------------------------

function FraudScoresTab() {
  const canWrite = useCanWrite();
  const toast = useToast();
  const qc = useQueryClient();
  const [autoSuspendedFilter, setAutoSuspendedFilter] = useState('');

  const filters = {
    auto_suspended: autoSuspendedFilter === 'true' ? true : autoSuspendedFilter === 'false' ? false : undefined,
    page_size: 50,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.governance.fraudScores(filters),
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<FraudScore>>('/api/v1/governance/fraud-scores/', { params: filters })
        .then((r) => r.data),
  });

  const [signalModal, setSignalModal] = useState(false);
  const [signalVendorId, setSignalVendorId] = useState('');
  const [signalType, setSignalType] = useState('USER_REPORT');
  const [signalReason, setSignalReason] = useState('');

  const addSignalMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/api/v1/governance/fraud-scores/signals/', {
        vendor_id: signalVendorId,
        signal: signalType,
        reason: signalReason,
      }),
    onSuccess: () => {
      toast.success('Fraud signal recorded');
      setSignalModal(false);
      setSignalVendorId('');
      setSignalReason('');
      void qc.invalidateQueries({ queryKey: ['governance', 'fraudScores'] });
    },
    onError: () => toast.error('Failed to record signal'),
  });

  const columns: ColumnDef<FraudScore>[] = [
    {
      key: 'vendor_name',
      header: 'Vendor',
      render: (r) => <span className={styles.mono}>{r.vendor_name ?? r.vendor_id.slice(0, 8) + '…'}</span>,
    },
    {
      key: 'score',
      header: 'Score',
      sortable: true,
      render: (r) => <ScoreCell score={r.score} />,
    },
    {
      key: 'signals',
      header: 'Signals',
      render: (r) => <span>{r.signals.map(formatLabel).join(', ') || '—'}</span>,
    },
    {
      key: 'is_auto_suspended',
      header: 'Auto-Suspended',
      render: (r) =>
        r.is_auto_suspended ? (
          <Badge variant="error" icon={<ShieldOff size={12} />} label="Suspended" />
        ) : (
          <Badge variant="success" icon={<ShieldCheck size={12} />} label="Active" />
        ),
    },
    {
      key: 'updated_at',
      header: 'Last Updated',
      render: (r) => <span>{new Date(r.updated_at).toLocaleDateString()}</span>,
    },
  ];

  const activeFilterCount = autoSuspendedFilter ? 1 : 0;

  return (
    <>
      <div className={styles.sectionHeading}>
        Fraud Scores
        {data && <span className={styles.count}>{data.count}</span>}
      </div>

      <FiltersBar
        activeFilterCount={activeFilterCount}
        onClearFilters={() => setAutoSuspendedFilter('')}
        filters={
          <div className={styles.filterRow}>
            <Select
              id="fraud-filter-suspended"
              label="Auto-suspended"
              options={[
                { value: '', label: 'All' },
                { value: 'true', label: 'Suspended only' },
                { value: 'false', label: 'Active only' },
              ]}
              value={autoSuspendedFilter}
              onChange={(e) => setAutoSuspendedFilter(e.target.value)}
            />
          </div>
        }
      />

      {canWrite && (
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Button
            variant="secondary"
            size="compact"
            leftIcon={<Flag size={14} />}
            onClick={() => setSignalModal(true)}
          >
            Add Fraud Signal
          </Button>
        </div>
      )}

      <Table
        aria-label="Fraud scores table"
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (data?.results ?? []).length === 0}
        emptyState={
          <EmptyState heading="No fraud scores" subheading="No vendors have accumulated fraud signals." />
        }
      />

      {canWrite && (
        <Modal
          isOpen={signalModal}
          onClose={() => setSignalModal(false)}
          title="Add Fraud Signal"
          description="Record a fraud signal against a vendor. Score thresholds: 3–5 manual review, ≥6 auto-suspend."
          footer={
            <>
              <Button variant="secondary" onClick={() => setSignalModal(false)}>Cancel</Button>
              <Button
                variant="destructive"
                loading={addSignalMutation.isPending}
                onClick={() => addSignalMutation.mutate()}
              >
                Record Signal
              </Button>
            </>
          }
        >
          <div className={styles.formGrid}>
            <Input
              id="signal-vendor-id"
              label="Vendor ID"
              required
              value={signalVendorId}
              onChange={(e) => setSignalVendorId(e.target.value)}
              placeholder="UUID of the vendor"
            />
            <Select
              id="signal-type"
              label="Signal Type"
              options={[
                { value: 'USER_REPORT', label: 'User Report (+1)' },
                { value: 'MULTI_CLAIM_SAME_DEVICE', label: 'Multi-Claim Same Device (+2)' },
                { value: 'BLACKLISTED_PHONE', label: 'Blacklisted Phone (+3)' },
                { value: 'GPS_ANOMALY', label: 'GPS Anomaly (+2)' },
                { value: 'EXCESSIVE_PROMOTIONS', label: 'Excessive Promotions (+1)' },
                { value: 'DUPLICATE_CLAIM', label: 'Duplicate Claim (+2)' },
              ]}
              value={signalType}
              onChange={(e) => setSignalType(e.target.value)}
            />
            <Textarea
              id="signal-reason"
              label="Reason"
              rows={3}
              value={signalReason}
              onChange={(e) => setSignalReason(e.target.value)}
              placeholder="Describe the reason for this signal…"
            />
          </div>
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Tab: Blacklist
// ---------------------------------------------------------------------------

function BlacklistTab() {
  const canWrite = useCanWrite();
  const toast = useToast();
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('true');
  const [addModal, setAddModal] = useState(false);
  const [liftTarget, setLiftTarget] = useState<BlacklistEntry | null>(null);
  const [form, setForm] = useState({ blacklist_type: 'PHONE_NUMBER', value: '', reason: '' });

  const filters = {
    blacklist_type: typeFilter || undefined,
    is_active: activeFilter === '' ? undefined : activeFilter === 'true',
    page_size: 50,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.governance.blacklist(filters),
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<BlacklistEntry>>('/api/v1/governance/blacklist/', { params: filters })
        .then((r) => r.data),
  });

  const addMutation = useMutation({
    mutationFn: () => apiClient.post('/api/v1/governance/blacklist/', form),
    onSuccess: () => {
      toast.success('Entry added to blacklist');
      setAddModal(false);
      setForm({ blacklist_type: 'PHONE_NUMBER', value: '', reason: '' });
      void qc.invalidateQueries({ queryKey: ['governance', 'blacklist'] });
    },
    onError: () => toast.error('Failed to add blacklist entry'),
  });

  const liftMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/api/v1/governance/blacklist/${id}/lift/`, {}),
    onSuccess: () => {
      toast.success('Blacklist entry lifted');
      setLiftTarget(null);
      void qc.invalidateQueries({ queryKey: ['governance', 'blacklist'] });
    },
    onError: () => toast.error('Failed to lift entry'),
  });

  const columns: ColumnDef<BlacklistEntry>[] = [
    {
      key: 'blacklist_type',
      header: 'Type',
      render: (r) => <Badge variant="info" label={formatLabel(r.blacklist_type)} />,
    },
    {
      key: 'value',
      header: 'Value',
      render: (r) => <span className={styles.mono}>{r.value}</span>,
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (r) => <span>{r.reason}</span>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (r) =>
        r.is_active ? (
          <Badge variant="error" icon={<Ban size={12} />} label={formatActiveStatus(true)} />
        ) : (
          <Badge variant="neutral" label="Lifted" />
        ),
    },
    {
      key: 'created_at',
      header: 'Added',
      render: (r) => <span>{new Date(r.created_at).toLocaleDateString()}</span>,
    },
    ...(canWrite
      ? [{
          key: 'actions' as const,
          header: 'Actions',
          render: (r: BlacklistEntry) =>
            r.is_active ? (
              <Button
                variant="ghost"
                size="compact"
                onClick={() => setLiftTarget(r)}
              >
                Lift
              </Button>
            ) : null,
        }]
      : []),
  ];

  const activeFilterCount = [typeFilter, activeFilter !== 'true' ? activeFilter : ''].filter(Boolean).length;

  return (
    <>
      <div className={styles.sectionHeading}>
        Blacklist
        {data && <span className={styles.count}>{data.count}</span>}
      </div>

      <FiltersBar
        activeFilterCount={activeFilterCount}
        onClearFilters={() => { setTypeFilter(''); setActiveFilter('true'); }}
        filters={
          <div className={styles.filterRow}>
            <Select
              id="bl-filter-type"
              label="Type"
              options={[
                { value: '', label: 'All types' },
                { value: 'PHONE_NUMBER', label: 'Phone Number' },
                { value: 'DEVICE_ID', label: 'Device ID' },
                { value: 'GPS_COORDINATE', label: 'GPS Coordinate' },
              ]}
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            />
            <Select
              id="bl-filter-active"
              label="Status"
              options={[
                { value: '', label: 'All' },
                { value: 'true', label: 'Active only' },
                { value: 'false', label: 'Lifted only' },
              ]}
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
            />
          </div>
        }
      />

      {canWrite && (
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Button
            variant="secondary"
            size="compact"
            leftIcon={<Ban size={14} />}
            onClick={() => setAddModal(true)}
          >
            Add to Blacklist
          </Button>
        </div>
      )}

      <Table
        aria-label="Blacklist table"
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (data?.results ?? []).length === 0}
        emptyState={
          <EmptyState heading="Blacklist is empty" subheading="No active blacklist entries." />
        }
      />

      {canWrite && (
        <>
          <Modal
            isOpen={addModal}
            onClose={() => setAddModal(false)}
            title="Add Blacklist Entry"
            description="Blacklisted entries are checked during vendor claim and fraud detection."
            footer={
              <>
                <Button variant="secondary" onClick={() => setAddModal(false)}>Cancel</Button>
                <Button
                  variant="destructive"
                  loading={addMutation.isPending}
                  onClick={() => addMutation.mutate()}
                >
                  Add Entry
                </Button>
              </>
            }
          >
            <div className={styles.formGrid}>
              <Select
                id="bl-add-type"
                label="Type"
                options={[
                  { value: 'PHONE_NUMBER', label: 'Phone Number' },
                  { value: 'DEVICE_ID', label: 'Device ID' },
                  { value: 'GPS_COORDINATE', label: 'GPS Coordinate' },
                ]}
                value={form.blacklist_type}
                onChange={(e) => setForm((f) => ({ ...f, blacklist_type: e.target.value }))}
              />
              <Input
                id="bl-add-value"
                label="Value"
                required
                value={form.value}
                onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
                placeholder="Phone number, device ID, or GPS coordinate"
              />
              <Textarea
                id="bl-add-reason"
                label="Reason"
                required
                rows={3}
                value={form.reason}
                onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                placeholder="Reason for blacklisting (required)…"
              />
            </div>
          </Modal>

          <Modal
            isOpen={liftTarget !== null}
            onClose={() => setLiftTarget(null)}
            title="Lift Blacklist Entry"
            description={`Remove "${liftTarget?.value}" from the blacklist?`}
            footer={
              <>
                <Button variant="secondary" onClick={() => setLiftTarget(null)}>Cancel</Button>
                <Button
                  variant="primary"
                  loading={liftMutation.isPending}
                  onClick={() => liftTarget && liftMutation.mutate(liftTarget.id)}
                >
                  Lift Entry
                </Button>
              </>
            }
          >
            <p style={{ font: 'var(--text-body)', color: 'var(--text-primary)' }}>
              This will deactivate the blacklist entry. The vendor or entity will no longer be blocked.
            </p>
          </Modal>
        </>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Tab: Suspensions
// ---------------------------------------------------------------------------

function SuspensionsTab() {
  const canWrite = useCanWrite();
  const toast = useToast();
  const qc = useQueryClient();
  const [actionFilter, setActionFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('true');
  const [issueModal, setIssueModal] = useState(false);
  const [form, setForm] = useState({
    vendor_id: '',
    action: 'WARNING',
    reason: '',
    policy_reference: '',
    suspension_days: '7',
  });

  const filters = {
    action: actionFilter || undefined,
    is_active: activeFilter === '' ? undefined : activeFilter === 'true',
    page_size: 50,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.governance.suspensions(filters),
    queryFn: () =>
      apiClient
        .get<PaginatedResponse<VendorSuspension>>('/api/v1/governance/suspensions/', { params: filters })
        .then((r) => r.data),
  });

  const issueMutation = useMutation({
    mutationFn: () =>
      apiClient.post('/api/v1/governance/suspensions/', {
        ...form,
        suspension_days: parseInt(form.suspension_days, 10),
      }),
    onSuccess: () => {
      toast.success('Enforcement action issued');
      setIssueModal(false);
      setForm({ vendor_id: '', action: 'WARNING', reason: '', policy_reference: '', suspension_days: '7' });
      void qc.invalidateQueries({ queryKey: ['governance', 'suspensions'] });
    },
    onError: () => toast.error('Failed to issue enforcement action'),
  });

  const columns: ColumnDef<VendorSuspension>[] = [
    {
      key: 'vendor_name',
      header: 'Vendor',
      render: (r) => <span className={styles.mono}>{r.vendor_name ?? r.vendor_id.slice(0, 8) + '…'}</span>,
    },
    {
      key: 'action',
      header: 'Action',
      render: (r) => <SuspensionActionBadge action={r.action} />,
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (r) => <span>{r.reason}</span>,
    },
    {
      key: 'is_active',
      header: 'Active',
      render: (r) =>
        r.is_active ? (
          <Badge variant="error" label={formatActiveStatus(true)} />
        ) : (
          <Badge variant="neutral" label="Lifted" />
        ),
    },
    {
      key: 'appeal_status',
      header: 'Appeal',
      render: (r) => <AppealStatusBadge status={r.appeal_status} />,
    },
    {
      key: 'suspension_ends_at',
      header: 'Ends At',
      render: (r) =>
        r.suspension_ends_at ? (
          <span>{new Date(r.suspension_ends_at).toLocaleDateString()}</span>
        ) : (
          <span>—</span>
        ),
    },
    {
      key: 'created_at',
      header: 'Issued',
      render: (r) => <span>{new Date(r.created_at).toLocaleDateString()}</span>,
    },
  ];

  const activeFilterCount = [actionFilter, activeFilter !== 'true' ? activeFilter : ''].filter(Boolean).length;

  return (
    <>
      <div className={styles.sectionHeading}>
        Vendor Suspensions
        {data && <span className={styles.count}>{data.count}</span>}
      </div>

      <FiltersBar
        activeFilterCount={activeFilterCount}
        onClearFilters={() => { setActionFilter(''); setActiveFilter('true'); }}
        filters={
          <div className={styles.filterRow}>
            <Select
              id="susp-filter-action"
              label="Action type"
              options={[
                { value: '', label: 'All actions' },
                { value: 'WARNING', label: 'Warning' },
                { value: 'CONTENT_REMOVAL', label: 'Content Removal' },
                { value: 'TEMPORARY_SUSPENSION', label: 'Temporary Suspension' },
                { value: 'PERMANENT_BAN', label: 'Permanent Ban' },
              ]}
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
            <Select
              id="susp-filter-active"
              label="Status"
              options={[
                { value: '', label: 'All' },
                { value: 'true', label: 'Active only' },
                { value: 'false', label: 'Lifted only' },
              ]}
              value={activeFilter}
              onChange={(e) => setActiveFilter(e.target.value)}
            />
          </div>
        }
      />

      {canWrite && (
        <div style={{ marginBottom: 'var(--space-4)' }}>
          <Button
            variant="destructive"
            size="compact"
            leftIcon={<AlertTriangle size={14} />}
            onClick={() => setIssueModal(true)}
          >
            Issue Enforcement Action
          </Button>
        </div>
      )}

      <Table
        aria-label="Vendor suspensions table"
        columns={columns}
        data={data?.results ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (data?.results ?? []).length === 0}
        emptyState={
          <EmptyState heading="No suspensions" subheading="No enforcement actions have been issued." />
        }
      />

      {canWrite && (
        <Modal
          isOpen={issueModal}
          onClose={() => setIssueModal(false)}
          title="Issue Enforcement Action"
          description="Actions are logged and audited. Temporary suspensions expire automatically."
          footer={
            <>
              <Button variant="secondary" onClick={() => setIssueModal(false)}>Cancel</Button>
              <Button
                variant="destructive"
                loading={issueMutation.isPending}
                onClick={() => issueMutation.mutate()}
              >
                Issue Action
              </Button>
            </>
          }
        >
          <div className={styles.formGrid}>
            <Input
              id="susp-vendor-id"
              label="Vendor ID"
              required
              value={form.vendor_id}
              onChange={(e) => setForm((f) => ({ ...f, vendor_id: e.target.value }))}
              placeholder="UUID of the vendor"
            />
            <Select
              id="susp-action"
              label="Action"
              options={[
                { value: 'WARNING', label: 'Warning' },
                { value: 'CONTENT_REMOVAL', label: 'Content Removal' },
                { value: 'TEMPORARY_SUSPENSION', label: 'Temporary Suspension' },
                { value: 'PERMANENT_BAN', label: 'Permanent Ban' },
              ]}
              value={form.action}
              onChange={(e) => setForm((f) => ({ ...f, action: e.target.value }))}
            />
            {form.action === 'TEMPORARY_SUSPENSION' && (
              <Input
                id="susp-days"
                label="Suspension Duration (days)"
                type="number"
                value={form.suspension_days}
                onChange={(e) => setForm((f) => ({ ...f, suspension_days: e.target.value }))}
              />
            )}
            <Textarea
              id="susp-reason"
              label="Reason"
              required
              rows={3}
              value={form.reason}
              onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
              placeholder="Reason for this enforcement action…"
            />
            <Input
              id="susp-policy"
              label="Policy Reference"
              value={form.policy_reference}
              onChange={(e) => setForm((f) => ({ ...f, policy_reference: e.target.value }))}
              placeholder="e.g. §9.2 Content Policy"
            />
          </div>
        </Modal>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

type TabId = 'fraud' | 'blacklist' | 'suspensions';

const TABS: { id: TabId; label: string }[] = [
  { id: 'fraud', label: 'Fraud Scores' },
  { id: 'blacklist', label: 'Blacklist' },
  { id: 'suspensions', label: 'Suspensions' },
];

export default function GovernancePage() {
  const [activeTab, setActiveTab] = useState<TabId>('fraud');

  return (
    <AdminLayout title="Governance">
      <PageHeader
        heading="Governance"
        subheading="Fraud detection, blacklist management, and vendor enforcement actions"
      />

      <nav className={styles.tabs} aria-label="Governance sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={[styles.tab, activeTab === tab.id ? styles.tabActive : ''].join(' ')}
            onClick={() => setActiveTab(tab.id)}
            aria-selected={activeTab === tab.id}
            role="tab"
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'fraud' && <FraudScoresTab />}
      {activeTab === 'blacklist' && <BlacklistTab />}
      {activeTab === 'suspensions' && <SuspensionsTab />}
    </AdminLayout>
  );
}
