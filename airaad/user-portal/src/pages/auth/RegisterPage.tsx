import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Phone, Mail, ArrowRight } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Button } from '@/components/dls/Button';
import { registerUser } from '@/api/auth';
import styles from './AuthPages.module.css';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      registerUser({ phone, full_name: fullName, email: email || undefined }),
    onSuccess: () => {
      toast.success('Account created! Please sign in.');
      navigate('/login', { replace: true });
    },
    onError: () => {
      toast.error('Registration failed. Please try again.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      toast.error('Please enter your name');
      return;
    }
    const cleaned = phone.replace(/\s+/g, '');
    if (cleaned.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }
    mutation.mutate();
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.logo}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logoImg} />
        </Link>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>Join AirAd to save your preferences and search history</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputGroup}>
            <label htmlFor="fullName" className={styles.label}>Full Name</label>
            <div className={styles.inputWrap}>
              <User size={18} className={styles.inputIcon} />
              <input
                id="fullName"
                type="text"
                placeholder="Your full name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={styles.input}
                autoComplete="name"
                required
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label htmlFor="regPhone" className={styles.label}>Phone Number</label>
            <div className={styles.inputWrap}>
              <Phone size={18} className={styles.inputIcon} />
              <input
                id="regPhone"
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

          <div className={styles.inputGroup}>
            <label htmlFor="email" className={styles.label}>
              Email <span className={styles.optional}>(optional)</span>
            </label>
            <div className={styles.inputWrap}>
              <Mail size={18} className={styles.inputIcon} />
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={styles.input}
                autoComplete="email"
              />
            </div>
          </div>

          <Button
            type="submit"
            fullWidth
            loading={mutation.isPending}
            icon={<ArrowRight size={18} />}
          >
            Create Account
          </Button>
        </form>

        <div className={styles.altAction}>
          <span>Already have an account?</span>
          <Link to="/login" className={styles.altLink}>Sign In</Link>
        </div>
        <Link to="/discover" className={styles.guestLink}>
          Continue as Guest
        </Link>
      </div>
    </div>
  );
}
