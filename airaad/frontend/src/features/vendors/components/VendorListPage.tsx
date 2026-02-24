import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useSearchParams, Link } from 'react-router-dom';
import { Plus, CheckCircle, XCircle, Trash2, Flag, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { FiltersBar } from '@/shared/components/dls/FiltersBar';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { QCStatusBadge } from '@/shared/components/dls/Badge';
import { Badge } from '@/shared/components/dls/Badge';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Textarea } from '@/shared/components/dls/Textarea';
import { Select } from '@/shared/components/dls/Select';
import { Modal } from '@/shared/components/dls/Modal';
import { Drawer } from '@/shared/components/dls/Drawer';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { RoleGate } from '@/shared/components/RoleGate';
import { useToast } from '@/shared/hooks/useToast';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { formatStatus, formatLabel } from '@/shared/utils/formatters';
import styles from './VendorListPage.module.css';

type QCStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW' | 'FLAGGED';

interface GeoCity {
  id: string;
  name: string;
}

interface GeoArea {
  id: string;
  name: string;
  city_id: string;
}

interface GeoCityListResponse {
  data: GeoCity[];
}

interface GeoAreaListResponse {
  data: GeoArea[];
}

interface Vendor {
  id: string;
  business_name: string;
  city_name?: string;
  area_name?: string;
  qc_status: QCStatus;
  data_source: string;
  phone?: string;
  created_at: string;
}

interface VendorListResponse {
  count: number;
  data: Vendor[];
}

const QC_STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'PENDING', label: 'Pending' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'NEEDS_REVIEW', label: 'Needs Review' },
  { value: 'FLAGGED', label: 'Flagged' },
];

const DATA_SOURCE_OPTIONS = [
  { value: '', label: 'All sources' },
  { value: 'MANUAL', label: 'Manual' },
  { value: 'CSV_IMPORT', label: 'CSV Import' },
  { value: 'FIELD_AGENT', label: 'Field Agent' },
];

const createVendorSchema = z.object({
  business_name: z.string().min(1, 'Business name is required'),
  phone: z.string().optional(),
  website: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  description: z.string().optional(),
});

type CreateVendorForm = z.infer<typeof createVendorSchema>;

function maskPhone(phone: string): string {
  if (phone.length < 4) return '••••';
  return phone.slice(0, -4).replace(/./g, '•') + phone.slice(-4);
}

export default function VendorListPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [deleteVendor, setDeleteVendor] = useState<Vendor | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [bulkAction, setBulkAction] = useState<'approve' | 'flag' | null>(null);
  const [rejectTarget, setRejectTarget] = useState<Vendor | null>(null);
  const [rejectNotes, setRejectNotes] = useState('');
  const [rejectNotesError, setRejectNotesError] = useState('');

  const createForm = useForm<CreateVendorForm>({ resolver: zodResolver(createVendorSchema) });

  const search = searchParams.get('search') ?? '';
  const qcStatus = searchParams.get('qc_status') ?? '';
  const dataSource = searchParams.get('data_source') ?? '';
  const cityId = searchParams.get('city_id') ?? '';
  const areaId = searchParams.get('area_id') ?? '';
  const page = parseInt(searchParams.get('page') ?? '1', 10);
  const debouncedSearch = useDebounce(search);

  function updateParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) {
        next.set(key, value);
      } else {
        next.delete(key);
      }
      next.set('page', '1');
      return next;
    });
  }

  const { data: cities } = useQuery({
    queryKey: queryKeys.geo.cities(),
    queryFn: () =>
      apiClient.get<GeoCityListResponse>('/api/v1/geo/cities/').then((r) => r.data.data),
  });

  const { data: areas } = useQuery({
    queryKey: queryKeys.geo.areas(cityId ? { city: cityId } : undefined),
    queryFn: () =>
      apiClient
        .get<GeoAreaListResponse>('/api/v1/geo/areas/', { params: cityId ? { city: cityId } : {} })
        .then((r) => r.data.data),
    enabled: !!cityId,
  });

  const filters = {
    search: debouncedSearch || undefined,
    qc_status: qcStatus || undefined,
    data_source: dataSource || undefined,
    city_id: cityId || undefined,
    area_id: areaId || undefined,
    page,
    page_size: 25,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.vendors.list(filters),
    queryFn: () =>
      apiClient
        .get<VendorListResponse>('/api/v1/vendors/', { params: filters })
        .then((r) => r.data),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) =>
      apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: 'REJECTED', qc_notes: notes }),
    onSuccess: () => {
      toast.success('Vendor rejected');
      setRejectTarget(null);
      setRejectNotes('');
      setRejectNotesError('');
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.list(filters) });
    },
    onError: () => toast.error('Failed to reject vendor'),
  });

  const qcMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: QCStatus }) =>
      apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: status }),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: queryKeys.vendors.list(filters) });
      const prev = qc.getQueryData<VendorListResponse>(queryKeys.vendors.list(filters));
      qc.setQueryData<VendorListResponse>(queryKeys.vendors.list(filters), (old) =>
        old
          ? { ...old, data: old.data.map((v) => (v.id === id ? { ...v, qc_status: status } : v)) }
          : old,
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.vendors.list(filters), ctx.prev);
      toast.error('Failed to update QC status');
    },
    onSuccess: () => void qc.invalidateQueries({ queryKey: queryKeys.vendors.list(filters) }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/v1/vendors/${id}/`),
    onSuccess: () => {
      toast.success('Vendor deleted');
      setDeleteVendor(null);
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.list(filters) });
    },
  });

  const createMutation = useMutation({
    mutationFn: (d: CreateVendorForm) =>
      apiClient.post('/api/v1/vendors/', { ...d, data_source: 'MANUAL_ENTRY' }),
    onSuccess: () => {
      toast.success('Vendor created');
      setCreateDrawerOpen(false);
      createForm.reset();
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.list(filters) });
    },
    onError: () => toast.error('Failed to create vendor'),
  });

  async function handleBulkAction(status: QCStatus) {
    setBulkAction(null);
    let count = 0;
    for (const id of selectedIds) {
      try {
        await apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: status });
        count++;
      } catch { /* continue */ }
    }
    toast.success(`${count} vendor(s) ${formatStatus(status).toLowerCase()}`);
    setSelectedIds([]);
    void qc.invalidateQueries({ queryKey: queryKeys.vendors.list(filters) });
  }

  const columns: ColumnDef<Vendor>[] = [
    {
      key: 'business_name',
      header: 'Business Name',
      sortable: true,
      render: (v) => (
        <Link to={`/vendors/${v.id}`} className={styles.nameLink}>
          {v.business_name}
        </Link>
      ),
    },
    {
      key: 'location',
      header: 'Location',
      render: (v) => (
        <span className={styles.location}>
          {[v.city_name, v.area_name].filter(Boolean).join(' › ')}
        </span>
      ),
    },
    {
      key: 'qc_status',
      header: 'QC Status',
      render: (v) => <QCStatusBadge status={v.qc_status} />,
    },
    {
      key: 'data_source',
      header: 'Source',
      render: (v) => <Badge variant="neutral" label={formatLabel(v.data_source)} />,
    },
    {
      key: 'phone',
      header: 'Phone',
      render: (v) => (
        <span className={styles.phone}>{v.phone ? maskPhone(v.phone) : '—'}</span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      sortable: true,
      render: (v) => (
        <span className={styles.date}>
          {new Date(v.created_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (v) => (
        <div className={styles.actions}>
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER']}>
            {v.qc_status !== 'APPROVED' && (
              <Button
                variant="ghost"
                size="compact"
                aria-label={`Approve ${v.business_name}`}
                onClick={() => qcMutation.mutate({ id: v.id, status: 'APPROVED' })}
              >
                <CheckCircle size={14} />
              </Button>
            )}
            {v.qc_status !== 'REJECTED' && (
              <Button
                variant="ghost"
                size="compact"
                aria-label={`Reject ${v.business_name}`}
                onClick={() => { setRejectTarget(v); setRejectNotes(''); setRejectNotesError(''); }}
              >
                <XCircle size={14} />
              </Button>
            )}
          </RoleGate>
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
            <Button
              variant="ghost"
              size="compact"
              aria-label={`Delete ${v.business_name}`}
              onClick={() => setDeleteVendor(v)}
            >
              <Trash2 size={14} />
            </Button>
          </RoleGate>
        </div>
      ),
    },
  ];

  function handleRejectSubmit() {
    if (!rejectNotes.trim()) {
      setRejectNotesError('QC notes are required when rejecting a vendor.');
      return;
    }
    setRejectNotesError('');
    if (rejectTarget) rejectMutation.mutate({ id: rejectTarget.id, notes: rejectNotes });
  }

  function handleCityChange(newCityId: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (newCityId) { next.set('city_id', newCityId); } else { next.delete('city_id'); }
      next.delete('area_id');
      next.set('page', '1');
      return next;
    });
  }

  const activeFilterCount = [qcStatus, dataSource, cityId, areaId].filter(Boolean).length;

  return (
    <AdminLayout title="Vendors">
      <PageHeader
        heading="Vendor Management"
        subheading={data ? `${data.count.toLocaleString()} vendors` : undefined}
        actions={
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY']}>
            <div className={styles.headerActions}>
              {selectedIds.length > 0 && (
                <>
                  <Button
                    variant="secondary"
                    size="compact"
                    leftIcon={<CheckCircle size={14} />}
                    onClick={() => setBulkAction('approve')}
                  >
                    Approve {selectedIds.length}
                  </Button>
                  <Button
                    variant="secondary"
                    size="compact"
                    leftIcon={<Flag size={14} />}
                    onClick={() => setBulkAction('flag')}
                  >
                    Flag {selectedIds.length}
                  </Button>
                </>
              )}
              <Button
                variant="primary"
                leftIcon={<Plus size={16} />}
                onClick={() => setCreateDrawerOpen(true)}
              >
                Add Vendor
              </Button>
            </div>
          </RoleGate>
        }
      />

      <FiltersBar
        search={search}
        onSearchChange={(v) => updateParam('search', v)}
        searchPlaceholder="Search vendors…"
        activeFilterCount={activeFilterCount}
        onClearFilters={() => {
          setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete('qc_status');
            next.delete('data_source');
            next.delete('city_id');
            next.delete('area_id');
            next.delete('search');
            next.set('page', '1');
            return next;
          });
        }}
        filters={
          <>
            <Select
              id="filter-qc"
              label="QC Status"
              options={QC_STATUS_OPTIONS}
              value={qcStatus}
              onChange={(e) => updateParam('qc_status', e.target.value)}
              className={styles.filterSelect}
            />
            <Select
              id="filter-source"
              label="Data Source"
              options={DATA_SOURCE_OPTIONS}
              value={dataSource}
              onChange={(e) => updateParam('data_source', e.target.value)}
              className={styles.filterSelect}
            />
            <Select
              id="filter-city"
              label="City"
              options={[
                { value: '', label: 'All cities' },
                ...(cities ?? []).map((c) => ({ value: c.id, label: c.name })),
              ]}
              value={cityId}
              onChange={(e) => handleCityChange(e.target.value)}
              className={styles.filterSelect}
            />
            {cityId && (
              <Select
                id="filter-area"
                label="Area"
                options={[
                  { value: '', label: 'All areas' },
                  ...(areas ?? []).map((a) => ({ value: a.id, label: a.name })),
                ]}
                value={areaId}
                onChange={(e) => updateParam('area_id', e.target.value)}
                className={styles.filterSelect}
              />
            )}
          </>
        }
      />

      <Table
        aria-label="Vendors table"
        columns={columns}
        data={data?.data ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (data?.data ?? []).length === 0}
        emptyState={
          <EmptyState
            heading="No vendors found"
            subheading="Try adjusting your filters or add a new vendor."
          />
        }
        selectable
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
        pagination={
          data
            ? {
                page,
                pageSize: 25,
                total: data.count,
                onPageChange: (p) => updateParam('page', String(p)),
              }
            : undefined
        }
      />

      <Modal
        isOpen={deleteVendor !== null}
        onClose={() => setDeleteVendor(null)}
        title="Delete Vendor"
        description={`Are you sure you want to delete "${deleteVendor?.business_name}"?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteVendor(null)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => deleteVendor && deleteMutation.mutate(deleteVendor.id)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>This action cannot be undone. The vendor will be soft-deleted.</p>
      </Modal>

      {/* Bulk Action Confirmation */}
      <Modal
        isOpen={bulkAction !== null}
        onClose={() => setBulkAction(null)}
        title={bulkAction === 'approve' ? 'Bulk Approve' : 'Bulk Flag'}
        description={`${bulkAction === 'approve' ? 'Approve' : 'Flag'} ${selectedIds.length} vendor(s)?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setBulkAction(null)}>Cancel</Button>
            <Button
              variant="primary"
              onClick={() => bulkAction && void handleBulkAction(bulkAction === 'approve' ? 'APPROVED' : 'FLAGGED')}
            >
              Confirm
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>
          This will update the QC status for {selectedIds.length} selected vendor(s).
        </p>
      </Modal>

      {/* Reject Vendor Modal */}
      <Modal
        isOpen={rejectTarget !== null}
        onClose={() => { setRejectTarget(null); setRejectNotes(''); setRejectNotesError(''); }}
        title="Reject Vendor"
        description={`Provide a reason for rejecting "${rejectTarget?.business_name ?? ''}".`}
        footer={
          <>
            <Button variant="secondary" onClick={() => { setRejectTarget(null); setRejectNotes(''); setRejectNotesError(''); }}>Cancel</Button>
            <Button
              variant="destructive"
              leftIcon={<AlertCircle size={14} />}
              loading={rejectMutation.isPending}
              onClick={handleRejectSubmit}
            >
              Reject Vendor
            </Button>
          </>
        }
      >
        <Textarea
          id="reject-vendor-notes"
          label="QC Notes"
          required
          rows={4}
          value={rejectNotes}
          onChange={(e) => setRejectNotes(e.target.value)}
          error={rejectNotesError}
          placeholder="Explain why this vendor is being rejected…"
        />
      </Modal>

      {/* Create Vendor Drawer */}
      <Drawer
        isOpen={createDrawerOpen}
        onClose={() => { setCreateDrawerOpen(false); createForm.reset(); }}
        title="Add Vendor"
        description="Create a new vendor record manually."
        footer={
          <Button
            variant="primary"
            loading={createMutation.isPending}
            onClick={createForm.handleSubmit((d) => createMutation.mutate(d))}
          >
            Create Vendor
          </Button>
        }
      >
        <form
          className={styles.drawerForm}
          onSubmit={createForm.handleSubmit((d) => createMutation.mutate(d))}
        >
          <Input
            id="create-vendor-name"
            label="Business name"
            required
            error={createForm.formState.errors.business_name?.message}
            {...createForm.register('business_name')}
          />
          <Input
            id="create-vendor-phone"
            label="Phone number"
            type="tel"
            error={createForm.formState.errors.phone?.message}
            {...createForm.register('phone')}
          />
          <Input
            id="create-vendor-website"
            label="Website"
            type="url"
            placeholder="https://"
            error={createForm.formState.errors.website?.message}
            {...createForm.register('website')}
          />
          <Textarea
            id="create-vendor-desc"
            label="Description"
            rows={3}
            error={createForm.formState.errors.description?.message}
            {...createForm.register('description')}
          />
        </form>
      </Drawer>
    </AdminLayout>
  );
}
