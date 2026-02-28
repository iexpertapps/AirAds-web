import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Phone, ArrowRight, ArrowLeft } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Button } from '@/components/dls/Button';
import { sendOTP, verifyOTP } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';
import styles from './AuthPages.module.css';

type Step = 'phone' | 'otp';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');

  const sendOtpMutation = useMutation({
    mutationFn: () => sendOTP(phone),
    onSuccess: () => {
      setStep('otp');
      toast.success('OTP sent to your phone');
    },
    onError: () => {
      toast.error('Failed to send OTP. Please try again.');
    },
  });

  const verifyOtpMutation = useMutation({
    mutationFn: () => verifyOTP(phone, otp),
    onSuccess: (res) => {
      const data = res.data;
      login(data.user, data.access, data.refresh);
      toast.success('Welcome back!');
      navigate('/discover', { replace: true });
    },
    onError: () => {
      toast.error('Invalid OTP. Please try again.');
    },
  });

  const handlePhoneSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = phone.replace(/\s+/g, '');
    if (cleaned.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }
    sendOtpMutation.mutate();
  };

  const handleOtpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length < 4) {
      toast.error('Please enter the complete OTP');
      return;
    }
    verifyOtpMutation.mutate();
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.logo}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logoImg} />
        </Link>
        <h1 className={styles.title}>Welcome Back</h1>
        <p className={styles.subtitle}>Sign in to access your saved preferences and history</p>

        {step === 'phone' ? (
          <form onSubmit={handlePhoneSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label htmlFor="phone" className={styles.label}>Phone Number</label>
              <div className={styles.inputWrap}>
                <Phone size={18} className={styles.inputIcon} />
                <input
                  id="phone"
                  type="tel"
                  placeholder="+92 3XX XXXXXXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className={styles.input}
                  autoComplete="tel"
                  required
                />
              </div>
            </div>
            <Button
              type="submit"
              fullWidth
              loading={sendOtpMutation.isPending}
              icon={<ArrowRight size={18} />}
            >
              Send OTP
            </Button>
          </form>
        ) : (
          <form onSubmit={handleOtpSubmit} className={styles.form}>
            <button
              type="button"
              className={styles.backBtn}
              onClick={() => setStep('phone')}
            >
              <ArrowLeft size={16} /> Change number
            </button>
            <p className={styles.otpSent}>OTP sent to <strong>{phone}</strong></p>
            <div className={styles.inputGroup}>
              <label htmlFor="otp" className={styles.label}>Enter OTP</label>
              <input
                id="otp"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="• • • • • •"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                className={`${styles.input} ${styles.otpInput}`}
                autoComplete="one-time-code"
                autoFocus
                required
              />
            </div>
            <Button
              type="submit"
              fullWidth
              loading={verifyOtpMutation.isPending}
              icon={<ArrowRight size={18} />}
            >
              Verify & Sign In
            </Button>
            <button
              type="button"
              className={styles.resendBtn}
              onClick={() => sendOtpMutation.mutate()}
              disabled={sendOtpMutation.isPending}
            >
              Resend OTP
            </button>
          </form>
        )}

        <div className={styles.altAction}>
          <span>Don't have an account?</span>
          <Link to="/register" className={styles.altLink}>Register</Link>
        </div>
        <Link to="/discover" className={styles.guestLink}>
          Continue as Guest
        </Link>
      </div>
    </div>
  );
}
