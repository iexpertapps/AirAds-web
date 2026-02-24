import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { Button } from '@/shared/components/dls/Button';
import { Modal } from '@/shared/components/dls/Modal';
import { Textarea } from '@/shared/components/dls/Textarea';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useToast } from '@/shared/hooks/useToast';
import { formatLabel } from '@/shared/utils/formatters';
import styles from './QAPage.module.css';

interface QAVendor {
  id: string;
  business_name: string;
  city_name?: string;
  area_name?: string;
  data_source: string;
  created_at: string;
}

interface QADashboardResponse {
  success: boolean;
  data: { vendors: QAVendor[] };
}

export default function QAPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [rejectTarget, setRejectTarget] = useState<QAVendor | null>(null);
  const [qcNotes, setQcNotes] = useState('');
  const [qcNotesError, setQcNotesError] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.qa.dashboard(),
    queryFn: () =>
      apiClient.get<QADashboardResponse>('/api/v1/qa/dashboard/').then((r) => r.data.data.vendors),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: 'APPROVED' }),
    onSuccess: (_, id) => {
      toast.success('Vendor approved');
      qc.setQueryData<QAVendor[]>(queryKeys.qa.dashboard(), (old) =>
        old ? old.filter((v) => v.id !== id) : old,
      );
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, notes }: { id: string; notes: string }) =>
      apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: 'REJECTED', qc_notes: notes }),
    onSuccess: (_, { id }) => {
      toast.success('Vendor rejected');
      setRejectTarget(null);
      setQcNotes('');
      qc.setQueryData<QAVendor[]>(queryKeys.qa.dashboard(), (old) =>
        old ? old.filter((v) => v.id !== id) : old,
      );
    },
  });

  async function handleBulkApprove() {
    setBulkConfirmOpen(false);
    let approved = 0;
    for (const id of selectedIds) {
      try {
        await apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, { qc_status: 'APPROVED' });
        approved++;
      } catch {
        // continue on individual errors
      }
    }
    toast.success(`${approved} vendor(s) approved`);
    setSelectedIds([]);
    void qc.invalidateQueries({ queryKey: queryKeys.qa.dashboard() });
  }

  function handleRejectSubmit() {
    if (!qcNotes.trim()) {
      setQcNotesError('QC notes are required when rejecting a vendor.');
      return;
    }
    setQcNotesError('');
    if (rejectTarget) {
      rejectMutation.mutate({ id: rejectTarget.id, notes: qcNotes });
    }
  }

  function daysWaiting(createdAt: string): number {
    return Math.floor((Date.now() - new Date(createdAt).getTime()) / 86_400_000);
  }

  const columns: ColumnDef<QAVendor>[] = [
    {
      key: 'business_name',
      header: 'Vendor',
      render: (v) => <span className={styles.vendorName}>{v.business_name}</span>,
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
      key: 'data_source',
      header: 'Source',
      render: (v) => <span>{formatLabel(v.data_source)}</span>,
    },
    {
      key: 'days_waiting',
      header: 'Days Waiting',
      sortable: true,
      render: (v) => {
        const days = daysWaiting(v.created_at);
        return (
          <span className={days > 7 ? styles.urgentDays : ''}>
            {days}d
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (v) => (
        <div className={styles.actions}>
          <Button
            variant="secondary"
            size="compact"
            leftIcon={<CheckCircle size={14} />}
            loading={approveMutation.isPending && approveMutation.variables === v.id}
            onClick={() => approveMutation.mutate(v.id)}
            aria-label={`Approve ${v.business_name}`}
          >
            Approve
          </Button>
          <Button
            variant="ghost"
            size="compact"
            leftIcon={<XCircle size={14} />}
            onClick={() => { setRejectTarget(v); setQcNotes(''); setQcNotesError(''); }}
            aria-label={`Reject ${v.business_name}`}
          >
            Reject
          </Button>
        </div>
      ),
    },
  ];

  return (
    <AdminLayout title="QA Dashboard">
      <PageHeader
        heading="QA Dashboard"
        subheading="Review vendors flagged for quality assurance"
        actions={
          <div className={styles.headerActions}>
            {selectedIds.length > 0 && (
              <Button
                variant="primary"
                size="compact"
                onClick={() => setBulkConfirmOpen(true)}
              >
                Approve {selectedIds.length} selected
              </Button>
            )}
            </div>
        }
      />

      <section aria-label="Vendors needing review">
        <h2 className={styles.sectionHeading}>
          Needs Review Queue
          {data && <span className={styles.count}>{data.length}</span>}
        </h2>
        <Table
          aria-label="QA review queue"
          columns={columns}
          data={data ?? []}
          isLoading={isLoading}
          isEmpty={!isLoading && (data ?? []).length === 0}
          emptyState={
            <EmptyState
              heading="Queue is clear"
              subheading="No vendors are currently flagged for review."
            />
          }
          selectable
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />
      </section>

      {/* Reject Modal */}
      <Modal
        isOpen={rejectTarget !== null}
        onClose={() => { setRejectTarget(null); setQcNotes(''); setQcNotesError(''); }}
        title="Reject Vendor"
        description={`Rejecting "${rejectTarget?.business_name}". QC notes are required.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={rejectMutation.isPending}
              onClick={handleRejectSubmit}
            >
              Reject
            </Button>
          </>
        }
      >
        <Textarea
          id="qa-reject-notes"
          label="QC Notes"
          required
          rows={4}
          value={qcNotes}
          onChange={(e) => setQcNotes(e.target.value)}
          error={qcNotesError}
          placeholder="Explain why this vendor is being rejected…"
        />
      </Modal>

      {/* Bulk Approve Confirmation */}
      <Modal
        isOpen={bulkConfirmOpen}
        onClose={() => setBulkConfirmOpen(false)}
        title="Bulk Approve"
        description={`Approve ${selectedIds.length} vendor(s)?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setBulkConfirmOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={() => void handleBulkApprove()}>
              Approve All
            </Button>
          </>
        }
      >
        <p className={styles.bulkNote}>
          This will approve {selectedIds.length} vendor(s) and remove them from the review queue.
        </p>
      </Modal>
    </AdminLayout>
  );
}
