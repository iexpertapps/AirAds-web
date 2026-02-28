import { useState, useCallback, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, ExternalLink, PartyPopper } from 'lucide-react';
import {
  getSubscriptionStatus,
  getInvoices,
  createCheckoutSession,
  cancelSubscription,
  resumeSubscription,
  createPortalSession,
} from '@/api/subscription';
import { useAuthStore } from '@/store/authStore';
import { queryKeys } from '@/queryKeys';
import { formatDateTime, formatCurrency } from '@/utils/formatters';
import styles from './SubscriptionPage.module.css';

interface TierDef {
  key: string;
  label: string;
  price: number;
  unit: string;
  features: string[];
}

const TIERS: TierDef[] = [
  {
    key: 'SILVER',
    label: 'Silver',
    price: 0,
    unit: 'Free forever',
    features: ['1 reel upload', 'Basic AR visibility', 'Basic metrics'],
  },
  {
    key: 'GOLD',
    label: 'Gold',
    price: 3000,
    unit: '/month',
    features: ['3 reel uploads', 'Boosted AR', 'Voice introduction', 'Verified badge', '1 happy hour/day'],
  },
  {
    key: 'DIAMOND',
    label: 'Diamond',
    price: 7000,
    unit: '/month',
    features: ['6 reel uploads', 'High priority AR', 'Dynamic voice bot', 'Premium badge', '3 happy hours/day', 'Advanced analytics'],
  },
  {
    key: 'PLATINUM',
    label: 'Platinum',
    price: 15000,
    unit: '/month',
    features: ['Unlimited reels', 'Dominant zone AR', 'Advanced voice bot', 'Elite crown', 'Smart automation', 'Competitor insights'],
  },
];

const TIER_RANK: Record<string, number> = { SILVER: 0, GOLD: 1, DIAMOND: 2, PLATINUM: 3 };

export default function SubscriptionPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const currentTier = user?.subscription_level ?? 'SILVER';
  const [searchParams, setSearchParams] = useSearchParams();
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (searchParams.get('success') === 'true') {
      setShowSuccess(true);
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription.status() });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, queryClient]);

  const { data: subStatus, isLoading: subLoading } = useQuery({
    queryKey: queryKeys.subscription.status(),
    queryFn: getSubscriptionStatus,
    staleTime: 30_000,
  });

  const { data: invoices, isLoading: invLoading } = useQuery({
    queryKey: queryKeys.subscription.invoices(),
    queryFn: getInvoices,
    staleTime: 60_000,
  });

  const checkoutMutation = useMutation({
    mutationFn: (packageLevel: string) => createCheckoutSession(packageLevel),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription.status() });
    },
  });

  const resumeMutation = useMutation({
    mutationFn: resumeSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription.status() });
    },
  });

  const portalMutation = useMutation({
    mutationFn: createPortalSession,
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });

  const handleUpgrade = useCallback(
    (tierKey: string) => {
      checkoutMutation.mutate(tierKey);
    },
    [checkoutMutation],
  );

  if (subLoading) {
    return <div className={styles.loading}>Loading subscription…</div>;
  }

  const status = subStatus?.status ?? 'NONE';
  const cancelAtEnd = subStatus?.cancel_at_period_end ?? false;

  return (
    <>
      <h1 className={styles.heading}>Subscription</h1>
      <p className={styles.subtext}>Manage your plan and billing</p>

      {showSuccess && (
        <div className={styles.successBanner} role="status">
          <PartyPopper size={20} strokeWidth={1.5} />
          <div>
            <strong>Subscription upgraded successfully!</strong>
            <p>Your new plan features are now active.</p>
          </div>
          <button className={styles.dismissBtn} onClick={() => setShowSuccess(false)} type="button" aria-label="Dismiss">&times;</button>
        </div>
      )}

      {/* Current Plan Card */}
      <div className={styles.currentPlan}>
        <div className={styles.planHeader}>
          <span className={styles.planName}>{currentTier} Plan</span>
          <span className={[styles.planStatusBadge, styles[`planStatusBadge--${status}`]].join(' ')}>
            {status === 'NONE' ? 'Free' : status.replace('_', ' ')}
          </span>
        </div>

        {subStatus?.current_period_end && (
          <p className={styles.planMeta}>
            {cancelAtEnd
              ? `Cancels at end of period: ${formatDateTime(subStatus.current_period_end)}`
              : `Renews on ${formatDateTime(subStatus.current_period_end)}`}
          </p>
        )}

        <div className={styles.planActions}>
          {status !== 'NONE' && (
            <button
              className={styles.manageBtn}
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              type="button"
            >
              <ExternalLink size={14} strokeWidth={1.5} />
              {portalMutation.isPending ? 'Opening...' : 'Manage billing'}
            </button>
          )}

          {status === 'ACTIVE' && !cancelAtEnd && currentTier !== 'SILVER' && (
            <button
              className={styles.cancelBtn}
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              type="button"
            >
              {cancelMutation.isPending ? 'Cancelling...' : 'Cancel subscription'}
            </button>
          )}

          {cancelAtEnd && (
            <button
              className={styles.resumeBtn}
              onClick={() => resumeMutation.mutate()}
              disabled={resumeMutation.isPending}
              type="button"
            >
              {resumeMutation.isPending ? 'Resuming...' : 'Resume subscription'}
            </button>
          )}
        </div>

        {cancelAtEnd && (
          <p className={styles.cancelWarning}>
            Your subscription will be cancelled at the end of the current billing period.
            You can resume anytime before then.
          </p>
        )}

        {status === 'PAST_DUE' && (
          <p className={styles.cancelWarning}>
            Your payment is past due. Please update your payment method to avoid service interruption.
          </p>
        )}

        {checkoutMutation.isError && (
          <p className={styles.error}>Failed to start checkout. Please try again.</p>
        )}
        {cancelMutation.isError && (
          <p className={styles.error}>Failed to cancel. Please try again.</p>
        )}
      </div>

      {/* Plan Comparison */}
      <h2 className={styles.comparisonHeading}>Compare Plans</h2>
      <div className={styles.tiersGrid}>
        {TIERS.map((tier) => {
          const isCurrent = tier.key === currentTier;
          const rank = TIER_RANK[tier.key] ?? 0;
          const currentRank = TIER_RANK[currentTier] ?? 0;
          const isUpgrade = rank > currentRank;
          const isDowngrade = rank < currentRank;

          return (
            <div
              key={tier.key}
              className={[styles.tierCard, isCurrent ? styles['tierCard--current'] : ''].join(' ')}
            >
              {tier.key === 'DIAMOND' && !isCurrent && <span className={styles.popularLabel}>Most Popular</span>}
              {isCurrent && <span className={styles.currentLabel}>Current plan</span>}
              <span className={styles.tierName}>{tier.label}</span>
              <span className={styles.tierPrice}>
                {tier.price === 0 ? 'Free' : formatCurrency(tier.price)}
              </span>
              <span className={styles.tierUnit}>{tier.unit}</span>

              <ul className={styles.tierFeatures}>
                {tier.features.map((f) => (
                  <li key={f} className={styles.tierFeature}>
                    <Check size={14} strokeWidth={2} className={styles.featureCheck} />
                    {f}
                  </li>
                ))}
              </ul>

              {isUpgrade && (
                <button
                  className={styles.upgradeBtn}
                  onClick={() => handleUpgrade(tier.key)}
                  disabled={checkoutMutation.isPending}
                  type="button"
                >
                  {checkoutMutation.isPending ? 'Redirecting...' : `Upgrade to ${tier.label}`}
                </button>
              )}

              {isDowngrade && tier.key !== 'SILVER' && (
                <button
                  className={styles.downgradeBtn}
                  onClick={() => handleUpgrade(tier.key)}
                  disabled={checkoutMutation.isPending}
                  type="button"
                >
                  Downgrade
                </button>
              )}

              {isCurrent && (
                <button className={styles.upgradeBtn} disabled type="button">
                  Current plan
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Billing History */}
      <h2 className={styles.invoiceHeading}>Billing History</h2>
      {invLoading ? (
        <p className="loading-invoices">Loading invoices…</p>
      ) : !invoices || invoices.length === 0 ? (
        <p className={styles.emptyInvoices}>No invoices yet.</p>
      ) : (
        <table className={styles.invoiceTable}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Plan</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Invoice</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>{formatDateTime(inv.created_at)}</td>
                <td>{inv.plan}</td>
                <td>{formatCurrency(inv.amount)}</td>
                <td>{inv.status}</td>
                <td>
                  {inv.invoice_pdf_url ? (
                    <a
                      href={inv.invoice_pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.downloadLink}
                    >
                      Download
                    </a>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
