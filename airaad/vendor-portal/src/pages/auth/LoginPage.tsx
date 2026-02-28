import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { sendOTP } from '@/api/auth';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: (phoneNumber: string) => sendOTP(phoneNumber),
    onSuccess: (_data, phoneNumber) => {
      navigate('/verify', { state: { phone: phoneNumber } });
    },
    onError: (err: unknown) => {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to send OTP. Please try again.');
      }
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      const cleaned = phone.replace(/\D/g, '');
      if (cleaned.length < 10 || cleaned.length > 11) {
        setError('Enter a valid Pakistani phone number');
        return;
      }
      mutation.mutate(`+92${cleaned}`);
    },
    [phone, mutation],
  );

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.logo}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />
          <span className={styles.logoText}>AirAd</span>
        </Link>
        <h1 className={styles.heading}>Welcome back</h1>
        <p className={styles.subtext}>
          Enter your phone number and we&apos;ll send you a verification code.
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label htmlFor="phone" className={styles.label}>Phone number</label>
            <div className={styles.phoneRow}>
              <input
                className={styles.countryCode}
                value="+92"
                readOnly
                tabIndex={-1}
                aria-hidden="true"
              />
              <input
                id="phone"
                type="tel"
                className={styles.phoneInput}
                placeholder="3XX XXXXXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                autoFocus
                autoComplete="tel"
                maxLength={11}
                required
              />
            </div>
          </div>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={mutation.isPending || phone.replace(/\D/g, '').length < 10}
          >
            {mutation.isPending ? 'Sending...' : 'Send verification code'}
          </button>
        </form>

        <Link to="/" className={styles.backLink}>
          &larr; Back to home
        </Link>
      </div>
    </div>
  );
}
