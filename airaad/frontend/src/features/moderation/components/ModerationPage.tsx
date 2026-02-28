import { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Film, CheckCircle, XCircle, ShieldAlert, ClipboardCheck, Eye, Play, MapPin, Clock, TrendingUp } from 'lucide-react';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Button } from '@/shared/components/dls/Button';
import { Badge } from '@/shared/components/dls/Badge';
import { Modal } from '@/shared/components/dls/Modal';
import { Textarea } from '@/shared/components/dls/Textarea';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useModerationQueue, useApproveReel, useRejectReel } from '../queries/useModeration';
import { formatDateTime } from '@/shared/utils/formatters';
import type { PendingReel } from '../types/moderation';
import styles from './ModerationPage.module.css';

type TabId = 'reels' | 'claims';
type ModalMode = 'preview' | 'reject';

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function ModerationPage() {
  const [activeTab, setActiveTab] = useState<TabId>('reels');
  const [previewReel, setPreviewReel] = useState<PendingReel | null>(null);
  const [modalMode, setModalMode] = useState<ModalMode>('preview');
  const [rejectReason, setRejectReason] = useState('');
  const [moderatorNotes, setModeratorNotes] = useState('');

  const { data, isLoading, error, refetch } = useModerationQueue();
  const approveReelMutation = useApproveReel();
  const rejectReelMutation = useRejectReel();

  const handleApproveReel = useCallback((reelId: string, notes?: string) => {
    const payload: { reelId: string; notes?: string } = { reelId };
    if (notes) payload.notes = notes;
    approveReelMutation.mutate(payload, {
      onSuccess: () => { setPreviewReel(null); },
    });
  }, [approveReelMutation]);

  const handleOpenPreview = useCallback((reel: PendingReel) => {
    setPreviewReel(reel);
    setModalMode('preview');
    setRejectReason('');
    setModeratorNotes(reel.moderation_notes ?? '');
  }, []);

  const handleOpenRejectFromPreview = useCallback(() => {
    setModalMode('reject');
  }, []);

  const handleConfirmReject = useCallback(() => {
    if (!previewReel || !rejectReason.trim()) return;
    rejectReelMutation.mutate(
      { reelId: previewReel.id, reason: rejectReason.trim() },
      { onSuccess: () => { setPreviewReel(null); setRejectReason(''); } },
    );
  }, [previewReel, rejectReason, rejectReelMutation]);

  const handleCloseModal = useCallback(() => {
    setPreviewReel(null);
    setRejectReason('');
    setModeratorNotes('');
  }, []);

  const reelsCount = data?.pending_reels_count ?? 0;
  const claimsCount = data?.pending_claims_count ?? 0;

  if (error) {
    return (
      <AdminLayout title="Content moderation">
        <PageHeader heading="Content moderation" subheading="Review flagged content" />
        <EmptyState
          illustration={<ShieldAlert size={32} strokeWidth={1.5} />}
          heading="Failed to load moderation queue"
          subheading="Something went wrong while fetching the moderation queue."
          ctaLabel="Retry"
          onCta={() => refetch()}
        />
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title="Content moderation">
      <PageHeader
        heading="Content moderation"
        subheading={`${data?.total_pending ?? 0} items pending review`}
      />

      <div className={styles.summaryCards}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryValue}>{reelsCount}</span>
          <span className={styles.summaryLabel}>Pending reels</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryValue}>{claimsCount}</span>
          <span className={styles.summaryLabel}>Pending claims</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={styles.summaryValue}>{data?.total_pending ?? 0}</span>
          <span className={styles.summaryLabel}>Total pending</span>
        </div>
      </div>

      <div className={styles.tabs} role="tablist" aria-label="Moderation categories">
        <button
          className={[styles.tab, activeTab === 'reels' ? styles['tab--active'] : ''].join(' ')}
          role="tab"
          aria-selected={activeTab === 'reels'}
          aria-controls="panel-reels"
          onClick={() => setActiveTab('reels')}
        >
          <Film size={16} strokeWidth={1.5} aria-hidden="true" />
          Reels
          <span className={styles.tabCount}>{reelsCount}</span>
        </button>
        <button
          className={[styles.tab, activeTab === 'claims' ? styles['tab--active'] : ''].join(' ')}
          role="tab"
          aria-selected={activeTab === 'claims'}
          aria-controls="panel-claims"
          onClick={() => setActiveTab('claims')}
        >
          <ClipboardCheck size={16} strokeWidth={1.5} aria-hidden="true" />
          Claims
          <span className={styles.tabCount}>{claimsCount}</span>
        </button>
      </div>

      {isLoading ? (
        <SkeletonTable rows={6} columns={5} />
      ) : activeTab === 'reels' ? (
        <ReelsPanel
          reels={data?.pending_reels ?? []}
          onPreview={handleOpenPreview}
        />
      ) : (
        <ClaimsPanel claims={data?.pending_claims ?? []} />
      )}

      {previewReel !== null && modalMode === 'preview' && (
        <Modal
          title={`Review: ${previewReel.title}`}
          isOpen={true}
          onClose={handleCloseModal}
        >
          <div className={styles.previewModal}>
            <div className={styles.thumbnailWrap}>
              {previewReel.thumbnail_url ? (
                <img
                  src={previewReel.thumbnail_url}
                  alt={`Thumbnail for ${previewReel.title}`}
                  className={styles.thumbnail}
                />
              ) : (
                <div className={styles.thumbnailPlaceholder} aria-label="No thumbnail available">
                  <Play size={32} strokeWidth={1.5} aria-hidden="true" />
                  <span>No thumbnail</span>
                </div>
              )}
              <div className={styles.thumbnailOverlay}>
                <Badge variant="neutral" label={formatDuration(previewReel.duration_seconds)} />
              </div>
            </div>

            <div className={styles.reelMeta}>
              <div className={styles.reelMetaRow}>
                <MapPin size={14} strokeWidth={1.5} aria-hidden="true" />
                <span>{previewReel.vendor_name}{previewReel.vendor_area ? ` — ${previewReel.vendor_area}` : ''}</span>
              </div>
              <div className={styles.reelMetaRow}>
                <Clock size={14} strokeWidth={1.5} aria-hidden="true" />
                <span>Submitted {formatDateTime(previewReel.created_at)}</span>
              </div>
              <div className={styles.reelMetaRow}>
                <TrendingUp size={14} strokeWidth={1.5} aria-hidden="true" />
                <span>{previewReel.view_count.toLocaleString()} views</span>
              </div>
            </div>

            <Textarea
              id="moderator-notes"
              label="Moderator notes (optional)"
              placeholder="Add internal notes about this content..."
              value={moderatorNotes}
              onChange={(e) => setModeratorNotes(e.target.value)}
              rows={3}
            />

            <div className={styles.previewModalActions}>
              <Button variant="ghost" onClick={handleCloseModal}>
                Close
              </Button>
              <Button
                variant="destructive"
                leftIcon={<XCircle size={16} strokeWidth={1.5} />}
                onClick={handleOpenRejectFromPreview}
              >
                Reject
              </Button>
              <Button
                variant="primary"
                leftIcon={<CheckCircle size={16} strokeWidth={1.5} />}
                onClick={() => handleApproveReel(previewReel.id, moderatorNotes || undefined) }
                loading={approveReelMutation.isPending}
              >
                Approve
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {previewReel !== null && modalMode === 'reject' && (
        <Modal title="Reject reel" isOpen={true} onClose={() => setModalMode('preview')}>
          <div className={styles.rejectModal}>
            <p>
              Rejecting <strong>{previewReel.title}</strong> by {previewReel.vendor_name}
            </p>
            <Textarea
              id="reject-reason"
              label="Rejection reason (shown to vendor)"
              placeholder="Explain why this reel is being rejected..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              required
              rows={4}
            />
            <div className={styles.rejectModalActions}>
              <Button variant="ghost" onClick={() => setModalMode('preview')}>
                Back
              </Button>
              <Button
                variant="destructive"
                onClick={handleConfirmReject}
                disabled={!rejectReason.trim()}
                loading={rejectReelMutation.isPending}
              >
                Confirm rejection
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </AdminLayout>
  );
}

interface ReelsPanelProps {
  reels: PendingReel[];
  onPreview: (reel: PendingReel) => void;
}

function ReelsPanel({ reels, onPreview }: ReelsPanelProps) {
  if (reels.length === 0) {
    return (
      <EmptyState
        illustration={<Film size={32} strokeWidth={1.5} />}
        heading="No reels pending review"
        subheading="All submitted reels have been moderated."
      />
    );
  }

  return (
    <div id="panel-reels" role="tabpanel" className={styles.tableWrap}>
      <table className={styles.table} aria-label="Pending reels">
        <thead>
          <tr>
            <th scope="col">Preview</th>
            <th scope="col">Title</th>
            <th scope="col">Vendor</th>
            <th scope="col">Duration</th>
            <th scope="col">Submitted</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {reels.map((reel) => (
            <tr key={reel.id}>
              <td>
                <button
                  className={styles.thumbBtn}
                  onClick={() => onPreview(reel)}
                  aria-label={`Preview reel ${reel.title}`}
                >
                  {reel.thumbnail_url ? (
                    <img
                      src={reel.thumbnail_url}
                      alt={reel.title}
                      className={styles.thumbImg}
                    />
                  ) : (
                    <div className={styles.thumbPlaceholder}>
                      <Play size={16} strokeWidth={1.5} aria-hidden="true" />
                    </div>
                  )}
                </button>
              </td>
              <td>
                <span className={styles.reelTitle}>{reel.title}</span>
              </td>
              <td>
                <Link to={`/vendors/${reel.vendor_id}`} className={styles.vendorLink}>
                  {reel.vendor_name}
                </Link>
                {reel.vendor_area ? (
                  <span className={styles.reelMeta}>{reel.vendor_area}</span>
                ) : null}
              </td>
              <td>
                <span className={styles.duration}>{formatDuration(reel.duration_seconds)}</span>
              </td>
              <td>{formatDateTime(reel.created_at)}</td>
              <td>
                <div className={styles.actions}>
                  <Button
                    variant="ghost"
                    size="compact"
                    leftIcon={<Eye size={16} strokeWidth={1.5} />}
                    onClick={() => onPreview(reel)}
                    aria-label={`Review reel ${reel.title}`}
                  >
                    Review
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ClaimsPanelProps {
  claims: Array<{
    vendor_id: string;
    business_name: string;
    area_name: string;
    claimed_by: string | null;
    updated_at: string;
    created_at: string;
  }>;
}

function ClaimsPanel({ claims }: ClaimsPanelProps) {
  if (claims.length === 0) {
    return (
      <EmptyState
        illustration={<ClipboardCheck size={32} strokeWidth={1.5} />}
        heading="No claims pending review"
        subheading="All claim requests have been reviewed."
      />
    );
  }

  return (
    <div id="panel-claims" role="tabpanel" className={styles.tableWrap}>
      <table className={styles.table} aria-label="Pending claims">
        <thead>
          <tr>
            <th scope="col">Business</th>
            <th scope="col">Claimed by</th>
            <th scope="col">Submitted</th>
            <th scope="col">Updated</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => (
            <tr key={claim.vendor_id}>
              <td>
                <Link to={`/vendors/${claim.vendor_id}`} className={styles.claimName}>
                  {claim.business_name}
                </Link>
                {claim.area_name ? (
                  <span className={styles.claimMeta}>{claim.area_name}</span>
                ) : null}
              </td>
              <td>
                <span className={styles.claimMeta}>{claim.claimed_by ?? '—'}</span>
              </td>
              <td>{formatDateTime(claim.created_at)}</td>
              <td>{formatDateTime(claim.updated_at)}</td>
              <td>
                <Link to="/admin/claims">
                  <Button variant="ghost" size="compact"
                    leftIcon={<ClipboardCheck size={16} strokeWidth={1.5} />}>
                    Review
                  </Button>
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
