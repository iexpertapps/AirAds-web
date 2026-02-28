import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Film, Eye } from 'lucide-react';
import { getReels, createReel, deleteReel } from '@/api/reels';
import type { CreateReelPayload, Reel } from '@/api/reels';
import { useAuthStore } from '@/store/authStore';
import { queryKeys } from '@/queryKeys';
import { formatDateTime } from '@/utils/formatters';
import styles from './ReelsPage.module.css';

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function ReelsPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const vendorId = user?.vendor_id ?? '';
  const [showCreate, setShowCreate] = useState(false);

  const { data: reels, isLoading } = useQuery({
    queryKey: queryKeys.reels.list(vendorId),
    queryFn: () => getReels(vendorId),
    enabled: !!vendorId,
    staleTime: 30_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (reelId: string) => deleteReel(vendorId, reelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reels.list(vendorId) });
    },
  });

  if (isLoading) {
    return <div className={styles.loading}>Loading reels…</div>;
  }

  return (
    <>
      <div className={styles.header}>
        <h1 className={styles.heading}>Reels</h1>
        <button className={styles.createBtn} onClick={() => setShowCreate(true)} type="button">
          <Plus size={16} strokeWidth={1.5} /> Upload reel
        </button>
      </div>

      {(!reels || reels.length === 0) ? (
        <div className={styles.empty}>
          <Film size={32} strokeWidth={1.5} className="empty-icon" />
          No reels yet. Upload a short video to showcase your business.
        </div>
      ) : (
        <div className={styles.grid}>
          {reels.map((r) => (
            <ReelCard
              key={r.id}
              reel={r}
              onDelete={() => deleteMutation.mutate(r.id)}
              deleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateReelModal vendorId={vendorId} onClose={() => setShowCreate(false)} />
      )}
    </>
  );
}

function ReelCard({ reel, onDelete, deleting }: { reel: Reel; onDelete: () => void; deleting: boolean }) {
  return (
    <div className={styles.card}>
      <div className={styles.thumbnail}>
        {reel.thumbnail_url ? (
          <img src={reel.thumbnail_url} alt={reel.title} loading="lazy" />
        ) : (
          <Film size={40} strokeWidth={1} className={styles.thumbnailPlaceholder} />
        )}
        {reel.duration_seconds > 0 && (
          <span className={styles.durationBadge}>{formatDuration(reel.duration_seconds)}</span>
        )}
      </div>

      <div className={styles.cardBody}>
        <span className={styles.cardTitle}>{reel.title}</span>
        <div className={styles.cardMeta}>
          <span className={[styles.statusBadge, styles[`statusBadge--${reel.moderation_status}`]].join(' ')}>
            {reel.moderation_status}
          </span>
          <span><Eye size={12} strokeWidth={1.5} className="inline-icon" />{reel.view_count.toLocaleString()} views</span>
          <span>{formatDateTime(reel.created_at)}</span>
        </div>
        {reel.moderation_status === 'REJECTED' && (
          <p className={styles.rejectionReason}>This reel was rejected by moderation.</p>
        )}
      </div>

      <div className={styles.cardActions}>
        <button className={styles.deleteBtn} onClick={onDelete} disabled={deleting} type="button">
          <Trash2 size={12} strokeWidth={1.5} /> Remove
        </button>
      </div>
    </div>
  );
}

function CreateReelModal({ vendorId, onClose }: { vendorId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [thumbnailUrl, setThumbnailUrl] = useState('');
  const [duration, setDuration] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (payload: CreateReelPayload) => createReel(vendorId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reels.list(vendorId) });
      onClose();
    },
    onError: () => {
      setError('Failed to upload reel. Please try again.');
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      if (!title.trim()) { setError('Title is required'); return; }
      if (!videoUrl.trim()) { setError('Video URL / S3 key is required'); return; }
      if (!duration || Number(duration) < 1) { setError('Duration is required'); return; }
      mutation.mutate({
        title: title.trim(),
        s3_key: videoUrl.trim(),
        duration_seconds: Number(duration),
        thumbnail_s3_key: thumbnailUrl.trim() || undefined,
      });
    },
    [title, videoUrl, thumbnailUrl, duration, mutation],
  );

  return (
    <div className={styles.modalOverlay} onClick={onClose} role="dialog" aria-modal="true" aria-label="Upload reel">
      <form className={styles.modalCard} onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 className={styles.modalHeading}>Upload Reel</h2>

        <div className={styles.field}>
          <label htmlFor="r-title" className={styles.label}>Title</label>
          <input id="r-title" className={styles.input} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Our signature pizza" required />
        </div>

        <div className={styles.field}>
          <label htmlFor="r-video" className={styles.label}>Video S3 Key / URL</label>
          <input id="r-video" className={styles.input} value={videoUrl} onChange={(e) => setVideoUrl(e.target.value)} placeholder="videos/my-reel.mp4" required />
          <span className={styles.hint}>Upload your video and paste the S3 key or URL here</span>
        </div>

        <div className={styles.field}>
          <label htmlFor="r-duration" className={styles.label}>Duration (seconds)</label>
          <input id="r-duration" type="number" className={styles.input} value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="30" min="1" required />
        </div>

        <div className={styles.field}>
          <label htmlFor="r-thumb" className={styles.label}>Thumbnail S3 Key (optional)</label>
          <input id="r-thumb" className={styles.input} value={thumbnailUrl} onChange={(e) => setThumbnailUrl(e.target.value)} placeholder="thumbnails/my-reel.jpg" />
        </div>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <div className={styles.modalActions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn} disabled={mutation.isPending}>
            {mutation.isPending ? 'Uploading...' : 'Upload reel'}
          </button>
        </div>
      </form>
    </div>
  );
}
