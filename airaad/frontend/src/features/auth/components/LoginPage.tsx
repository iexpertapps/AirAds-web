import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { AuthStateManager } from '@/features/auth/store/authStore';
import type { AuthUser } from '@/features/auth/store/authStore';
import { apiClient } from '@/lib/axios';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import styles from './LoginPage.module.css';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type FormValues = z.infer<typeof schema>;

interface LoginResponse {
  success: boolean;
  data: {
    tokens: { access: string; refresh: string };
    user: AuthUser;
  };
  message?: string;
}

function getDefaultRoute(role: string): string {
  switch (role) {
    case 'DATA_ENTRY':
      return '/vendors';
    default:
      return '/';
  }
}

export default function LoginPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (data: FormValues) =>
      apiClient.post<LoginResponse>('/api/v1/auth/login/', data).then((r) => r.data),
    onSuccess: async (data) => {
      // Use unified state manager for consistent login
      AuthStateManager.login(data.data.tokens, data.data.user);
      
      // Wait for state to be properly set before navigation
      try {
        await AuthStateManager.waitForAuthentication(2000);
        const redirect = searchParams.get('redirect');
        const destination = redirect ? decodeURIComponent(redirect) : getDefaultRoute(data.data.user.role);
        
        // Use React Router navigation for SPA experience
        navigate(destination, { replace: true });
      } catch (error) {
        console.error('Authentication state error:', error);
        // Fallback to immediate navigation if timeout occurs
        const redirect = searchParams.get('redirect');
        const destination = redirect ? decodeURIComponent(redirect) : getDefaultRoute(data.data.user.role);
        navigate(destination, { replace: true });
      }
    },
    onError: (err: unknown) => {
      if (
        err !== null &&
        typeof err === 'object' &&
        'response' in err &&
        err.response !== null &&
        typeof err.response === 'object' &&
        'data' in err.response
      ) {
        const data = (err.response as { data: Record<string, unknown> }).data;
        setApiError(typeof data['message'] === 'string' ? data['message'] : 'Login failed.');
      } else {
        setApiError('Login failed. Please try again.');
      }
    },
  });

  function onSubmit(values: FormValues) {
    setApiError(null);
    mutation.mutate(values);
  }

  return (
    <div className={styles.page}>
      <div className={styles.card} role="main">
        <div className={styles.logoArea} aria-label="AirAd Admin Portal">
          <div className={styles.logoIconWrap} aria-hidden="true">
            <img src="/airad_icon.png" alt="" className={styles.logoImg} />
          </div>
          <span className={styles.logo}>AirAd</span>
          <p className={styles.subtitle}>Internal Admin Portal</p>
        </div>

        <form
          className={styles.form}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          aria-label="Sign in form"
        >
          <Input
            id="email"
            label="Email address"
            type="email"
            autoComplete="email"
            autoFocus
            required
            error={errors.email?.message}
            {...register('email')}
          />

          <div className={styles.passwordWrapper}>
            <Input
              id="password"
              label="Password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              error={errors.password?.message}
              {...register('password')}
            />
            <button
              type="button"
              className={styles.showPasswordBtn}
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
            >
              {showPassword ? (
                <EyeOff size={16} strokeWidth={1.5} aria-hidden="true" />
              ) : (
                <Eye size={16} strokeWidth={1.5} aria-hidden="true" />
              )}
            </button>
          </div>

          {apiError && (
            <p className={styles.apiError} role="alert" aria-live="assertive">
              {apiError}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            size="large"
            loading={mutation.isPending}
            className={styles.submitBtn}
          >
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
