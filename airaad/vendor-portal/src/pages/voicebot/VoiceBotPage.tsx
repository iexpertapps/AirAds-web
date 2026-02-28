import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Lock, Plus, X, Mic } from 'lucide-react';
import { getVoiceBotConfig, updateVoiceBotConfig } from '@/api/voicebot';
import { queryKeys } from '@/queryKeys';
import type { UpdateVoiceBotPayload } from '@/api/voicebot';
import { useAuthStore } from '@/store/authStore';
import styles from './VoiceBotPage.module.css';

const TIER_RANK: Record<string, number> = { SILVER: 0, GOLD: 1, DIAMOND: 2, PLATINUM: 3 };

export default function VoiceBotPage() {
  const user = useAuthStore((s) => s.user);
  const vendorId = user?.vendor_id ?? '';
  const tier = user?.subscription_level ?? 'SILVER';
  const tierRank = TIER_RANK[tier] ?? 0;

  if (tierRank < TIER_RANK['GOLD']) {
    return (
      <>
        <h1 className={styles.heading}>Voice Bot</h1>
        <div className={styles.gateOverlay}>
          <div className={styles.gateContent}>
            <Lock size={32} strokeWidth={1.5} className={styles.gateIcon} />
            <h2 className={styles.gateHeading}>Voice Bot requires Gold or higher</h2>
            <p className={styles.gateText}>
              Upgrade your plan to let customers hear about your business through AirAd&apos;s voice assistant.
            </p>
            <Link to="/portal/subscription" className={styles.upgradeBtn}>Upgrade now</Link>
          </div>
        </div>
      </>
    );
  }

  return <VoiceBotForm vendorId={vendorId} tier={tier} />;
}

function VoiceBotForm({ vendorId, tier }: { vendorId: string; tier: string }) {
  const queryClient = useQueryClient();
  const tierRank = TIER_RANK[tier] ?? 0;

  const { data: config, isLoading } = useQuery({
    queryKey: queryKeys.voicebot.config(vendorId),
    queryFn: () => getVoiceBotConfig(vendorId),
    enabled: !!vendorId,
    staleTime: 60_000,
  });

  const [greeting, setGreeting] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [menuItems, setMenuItems] = useState<string[]>(['']);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (config) {
      setGreeting(config.intro_message ?? '');
      setDescription(config.opening_hours_summary ?? '');
      setInstructions(config.custom_qa_pairs?.length ? JSON.stringify(config.custom_qa_pairs) : '');
      setMenuItems(
        Array.isArray(config.menu_items) && config.menu_items.length
          ? config.menu_items.map((m) => (typeof m === 'string' ? m : String(m)))
          : ['']
      );
      setIsActive(config.is_active ?? false);
    }
  }, [config]);

  const mutation = useMutation({
    mutationFn: (payload: UpdateVoiceBotPayload) => updateVoiceBotConfig(vendorId, payload),
    onSuccess: () => {
      setSuccess('Voice bot configuration saved.');
      setError('');
      queryClient.invalidateQueries({ queryKey: queryKeys.voicebot.config(vendorId) });
    },
    onError: () => {
      setError('Failed to save configuration.');
      setSuccess('');
    },
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setError('');
      setSuccess('');
      mutation.mutate({
        intro_message: greeting,
        opening_hours_summary: description,
        custom_qa_pairs: instructions.trim() ? [{ text: instructions }] : [],
        menu_items: menuItems.filter((m) => m.trim()),
        is_active: isActive,
      });
    },
    [greeting, description, instructions, menuItems, isActive, mutation],
  );

  const addMenuItem = useCallback(() => {
    setMenuItems((prev) => [...prev, '']);
  }, []);

  const removeMenuItem = useCallback((index: number) => {
    setMenuItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateMenuItem = useCallback((index: number, value: string) => {
    setMenuItems((prev) => prev.map((item, i) => (i === index ? value : item)));
  }, []);

  if (isLoading) {
    return <div className={styles.loading}>Loading voice bot configuration…</div>;
  }

  const isDynamic = tierRank >= TIER_RANK['DIAMOND'];

  return (
    <>
      <h1 className={styles.heading}>Voice Bot</h1>
      <p className={styles.subtext}>
        Configure how AirAd introduces your business to customers via voice.
        {isDynamic ? ' Dynamic voice bot enabled.' : ' Basic voice introduction.'}
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <div className={styles.toggleRow}>
            <div className={styles.toggleLabel}>
              <span className={styles.toggleTitle}>Voice Bot Active</span>
              <span className={styles.toggleDesc}>Enable voice introduction for your business</span>
            </div>
            <button
              type="button"
              className={[styles.toggle, isActive ? styles['toggle--active'] : ''].join(' ')}
              onClick={() => setIsActive(!isActive)}
              role="switch"
              aria-checked={isActive}
              aria-label="Toggle voice bot"
            />
          </div>
        </div>

        <div className={styles.fieldGroup}>
          <h2 className={styles.groupHeading}>
            <Mic size={16} strokeWidth={1.5} className="inline-icon" />
            Voice Configuration
          </h2>

          <div className={styles.field}>
            <label htmlFor="vb-greeting" className={styles.label}>Greeting text</label>
            <textarea
              id="vb-greeting"
              className={styles.textarea}
              placeholder="Welcome to our restaurant! We serve the best pizza in town."
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              rows={3}
            />
            <span className={styles.hint}>This is what customers hear first</span>
          </div>

          <div className={styles.field}>
            <label htmlFor="vb-desc" className={styles.label}>Business description</label>
            <textarea
              id="vb-desc"
              className={styles.textarea}
              placeholder="A family-run Italian restaurant since 2010..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

        </div>

        {isDynamic && (
          <div className={styles.fieldGroup}>
            <h2 className={styles.groupHeading}>Menu Items (Dynamic)</h2>
            <span className={styles.hint}>Customers can ask about these items by voice</span>

            <div className={styles.menuItems}>
              {menuItems.map((item, i) => (
                <div key={i} className={styles.menuItemRow}>
                  <input
                    className={styles.menuItemInput}
                    value={item}
                    onChange={(e) => updateMenuItem(i, e.target.value)}
                    placeholder={`Item ${i + 1}`}
                  />
                  {menuItems.length > 1 && (
                    <button type="button" className={styles.removeItemBtn} onClick={() => removeMenuItem(i)} aria-label="Remove item">
                      <X size={14} strokeWidth={1.5} />
                    </button>
                  )}
                </div>
              ))}
              <button type="button" className={styles.addItemBtn} onClick={addMenuItem}>
                <Plus size={14} strokeWidth={1.5} /> Add item
              </button>
            </div>
          </div>
        )}

        {isDynamic && (
          <div className={styles.fieldGroup}>
            <h2 className={styles.groupHeading}>Special Instructions</h2>
            <div className={styles.field}>
              <textarea
                className={styles.textarea}
                placeholder="e.g. Always mention our lunch special. Don't discuss competitor prices."
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                rows={3}
              />
            </div>
          </div>
        )}

        {error && <p className={styles.error} role="alert">{error}</p>}
        {success && <p className={styles.success} role="status">{success}</p>}

        <div className={styles.actions}>
          <button type="submit" className={styles.submitBtn} disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving...' : 'Save configuration'}
          </button>
        </div>
      </form>
    </>
  );
}
