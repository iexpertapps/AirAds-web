import { useState, useMemo, useCallback } from 'react';
import { CheckCircle, XCircle, ClipboardCheck } from 'lucide-react';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { Badge } from '@/shared/components/dls/Badge';
import { Modal } from '@/shared/components/dls/Modal';
import { Textarea } from '@/shared/components/dls/Textarea';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useClaimsList, useApproveClaim, useRejectClaim } from '../queries/useClaims';
import { formatDateTime } from '@/shared/utils/formatters';
import type { ClaimStatus } from '../types/claim';
import styles from './ClaimReviewPage.module.css';

const STATUS_BADGE_VARIANT: Record<ClaimStatus, 'warning' | 'success' | 'error'> = {
  CLAIM_PENDING: 'warning',
  CLAIMED: 'success',
  CLAIM_REJECTED: 'error',
};

const STATUS_LABELS: Record<ClaimStatus, string> = {
  CLAIM_PENDING: 'Pending',
  CLAIMED: 'Approved',
  CLAIM_REJECTED: 'Rejected',
};

function getDaysWaiting(updatedAt: string): number {
  const now = Date.now();
  const updated = new Date(updatedAt).getTime();
  return Math.max(0, Math.floor((now - updated) / (1000 * 60 * 60 * 24)));
}

function getDaysClass(days: number): string {
  if (days >= 7) return styles['daysWaiting--urgent'];
  if (days >= 3) return styles['daysWaiting--normal'];
  return styles['daysWaiting--recent'];
}

function maskPhone(phone: string | null): string {
  if (!phone) return '—';
  if (phone.length <= 4) return phone;
  return '*'.repeat(phone.length - 4) + phone.slice(-4);
}

export default function ClaimReviewPage() {
  const [statusFilter, setStatusFilter] = useState<string>('CLAIM_PENDING');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const filters = useMemo(() => ({
    status: statusFilter,
    search: searchTerm || undefined,
    page,
    page_size: 25,
  }), [statusFilter, searchTerm, page]);

  const { data, isLoading, error, refetch } = useClaimsList(filters);
  const approveMutation = useApproveClaim();
  const rejectMutation = useRejectClaim();

  const handleApprove = useCallback((vendorId: string) => {
    approveMutation.mutate(vendorId);
  }, [approveMutation]);

  const handleOpenReject = useCallback((vendorId: string) => {
    setRejectTarget(vendorId);
    setRejectReason('');
  }, []);

  const handleConfirmReject = useCallback(() => {
    if (!rejectTarget || !rejectReason.trim()) return;
    rejectMutation.mutate(
      { vendorId: rejectTarget, reason: rejectReason.trim() },
      { onSuccess: () => setRejectTarget(null) },
    );
  }, [rejectTarget, rejectReason, rejectMutation]);

  const handleCloseReject = useCallback(() => {
    setRejectTarget(null);
    setRejectReason('');
  }, []);

  const handleStatusChange = useCallback((value: string) => {
    setStatusFilter(value);
    setPage(1);
  }, []);

  const handleSearch = useCallback((value: string) => {
    setSearchTerm(value);
    setPage(1);
  }, []);

  const claims = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / 25);
  const isPending = statusFilter === 'CLAIM_PENDING';

  if (error) {
    return (
      <AdminLayout title="Claim review">
        <PageHeader heading="Claim review" subheading="Review vendor ownership claims" />
        <EmptyState
          illustration={<ClipboardCheck size={32} strokeWidth={1.5} />}
          heading="Failed to load claims"
          subheading="Something went wrong while fetching the claims queue."
          ctaLabel="Retry"
          onCta={() => refetch()}
        />
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Claim review">
      <PageHeader
        heading="Claim review"
        subheading={`${totalCount.toLocaleString()} claim${totalCount !== 1 ? 's' : ''} total`}
      />

      <div className={styles.filters}>
        <div className={styles.searchInput}>
          <Input
            id="claim-search"
            label="Search"
            placeholder="Search by business name..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>

        <div className={styles.statusFilter}>
          <Select
            id="claims-status-filter"
            label="Status"
            value={statusFilter}
            onChange={(e) => handleStatusChange(e.target.value)}
            options={[
              { value: 'CLAIM_PENDING', label: 'Pending' },
              { value: 'CLAIMED', label: 'Approved' },
              { value: 'CLAIM_REJECTED', label: 'Rejected' },
            ]}
          />
        </div>

        <span className={styles.resultCount}>
          Showing {claims.length} of {totalCount.toLocaleString()}
        </span>
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} columns={6} />
      ) : claims.length === 0 ? (
        <EmptyState
          illustration={<ClipboardCheck size={32} strokeWidth={1.5} />}
          heading={isPending ? 'No pending claims' : 'No claims found'}
          subheading={isPending ? 'All claim requests have been reviewed.' : 'No claims match your current filters.'}
        />
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table} aria-label="Claim review queue">
            <thead>
              <tr>
                <th scope="col">Business</th>
                <th scope="col">Claimer phone</th>
                <th scope="col">Status</th>
                <th scope="col">Days waiting</th>
                <th scope="col">Updated</th>
                {isPending && <th scope="col">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => {
                const days = getDaysWaiting(claim.updated_at);
                return (
                  <tr key={claim.id}>
                    <td>
                      <span className={styles.vendorName}>{claim.business_name}</span>
                      <br />
                      <span className={styles.areaText}>{claim.area_name}</span>
                    </td>
                    <td>
                      <span className={styles.maskedPhone}>{maskPhone(claim.owner_phone)}</span>
                    </td>
                    <td>
                      <Badge
                        variant={STATUS_BADGE_VARIANT[claim.claimed_status]}
                        label={STATUS_LABELS[claim.claimed_status]}
                      />
                    </td>
                    <td>
                      <span className={[styles.daysWaiting, getDaysClass(days)].join(' ')}>
                        {days === 0 ? 'Today' : `${days}d`}
                      </span>
                    </td>
                    <td>{formatDateTime(claim.updated_at)}</td>
                    {isPending && (
                      <td>
                        <div className={styles.actions}>
                          <Button
                            variant="ghost"
                            size="compact"
                            leftIcon={<CheckCircle size={16} strokeWidth={1.5} />}
                            onClick={() => handleApprove(claim.id)}
                            loading={approveMutation.isPending}
                            aria-label={`Approve claim for ${claim.business_name}`}
                          >
                            Approve
                          </Button>
                          <Button
                            variant="destructive"
                            size="compact"
                            leftIcon={<XCircle size={16} strokeWidth={1.5} />}
                            onClick={() => handleOpenReject(claim.id)}
                            aria-label={`Reject claim for ${claim.business_name}`}
                          >
                            Reject
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className={styles.pagination}>
              <span className={styles.paginationInfo}>
                Page {page} of {totalPages}
              </span>
              <div className={styles.paginationButtons}>
                <Button
                  variant="ghost"
                  size="compact"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="ghost"
                  size="compact"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {rejectTarget !== null && (
        <Modal
          title="Reject claim"
          isOpen={true}
          onClose={handleCloseReject}
        >
          <div className={styles.rejectModal}>
            <Textarea
              id="reject-reason"
              label="Rejection reason"
              placeholder="Explain why this claim is being rejected..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              required
              rows={4}
            />
            <div className={styles.rejectModalActions}>
              <Button variant="ghost" onClick={handleCloseReject}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmReject}
                disabled={!rejectReason.trim()}
                loading={rejectMutation.isPending}
              >
                Reject claim
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </AdminLayout>
  );
}
