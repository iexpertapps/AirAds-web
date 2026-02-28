import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { verifyOTP, sendOTP } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import styles from './VerifyOTPPage.module.css';

const OTP_LENGTH = 6;
const RESEND_COOLDOWN = 30;

export default function VerifyOTPPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const phone = (location.state as { phone?: string })?.phone ?? '';
  const login = useAuthStore((s) => s.login);

  const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
  const [error, setError] = useState('');
  const [resendTimer, setResendTimer] = useState(RESEND_COOLDOWN);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (!phone) {
      navigate('/login', { replace: true });
    }
  }, [phone, navigate]);

  useEffect(() => {
    if (resendTimer <= 0) return;
    const id = setInterval(() => setResendTimer((t) => t - 1), 1000);
    return () => clearInterval(id);
  }, [resendTimer]);

  const verifyMutation = useMutation({
    mutationFn: (code: string) => verifyOTP(phone, code),
    onSuccess: (res) => {
      const { user, access, refresh } = res.data;
      login(user, access, refresh);
      if (user.vendor_id && user.activation_stage === 'PROFILE_COMPLETE') {
        navigate('/portal/dashboard', { replace: true });
      } else {
        navigate('/onboarding/search', { replace: true });
      }
    },
    onError: (err: unknown) => {
      let msg = 'Invalid code. Please try again.';
      if (typeof err === 'object' && err !== null && 'response' in err) {
        const axErr = err as { response?: { data?: { message?: string } } };
        if (axErr.response?.data?.message) {
          msg = axErr.response.data.message;
        }
      }
      setError(msg);
      setDigits(Array(OTP_LENGTH).fill(''));
      inputRefs.current[0]?.focus();
    },
  });

  const resendMutation = useMutation({
    mutationFn: () => sendOTP(phone),
    onSuccess: () => {
      setResendTimer(RESEND_COOLDOWN);
      setError('');
    },
  });

  const handleChange = useCallback(
    (index: number, value: string) => {
      if (!/^\d*$/.test(value)) return;
      const next = [...digits];
      next[index] = value.slice(-1);
      setDigits(next);

      if (value && index < OTP_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }

      if (next.every((d) => d !== '') && next.join('').length === OTP_LENGTH) {
        verifyMutation.mutate(next.join(''));
      }
    },
    [digits, verifyMutation],
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Backspace' && !digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
    },
    [digits],
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
      if (!pasted) return;
      const next = Array(OTP_LENGTH).fill('');
      pasted.split('').forEach((ch, i) => { next[i] = ch; });
      setDigits(next);
      const focusIdx = Math.min(pasted.length, OTP_LENGTH - 1);
      inputRefs.current[focusIdx]?.focus();
      if (pasted.length === OTP_LENGTH) {
        verifyMutation.mutate(pasted);
      }
    },
    [verifyMutation],
  );

  const code = digits.join('');
  const isComplete = code.length === OTP_LENGTH;

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.logo}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />
          <span className={styles.logoText}>AirAd</span>
        </Link>
        <h1 className={styles.heading}>Verify your phone</h1>
        <p className={styles.subtext}>
          Enter the 6-digit code sent to <span className={styles.phoneBold}>{phone}</span>
        </p>

        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            if (isComplete) verifyMutation.mutate(code);
          }}
        >
          <div className={styles.otpRow} onPaste={handlePaste}>
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                className={styles.otpInput}
                value={digit}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                autoFocus={i === 0}
                aria-label={`Digit ${i + 1}`}
                autoComplete="one-time-code"
              />
            ))}
          </div>

          {error && <p className={styles.error} role="alert">{error}</p>}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!isComplete || verifyMutation.isPending}
          >
            {verifyMutation.isPending ? 'Verifying...' : 'Verify & continue'}
          </button>
        </form>

        <div className={styles.resendRow}>
          {resendTimer > 0 ? (
            <span>Resend code in {resendTimer}s</span>
          ) : (
            <button
              className={styles.resendBtn}
              onClick={() => resendMutation.mutate()}
              disabled={resendMutation.isPending}
            >
              {resendMutation.isPending ? 'Sending...' : 'Resend code'}
            </button>
          )}
        </div>

        <Link to="/login" className={styles.backLink}>
          &larr; Change phone number
        </Link>
      </div>
    </div>
  );
}
