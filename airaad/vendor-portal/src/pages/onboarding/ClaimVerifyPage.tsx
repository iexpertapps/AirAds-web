import { useCallback } from 'react';
import { useNavigate, useParams, useLocation, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle } from 'lucide-react';
import { submitClaim } from '@/api/vendor';
import { useAuthStore } from '@/store/authStore';
import type { NearbyVendor } from '@/api/vendor';
import styles from './ClaimVerifyPage.module.css';

export default function ClaimVerifyPage() {
  const navigate = useNavigate();
  const { vendorId } = useParams<{ vendorId: string }>();
  const location = useLocation();
  const vendor = (location.state as { vendor?: NearbyVendor })?.vendor;
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);

  const claimMutation = useMutation({
    mutationFn: () => submitClaim(vendorId!),
    onSuccess: () => {
      if (user) {
        setUser({ ...user, vendor_id: vendorId!, activation_stage: 'CLAIM_PENDING' });
      }
      navigate('/onboarding/setup', { replace: true });
    },
  });

  const handleConfirm = useCallback(() => {
    if (vendorId) claimMutation.mutate();
  }, [vendorId, claimMutation]);

  if (!vendorId) {
    return (
      <div className={styles.page}>
        <div className={styles.inner}>
          <p className={styles.error}>Invalid vendor. Please go back and search again.</p>
          <Link to="/onboarding/search" className={styles.backLink}>
            <ArrowLeft size={14} strokeWidth={1.5} /> Back to search
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <Link to="/" className="onboarding-logo">
          <img src="/airad_icon.png" alt="AirAd" className="onboarding-logo-icon" />
          <span className="onboarding-logo-text">AirAd</span>
        </Link>

        <Link to="/onboarding/search" className={styles.backLink}>
          <ArrowLeft size={14} strokeWidth={1.5} /> Back to search
        </Link>

        <h1 className={styles.heading}>Claim This Business</h1>
        <p className={styles.subtext}>
          Confirm that you are the owner or authorized representative of this business.
        </p>

        {vendor && (
          <div className={styles.vendorCard}>
            <span className={styles.vendorName}>{vendor.business_name}</span>
            <span className={styles.vendorAddress}>
              {vendor.address_text}{vendor.area_name ? `, ${vendor.area_name}` : ''}
            </span>
          </div>
        )}

        <div className={styles.confirmSection}>
          <p className={styles.confirmText}>
            By clicking below, you confirm that you are the authorized owner or manager
            of this business and agree to AirAd&apos;s Terms of Service.
          </p>

          {claimMutation.isError && (
            <p className={styles.error} role="alert">
              Failed to submit claim. Please try again.
            </p>
          )}

          {claimMutation.isSuccess ? (
            <div className={styles.successMsg}>
              <CheckCircle size={48} strokeWidth={1.5} className={styles.successIcon} />
              <h2 className={styles.successHeading}>Claim submitted!</h2>
              <p className={styles.successText}>
                Your claim is being reviewed. Let&apos;s set up your profile while you wait.
              </p>
            </div>
          ) : (
            <button
              className={styles.submitBtn}
              onClick={handleConfirm}
              disabled={claimMutation.isPending}
              type="button"
            >
              {claimMutation.isPending ? 'Submitting...' : 'Confirm & Claim Business'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
