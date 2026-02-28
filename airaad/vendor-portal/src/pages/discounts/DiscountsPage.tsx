import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Tag, Clock } from 'lucide-react';
import { getDiscounts, createDiscount, deleteDiscount } from '@/api/discounts';
import type { CreateDiscountPayload, Discount } from '@/api/discounts';
import { useAuthStore } from '@/store/authStore';
import { queryKeys } from '@/queryKeys';
import { formatDateTime } from '@/utils/formatters';
import styles from './DiscountsPage.module.css';

export default function DiscountsPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const vendorId = user?.vendor_id ?? '';
  const [showCreate, setShowCreate] = useState(false);

  const { data: discounts, isLoading } = useQuery({
    queryKey: queryKeys.discounts.list(vendorId),
    queryFn: () => getDiscounts(vendorId),
    enabled: !!vendorId,
    staleTime: 30_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (discountId: string) => deleteDiscount(vendorId, discountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.discounts.list(vendorId) });
    },
  });

  if (isLoading) {
    return <div className={styles.loading}>Loading discounts…</div>;
  }

  return (
    <>
      <div className={styles.header}>
        <h1 className={styles.heading}>Discounts</h1>
        <button className={styles.createBtn} onClick={() => setShowCreate(true)} type="button">
          <Plus size={16} strokeWidth={1.5} /> Create discount
        </button>
      </div>

      {(!discounts || discounts.length === 0) ? (
        <div className={styles.empty}>
          <Tag size={32} strokeWidth={1.5} className="empty-icon" />
          No discounts yet. Create your first discount to attract nearby customers.
        </div>
      ) : (
        <div className={styles.grid}>
          {discounts.map((d) => (
            <DiscountCard
              key={d.id}
              discount={d}
              onDelete={() => deleteMutation.mutate(d.id)}
              deleting={deleteMutation.isPending}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateDiscountModal
          vendorId={vendorId}
          onClose={() => setShowCreate(false)}
        />
      )}
    </>
  );
}

function DiscountCard({ discount, onDelete, deleting }: { discount: Discount; onDelete: () => void; deleting: boolean }) {
  const now = new Date();
  const end = new Date(discount.end_time);
  const isExpired = end < now;

  const numValue = parseFloat(discount.value) || 0;
  const isHappyHour = discount.discount_type === 'HAPPY_HOUR';
  const valueLabel = discount.discount_type === 'PERCENTAGE'
    ? `${numValue}% off`
    : discount.discount_type === 'BUY_ONE_GET_ONE'
      ? 'Buy One Get One'
      : `PKR ${numValue} off`;

  return (
    <div className={[styles.card, !discount.is_active || isExpired ? styles['card--inactive'] : ''].join(' ')}>
      <div className={styles.cardHeader}>
        <span className={styles.cardTitle}>{discount.title}</span>
        {isHappyHour && (
          <span className={[styles.cardBadge, styles['cardBadge--happyHour']].join(' ')}>
            <Clock size={10} strokeWidth={2} /> Happy Hour
          </span>
        )}
        {!isHappyHour && discount.is_active && !isExpired && (
          <span className={[styles.cardBadge, styles['cardBadge--active']].join(' ')}>Active</span>
        )}
        {isExpired && (
          <span className={[styles.cardBadge, styles['cardBadge--expired']].join(' ')}>Expired</span>
        )}
      </div>
      {discount.item_description && <p className={styles.cardDesc}>{discount.item_description}</p>}
      <span className={styles.cardValue}>{valueLabel}</span>
      <span className={styles.cardMeta}>
        {formatDateTime(discount.start_time)} — {formatDateTime(discount.end_time)}
      </span>
      <div className={styles.cardActions}>
        <button
          className={styles.deleteBtn}
          onClick={onDelete}
          disabled={deleting}
          type="button"
        >
          <Trash2 size={12} strokeWidth={1.5} /> Remove
        </button>
      </div>
    </div>
  );
}

function CreateDiscountModal({ vendorId, onClose }: { vendorId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [discountType, setDiscountType] = useState<'PERCENTAGE' | 'FIXED_AMOUNT' | 'BUY_ONE_GET_ONE'>('PERCENTAGE');
  const [discountValue, setDiscountValue] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [isHappyHour, setIsHappyHour] = useState(false);
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (payload: CreateDiscountPayload) => createDiscount(vendorId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.discounts.list(vendorId) });
      onClose();
    },
    onError: () => {
      setError('Failed to create discount. Please try again.');
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      if (!title.trim()) { setError('Title is required'); return; }
      if (!startTime || !endTime) { setError('Start and end times are required'); return; }
      mutation.mutate({
        title: title.trim(),
        item_description: description.trim() || undefined,
        discount_type: isHappyHour ? 'HAPPY_HOUR' : discountType,
        value: discountType === 'BUY_ONE_GET_ONE' ? 0 : Number(discountValue),
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
      });
    },
    [title, description, discountType, discountValue, startTime, endTime, isHappyHour, mutation],
  );

  return (
    <div className={styles.modalOverlay} onClick={onClose} role="dialog" aria-modal="true" aria-label="Create discount">
      <form className={styles.modalCard} onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 className={styles.modalHeading}>New Discount</h2>

        <div className={styles.field}>
          <label htmlFor="d-title" className={styles.label}>Title</label>
          <input id="d-title" className={styles.input} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Weekend Special" required />
        </div>

        <div className={styles.field}>
          <label htmlFor="d-desc" className={styles.label}>Description (optional)</label>
          <input id="d-desc" className={styles.input} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description" />
        </div>

        <div className={styles.field}>
          <label htmlFor="d-type" className={styles.label}>Type</label>
          <select id="d-type" className={styles.select} value={discountType} onChange={(e) => setDiscountType(e.target.value as typeof discountType)}>
            <option value="PERCENTAGE">Percentage</option>
            <option value="FIXED_AMOUNT">Fixed amount (PKR)</option>
            <option value="BUY_ONE_GET_ONE">Buy One Get One</option>
          </select>
        </div>

        {discountType !== 'BUY_ONE_GET_ONE' && (
          <div className={styles.field}>
            <label htmlFor="d-value" className={styles.label}>
              {discountType === 'PERCENTAGE' ? 'Percentage (%)' : 'Amount (PKR)'}
            </label>
            <input id="d-value" type="number" className={styles.input} value={discountValue} onChange={(e) => setDiscountValue(e.target.value)} min="1" max={discountType === 'PERCENTAGE' ? '100' : undefined} required />
          </div>
        )}

        <div className={styles.field}>
          <label htmlFor="d-start" className={styles.label}>Start time</label>
          <input id="d-start" type="datetime-local" className={styles.input} value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
        </div>

        <div className={styles.field}>
          <label htmlFor="d-end" className={styles.label}>End time</label>
          <input id="d-end" type="datetime-local" className={styles.input} value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
        </div>

        <div className={styles.field}>
          <label className="checkbox-label">
            <input type="checkbox" checked={isHappyHour} onChange={(e) => setIsHappyHour(e.target.checked)} />
            <span className={styles.label}>Happy Hour discount</span>
          </label>
        </div>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <div className={styles.modalActions}>
          <button type="button" className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn} disabled={mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Create discount'}
          </button>
        </div>
      </form>
    </div>
  );
}
