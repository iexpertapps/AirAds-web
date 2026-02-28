import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { updateVendorProfile, updateBusinessHours } from '@/api/vendor';
import { useAuthStore } from '@/store/authStore';
import { queryKeys } from '@/queryKeys';
import type { VendorProfile } from '@/api/vendor';
import styles from './ProfileEditPage.module.css';

function parseHoursText(text: string): Record<string, { open: string; close: string; is_closed: boolean }> {
  const result: Record<string, { open: string; close: string; is_closed: boolean }> = {};
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const match = trimmed.match(/^(MON|TUE|WED|THU|FRI|SAT|SUN):\s*(.+)$/i);
    if (!match) continue;
    const day = match[1].toUpperCase();
    const value = match[2].trim();
    if (value.toLowerCase() === 'closed') {
      result[day] = { open: '00:00', close: '00:00', is_closed: true };
    } else {
      const times = value.split(/\s*[–-]\s*/);
      result[day] = { open: times[0] || '09:00', close: times[1] || '22:00', is_closed: false };
    }
  }
  return result;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export default function ProfileEditPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const vendorId = user?.vendor_id;

  const { data: profile, isLoading } = useQuery({
    queryKey: queryKeys.vendor.profile(vendorId ?? ''),
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<VendorProfile>>(
        '/api/v1/vendor-portal/profile/',
      );
      return data.data;
    },
    enabled: !!vendorId,
    staleTime: 60_000,
  });

  const [description, setDescription] = useState('');
  const [hours, setHours] = useState('');
  const [originalHoursText, setOriginalHoursText] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (profile) {
      setDescription(profile.description ?? '');
      const bh = profile.business_hours as unknown;
      if (typeof bh === 'object' && bh !== null) {
        const dayOrder = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
        const bhMap = bh as Record<string, { open: string; close: string; is_closed: boolean }>;
        const lines = dayOrder
          .filter((d) => d in bhMap)
          .map((d) => {
            const info = bhMap[d];
            return info.is_closed ? `${d}: Closed` : `${d}: ${info.open} – ${info.close}`;
          });
        const text = lines.join('\n');
        setHours(text);
        setOriginalHoursText(text);
      } else {
        const text = typeof bh === 'string' ? bh : '';
        setHours(text);
        setOriginalHoursText(text);
      }
    }
  }, [profile]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!vendorId) throw new Error('No vendor ID');
      await updateVendorProfile(vendorId, {
        description: description || undefined,
      });
      if (hours && hours !== originalHoursText) {
        const parsed = parseHoursText(hours);
        await updateBusinessHours(parsed);
      }
    },
    onSuccess: () => {
      setSuccess('Profile updated successfully.');
      setError('');
      queryClient.invalidateQueries({ queryKey: queryKeys.vendor.profile(vendorId ?? '') });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.overview() });
    },
    onError: () => {
      setError('Failed to update profile. Please try again.');
      setSuccess('');
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      setSuccess('');
      mutation.mutate();
    },
    [mutation],
  );

  if (isLoading) {
    return <div className={styles.loading}>Loading profile…</div>;
  }

  return (
    <>
      <h1 className={styles.heading}>Edit Profile</h1>
      <p className={styles.subtext}>Update your business information visible to customers.</p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <h2 className={styles.groupHeading}>Business Information</h2>

          <div className={styles.field}>
            <label htmlFor="biz-name" className={styles.label}>Business name</label>
            <input
              id="biz-name"
              type="text"
              className={styles.input}
              value={profile?.business_name ?? ''}
              readOnly
            />
            <span className={styles.hint}>Contact support to change your business name</span>
          </div>

          <div className={styles.field}>
            <label htmlFor="address" className={styles.label}>Address</label>
            <input
              id="address"
              type="text"
              className={styles.input}
              value={profile?.address_text ?? ''}
              readOnly
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="area" className={styles.label}>Area</label>
            <input
              id="area"
              type="text"
              className={styles.input}
              value={profile?.area_name ?? ''}
              readOnly
            />
          </div>
        </div>

        <div className={styles.fieldGroup}>
          <h2 className={styles.groupHeading}>Contact & Hours</h2>

          <div className={styles.field}>
            <label htmlFor="phone" className={styles.label}>Business phone</label>
            <input
              id="phone"
              type="tel"
              className={styles.input}
              value={profile?.phone_masked ?? ''}
              readOnly
            />
            <span className={styles.hint}>Phone is managed through account settings</span>
          </div>

          <div className={styles.field}>
            <label htmlFor="desc" className={styles.label}>Business description</label>
            <textarea
              id="desc"
              className={styles.textarea}
              placeholder="Describe your business..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="hours" className={styles.label}>Business hours</label>
            <textarea
              id="hours"
              className={styles.textarea}
              placeholder={"Mon–Sat: 9:00 AM – 10:00 PM\nSun: Closed"}
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              rows={4}
            />
          </div>
        </div>

        {error && <p className={styles.error} role="alert">{error}</p>}
        {success && <p className={styles.success} role="status">{success}</p>}

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </form>
    </>
  );
}
