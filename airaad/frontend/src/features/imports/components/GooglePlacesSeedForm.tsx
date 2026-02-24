import { useState, useCallback, useMemo } from 'react';
import { MapPin, Search, Check, AlertTriangle, Database, RefreshCw } from 'lucide-react';
import { Select } from '@/shared/components/dls/Select';
import { Input } from '@/shared/components/dls/Input';
import { Button } from '@/shared/components/dls/Button';
import { Table } from '@/shared/components/dls/Table';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { ImportStatusBadge } from '@/shared/components/dls/Badge';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { useToast } from '@/shared/hooks/useToast';
import {
  useCountries,
  useCities,
  useAreas,
  useCategories,
  useSeedBatches,
  useSeedMutation,
} from '../hooks/useGooglePlacesSeed';
import type { CategoryTag, SeedBatchItem } from '../hooks/useGooglePlacesSeed';
import styles from './GooglePlacesSeedForm.module.css';

type ImportStatus = 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED';

/* ── Helpers — zero logic in JSX ── */

function toSelectOptions(items: Array<{ id: string; name: string }> | undefined) {
  return (items ?? []).map((i) => ({ value: i.id, label: i.name }));
}

function computeProgress(batch: SeedBatchItem): number {
  if (batch.total_rows === 0) return 0;
  return Math.round((batch.processed_rows / batch.total_rows) * 100);
}

function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function progressFillClass(status: ImportStatus): string {
  const base = styles.progressMiniFill ?? '';
  if (status === 'DONE') return `${base} ${styles.progressMiniFillDone ?? ''}`;
  if (status === 'FAILED') return `${base} ${styles.progressMiniFillFailed ?? ''}`;
  return base;
}

/* ── Component ── */

export default function GooglePlacesSeedForm() {
  const toast = useToast();

  /* ── Form state ── */
  const [countryId, setCountryId] = useState('');
  const [cityId, setCityId] = useState('');
  const [areaId, setAreaId] = useState('');
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('restaurants food');
  const [radiusM, setRadiusM] = useState('1500');
  const [conflictMessage, setConflictMessage] = useState('');

  /* ── Queries ── */
  const countriesQuery = useCountries();
  const citiesQuery = useCities(countryId);
  const areasQuery = useAreas(cityId);
  const categoriesQuery = useCategories();
  const batchesQuery = useSeedBatches();
  const seedMutation = useSeedMutation();

  /* ── Derived data ── */
  const countryOptions = useMemo(() => toSelectOptions(countriesQuery.data), [countriesQuery.data]);
  const cityOptions = useMemo(() => toSelectOptions(citiesQuery.data), [citiesQuery.data]);
  const areaOptions = useMemo(() => toSelectOptions(areasQuery.data), [areasQuery.data]);
  const categories: CategoryTag[] = categoriesQuery.data ?? [];
  const batches: SeedBatchItem[] = batchesQuery.data ?? [];

  const canSubmit = areaId !== '' && searchQuery.trim() !== '';
  const radiusNum = parseInt(radiusM, 10);
  const radiusValid = !isNaN(radiusNum) && radiusNum >= 100 && radiusNum <= 5000;

  /* ── Handlers ── */

  const handleCountryChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setCountryId(e.target.value);
      setCityId('');
      setAreaId('');
      setConflictMessage('');
    },
    [],
  );

  const handleCityChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setCityId(e.target.value);
      setAreaId('');
      setConflictMessage('');
    },
    [],
  );

  const handleAreaChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      setAreaId(e.target.value);
      setConflictMessage('');
    },
    [],
  );

  const toggleCategory = useCallback((tagId: string) => {
    setSelectedCategoryIds((prev) => {
      const next = new Set(prev);
      if (next.has(tagId)) {
        next.delete(tagId);
      } else {
        next.add(tagId);
      }
      return next;
    });
  }, []);

  const handleSeed = useCallback(() => {
    if (!canSubmit || !radiusValid) return;
    setConflictMessage('');

    seedMutation.mutate(
      {
        country_id: countryId,
        city_id: cityId,
        area_id: areaId,
        category_tags: Array.from(selectedCategoryIds),
        search_query: searchQuery.trim(),
        radius_m: radiusNum,
      },
      {
        onSuccess: () => {
          toast.success('Google Places seed queued');
        },
        onError: (error: unknown) => {
          const axiosErr = error as { response?: { status?: number; data?: { message?: string; errors?: Record<string, string[]> } } };
          const status = axiosErr.response?.status;
          const serverMessage = axiosErr.response?.data?.message;

          if (status === 409) {
            setConflictMessage(
              serverMessage ?? 'An identical import is already in progress.',
            );
          } else if (status === 400) {
            toast.error(serverMessage ?? 'Please check your selections and try again.');
          } else {
            toast.error(serverMessage ?? 'Something went wrong. Please try again later.');
          }
        },
      },
    );
  }, [
    canSubmit,
    radiusValid,
    countryId,
    cityId,
    areaId,
    selectedCategoryIds,
    searchQuery,
    radiusNum,
    seedMutation,
    toast,
  ]);

  /* ── Table columns ── */

  const batchColumns: ColumnDef<SeedBatchItem>[] = useMemo(
    () => [
      {
        key: 'area_name',
        header: 'Area',
        render: (b) => <span className={styles.areaCell}>{b.area_name || '—'}</span>,
      },
      {
        key: 'search_query',
        header: 'Query',
        render: (b) => (
          <span className={styles.queryCell} title={b.search_query}>
            {b.search_query}
          </span>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        render: (b) => <ImportStatusBadge status={b.status} />,
      },
      {
        key: 'progress',
        header: 'Progress',
        render: (b) => {
          const pct = computeProgress(b);
          return (
            <div className={styles.progressMini}>
              <div
                className={styles.progressMiniBar}
                role="progressbar"
                aria-valuenow={b.processed_rows}
                aria-valuemin={0}
                aria-valuemax={b.total_rows}
              >
                <div
                  className={progressFillClass(b.status)}
                  style={{ ['--progress-width' as string]: `${pct}%` } as React.CSSProperties}
                />
              </div>
              <span className={styles.progressMiniLabel}>
                {b.processed_rows}/{b.total_rows}
              </span>
            </div>
          );
        },
      },
      {
        key: 'error_count',
        header: 'Errors',
        render: (b) => (
          <span className={b.error_count > 0 ? styles.statBad : styles.statGood}>
            {b.error_count}
          </span>
        ),
      },
      {
        key: 'created_at',
        header: 'Started',
        render: (b) => <span className={styles.dateCell}>{formatShortDate(b.created_at)}</span>,
      },
    ],
    [],
  );

  /* ── Render ── */

  return (
    <section className={styles.seedSection} aria-label="Seed vendors from Google Places">
      {/* Header */}
      <div className={styles.seedHeader}>
        <MapPin size={20} strokeWidth={1.5} aria-hidden="true" className={styles.seedIcon} />
        <h2 className={styles.seedTitle}>Seed from Google Places</h2>
        <span className={styles.seedSubtitle}>Country → City → Area → Category</span>
      </div>

      {/* Conflict banner */}
      {conflictMessage && (
        <div className={styles.conflictBanner} role="alert">
          <AlertTriangle
            size={16}
            strokeWidth={1.5}
            aria-hidden="true"
            className={styles.conflictIcon}
          />
          <span className={styles.conflictText}>{conflictMessage}</span>
        </div>
      )}

      {/* Form grid — 2 columns */}
      <div className={styles.formGrid}>
        <Select
          id="seed-country"
          label="Country"
          placeholder="Select country…"
          options={countryOptions}
          value={countryId}
          onChange={handleCountryChange}
          required
          disabled={countriesQuery.isLoading}
        />

        <Select
          id="seed-city"
          label="City"
          placeholder={countryId ? 'Select city…' : 'Select country first'}
          options={cityOptions}
          value={cityId}
          onChange={handleCityChange}
          required
          disabled={countryId === '' || citiesQuery.isLoading}
        />

        <Select
          id="seed-area"
          label="Area"
          placeholder={cityId ? 'Select area…' : 'Select city first'}
          options={areaOptions}
          value={areaId}
          onChange={handleAreaChange}
          required
          disabled={cityId === '' || areasQuery.isLoading}
        />

        <Input
          id="seed-radius"
          label="Search radius (meters)"
          type="number"
          value={radiusM}
          onChange={(e) => setRadiusM(e.target.value)}
          hint="100–5000m"
          error={radiusM !== '' && !radiusValid ? 'Must be between 100 and 5000' : undefined}
        />

        <Input
          id="seed-query"
          label="Search query"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="restaurants food"
          required
          hint="Google Places keyword for Nearby Search"
        />

        {/* Categories — full width */}
        <div className={styles.categoriesField}>
          <span className={styles.categoriesLabel}>
            Category tags
            {categoriesQuery.isLoading && ' (loading…)'}
          </span>
          <div className={styles.categoriesGrid} role="group" aria-label="Category tags">
            {categories.map((tag) => {
              const isSelected = selectedCategoryIds.has(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  role="checkbox"
                  aria-checked={isSelected}
                  className={[
                    styles.categoryChip,
                    isSelected ? styles.categoryChipSelected : '',
                  ].join(' ')}
                  onClick={() => toggleCategory(tag.id)}
                >
                  {isSelected && (
                    <Check
                      size={12}
                      strokeWidth={2}
                      aria-hidden="true"
                      className={styles.categoryChipCheck}
                    />
                  )}
                  {tag.display_label ?? tag.name}
                </button>
              );
            })}
            {categories.length === 0 && !categoriesQuery.isLoading && (
              <span className={styles.queryCell}>No category tags configured</span>
            )}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className={styles.formActions}>
        <Button
          variant="primary"
          leftIcon={<Search size={16} strokeWidth={1.5} />}
          loading={seedMutation.isPending}
          disabled={!canSubmit || !radiusValid}
          onClick={handleSeed}
        >
          Seed vendors
        </Button>
      </div>

      {/* Batch history table */}
      <div className={styles.batchesSection}>
        <div className={styles.batchesSectionHeader}>
          <Database size={16} strokeWidth={1.5} aria-hidden="true" />
          <h3 className={styles.batchesSectionTitle}>Google Places batches</h3>
          <span className={styles.batchesSectionCount}>({batches.length})</span>
          <Button
            variant="ghost"
            size="compact"
            leftIcon={<RefreshCw size={14} strokeWidth={1.5} />}
            onClick={() => void batchesQuery.refetch()}
            aria-label="Refresh batch list"
          >
            Refresh
          </Button>
        </div>

        <Table
          aria-label="Google Places seed batches"
          columns={batchColumns}
          data={batches}
          isLoading={batchesQuery.isLoading}
          isEmpty={!batchesQuery.isLoading && batches.length === 0}
          emptyState={
            <EmptyState
              heading="No Google Places batches yet"
              subheading="Select a country, city, and area above, then seed vendors from Google Places."
            />
          }
        />
      </div>
    </section>
  );
}
