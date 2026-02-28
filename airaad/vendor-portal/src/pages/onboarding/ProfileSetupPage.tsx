import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { updateVendorProfile, updateBusinessHours } from '@/api/vendor';
import { useAuthStore } from '@/store/authStore';
import styles from './ProfileSetupPage.module.css';

export default function ProfileSetupPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const vendorId = user?.vendor_id;

  const [phone, setPhone] = useState('');
  const [hours, setHours] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      if (!vendorId) throw new Error('No vendor ID');
      await updateVendorProfile(vendorId, {
        description: phone || undefined,
      });
      if (hours) {
        await updateBusinessHours({ hours_text: hours });
      }
    },
    onSuccess: () => {
      if (user) {
        setUser({ ...user, activation_stage: 'PROFILE_COMPLETE' });
      }
      navigate('/onboarding/welcome', { replace: true });
    },
    onError: () => {
      setError('Failed to update profile. Please try again.');
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      mutation.mutate();
    },
    [mutation],
  );

  const handleSkip = useCallback(() => {
    if (user) {
      setUser({ ...user, activation_stage: 'PROFILE_COMPLETE' });
    }
    navigate('/onboarding/welcome', { replace: true });
  }, [user, setUser, navigate]);

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <Link to="/" className="onboarding-logo">
          <img src="/airad_icon.png" alt="AirAd" className="onboarding-logo-icon" />
          <span className="onboarding-logo-text">AirAd</span>
        </Link>
        <h1 className={styles.heading}>Complete Your Profile</h1>
        <p className={styles.subtext}>
          Help customers find you — add your business hours and contact details.
          You can always update these later.
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="phone" className={styles.label}>Business phone number</label>
            <input
              id="phone"
              type="tel"
              className={styles.input}
              placeholder="+92 3XX XXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
            />
            <span className={styles.hint}>Displayed on your public listing</span>
          </div>

          <div className={styles.field}>
            <label htmlFor="hours" className={styles.label}>Business hours</label>
            <textarea
              id="hours"
              className={styles.textarea}
              placeholder={"Mon–Sat: 9:00 AM – 10:00 PM\nSun: 12:00 PM – 8:00 PM"}
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              rows={4}
            />
            <span className={styles.hint}>Free-text format — enter your operating hours</span>
          </div>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.skipBtn}
              onClick={handleSkip}
            >
              Skip for now
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Saving...' : 'Save & continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
