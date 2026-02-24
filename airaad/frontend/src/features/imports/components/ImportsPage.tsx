import { lazy, Suspense, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Papa from 'papaparse';
import { Upload, Download, Eye, MapPin } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { ImportStatusBadge } from '@/shared/components/dls/Badge';
import { Button } from '@/shared/components/dls/Button';
import { Drawer } from '@/shared/components/dls/Drawer';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { useToast } from '@/shared/hooks/useToast';
import { usePermission } from '@/shared/hooks/usePermission';
import styles from './ImportsPage.module.css';

const GooglePlacesSeedForm = lazy(() => import('./GooglePlacesSeedForm'));

type ImportTab = 'csv' | 'google-places';

type ImportStatus = 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED';

interface ImportBatch {
  id: string;
  import_type: string;
  file_key: string;
  file_name: string;
  status: ImportStatus;
  uploaded_by_email: string;
  created_by_email: string;
  created_at: string;
  total_rows: number;
  processed_rows: number;
  vendors_created: number;
  vendors_failed: number;
  error_count: number;
  error_log?: Array<{ row: number; field: string; message: string }>;
}

interface ImportListResponse {
  data: ImportBatch[];
}

const REQUIRED_COLUMNS = ['business_name', 'longitude', 'latitude', 'city_slug', 'area_slug'];

const GOOGLE_PLACES_ROLES = ['SUPER_ADMIN', 'CITY_MANAGER', 'OPERATIONS_MANAGER'] as const;
const CSV_UPLOAD_ROLES = ['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY'] as const;

function hasActiveJobs(data: ImportBatch[] | undefined): boolean {
  return (data ?? []).some((b) => b.status === 'QUEUED' || b.status === 'PROCESSING');
}

export default function ImportsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [drawerBatchId, setDrawerBatchId] = useState<string | null>(null);
  const [previewRows, setPreviewRows] = useState<string[][]>([]);
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [missingCols, setMissingCols] = useState<string[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const canSeedGooglePlaces = usePermission([...GOOGLE_PLACES_ROLES]);
  const canUploadCSV = usePermission([...CSV_UPLOAD_ROLES]);
  const defaultTab: ImportTab = canSeedGooglePlaces && !canUploadCSV ? 'google-places' : 'csv';
  const [activeTab, setActiveTab] = useState<ImportTab>(defaultTab);
  const showTabs = canSeedGooglePlaces && canUploadCSV;

  const { data: liveDrawerBatch } = useQuery({
    queryKey: queryKeys.imports.detail(drawerBatchId ?? ''),
    queryFn: () =>
      apiClient
        .get<{ data: ImportBatch }>(`/api/v1/imports/${drawerBatchId}/`)
        .then((r) => r.data.data),
    enabled: drawerBatchId !== null,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === 'QUEUED' || s === 'PROCESSING' ? 5_000 : false;
    },
  });

  const { data: batches, isLoading } = useQuery({
    queryKey: queryKeys.imports.list(),
    queryFn: () =>
      apiClient.get<ImportListResponse>('/api/v1/imports/').then((r) => r.data.data),
    refetchInterval: (query) =>
      hasActiveJobs(query.state.data as ImportBatch[] | undefined) ? 10_000 : false,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return apiClient.post('/api/v1/imports/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      toast.success('Import queued successfully');
      setPendingFile(null);
      setPreviewRows([]);
      setPreviewHeaders([]);
      setMissingCols([]);
      void qc.invalidateQueries({ queryKey: queryKeys.imports.list() });
    },
  });

  function parseCSVPreview(file: File) {
    Papa.parse<string[]>(file, {
      preview: 6,
      complete: (results) => {
        const rows = results.data as string[][];
        const headers = rows[0] ?? [];
        const dataRows = rows.slice(1);
        setPreviewHeaders(headers);
        setPreviewRows(dataRows);
        const missing = REQUIRED_COLUMNS.filter(
          (col) => !headers.map((h) => h.toLowerCase().trim()).includes(col),
        );
        setMissingCols(missing);
        setPendingFile(file);
      },
    });
  }

  function handleFileSelect(file: File) {
    if (!file.name.endsWith('.csv')) {
      toast.error('Only .csv files are accepted');
      return;
    }
    parseCSVPreview(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }

  function handleExportErrors(batch: ImportBatch) {
    if (!batch.error_log?.length) return;
    const csv = Papa.unparse(batch.error_log);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `import-errors-${batch.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const columns: ColumnDef<ImportBatch>[] = [
    {
      key: 'file_name',
      header: 'File Name',
      render: (b) => <span className={styles.fileName}>{b.file_name}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (b) => <ImportStatusBadge status={b.status} />,
    },
    {
      key: 'uploaded_by_email',
      header: 'Uploaded By',
      render: (b) => <span>{b.uploaded_by_email}</span>,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (b) => <span>{new Date(b.created_at).toLocaleString()}</span>,
    },
    {
      key: 'vendors_created',
      header: 'Imported',
      render: (b) => <span className={styles.statGood}>{b.vendors_created}</span>,
    },
    {
      key: 'vendors_failed',
      header: 'Failed',
      render: (b) => (
        <span className={b.vendors_failed > 0 ? styles.statBad : styles.statGood}>
          {b.vendors_failed}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (b) => (
        <div className={styles.actions}>
          <Button
            variant="ghost"
            size="compact"
            leftIcon={<Eye size={14} />}
            onClick={() => setDrawerBatchId(b.id)}
            aria-label={`View details for ${b.file_name}`}
          >
            Details
          </Button>
          {b.error_log && b.error_log.length > 0 && (
            <Button
              variant="ghost"
              size="compact"
              leftIcon={<Download size={14} />}
              onClick={() => handleExportErrors(b)}
              aria-label={`Download error log for ${b.file_name}`}
            >
              Errors
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <AdminLayout title="Import Management">
      <PageHeader
        heading="Import center"
        subheading="Import vendor data via CSV upload or Google Places seeding"
      />

      {/* Tab bar — only shown when user has access to both methods */}
      {showTabs && (
        <div className={styles.tabBar} role="tablist" aria-label="Import method">
          <button
            role="tab"
            aria-selected={activeTab === 'csv'}
            className={[styles.tab, activeTab === 'csv' ? styles.tabActive : ''].join(' ')}
            onClick={() => setActiveTab('csv')}
          >
            <Upload size={16} strokeWidth={1.5} aria-hidden="true" className={styles.tabIcon} />
            CSV upload
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'google-places'}
            className={[styles.tab, activeTab === 'google-places' ? styles.tabActive : ''].join(' ')}
            onClick={() => setActiveTab('google-places')}
          >
            <MapPin size={16} strokeWidth={1.5} aria-hidden="true" className={styles.tabIcon} />
            Google Places
          </button>
        </div>
      )}

      {/* Google Places Seed tab */}
      {(activeTab === 'google-places' || (!showTabs && canSeedGooglePlaces)) && (
        <Suspense fallback={<SkeletonTable />}>
          <GooglePlacesSeedForm />
        </Suspense>
      )}

      {/* CSV Upload tab */}
      {(activeTab === 'csv' || (!showTabs && canUploadCSV)) && (
      <>
      {/* Upload Zone */}
      <div
        className={[styles.dropZone, isDragging ? styles.dropZoneDragging : ''].join(' ')}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        aria-label="Drop CSV file here or click to browse"
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={32} strokeWidth={1} aria-hidden="true" className={styles.uploadIcon} />
        <p className={styles.dropText}>Drag & drop a CSV file here, or <span className={styles.browseLink}>browse</span></p>
        <p className={styles.dropHint}>Only .csv files accepted</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className={styles.hiddenInput}
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileSelect(file);
          }}
        />
      </div>

      {/* CSV Preview */}
      {pendingFile && previewHeaders.length > 0 && (
        <div className={styles.preview}>
          <div className={styles.previewHeader}>
            <h2 className={styles.previewTitle}>Preview: {pendingFile.name}</h2>
            {missingCols.length > 0 && (
              <p className={styles.missingCols} role="alert">
                Missing required columns: <strong>{missingCols.join(', ')}</strong>
              </p>
            )}
          </div>
          <div className={styles.previewTableWrapper}>
            <table className={styles.previewTable}>
              <thead>
                <tr>
                  {previewHeaders.map((h, i) => (
                    <th
                      key={i}
                      className={[
                        styles.previewTh,
                        missingCols.includes(h.toLowerCase().trim()) ? styles.missingCol : '',
                      ].join(' ')}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci} className={styles.previewTd}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={styles.previewActions}>
            <Button variant="secondary" onClick={() => { setPendingFile(null); setPreviewRows([]); setPreviewHeaders([]); setMissingCols([]); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              leftIcon={<Upload size={16} />}
              loading={uploadMutation.isPending}
              disabled={missingCols.length > 0}
              onClick={() => pendingFile && uploadMutation.mutate(pendingFile)}
            >
              Upload & Import
            </Button>
          </div>
        </div>
      )}

      {/* Batch Table */}
      <Table
        aria-label="Import batches table"
        columns={columns}
        data={(batches ?? []).filter((b) => b.import_type === 'CSV' || !b.import_type)}
        isLoading={isLoading}
        isEmpty={!isLoading && (batches ?? []).filter((b) => b.import_type === 'CSV' || !b.import_type).length === 0}
        emptyState={
          <EmptyState
            heading="No CSV imports yet"
            subheading="Upload a CSV file above to start importing vendor data."
          />
        }
      />
      </>
      )}

      {/* Batch Detail Drawer */}
      <Drawer
        isOpen={drawerBatchId !== null}
        onClose={() => setDrawerBatchId(null)}
        title={liveDrawerBatch?.file_name ?? 'Import Details'}
      >
        {liveDrawerBatch && (
          <div className={styles.drawerContent}>
            <div className={styles.progressSection}>
              <p className={styles.progressLabel}>
                {liveDrawerBatch.vendors_created + liveDrawerBatch.vendors_failed} / {liveDrawerBatch.total_rows} rows processed
              </p>
              <div className={styles.progressBar} role="progressbar"
                aria-valuenow={liveDrawerBatch.vendors_created + liveDrawerBatch.vendors_failed}
                aria-valuemin={0}
                aria-valuemax={liveDrawerBatch.total_rows}
              >
                <div
                  className={styles.progressFill}
                  style={{ ['--progress-width' as string]: `${liveDrawerBatch.total_rows > 0 ? ((liveDrawerBatch.vendors_created + liveDrawerBatch.vendors_failed) / liveDrawerBatch.total_rows) * 100 : 0}%` } as React.CSSProperties}
                />
              </div>
              <div className={styles.progressStats}>
                <span className={styles.statGood}>✓ {liveDrawerBatch.vendors_created} created</span>
                <span className={styles.statBad}>✗ {liveDrawerBatch.vendors_failed} failed</span>
              </div>
            </div>

            {liveDrawerBatch.error_log && liveDrawerBatch.error_log.length > 0 && (
              <div className={styles.errorLog}>
                <div className={styles.errorLogHeader}>
                  <h3 className={styles.errorLogTitle}>Error Log ({liveDrawerBatch.error_log.length} errors)</h3>
                  <Button variant="secondary" size="compact" leftIcon={<Download size={14} />}
                    onClick={() => handleExportErrors(liveDrawerBatch)}>
                    Export CSV
                  </Button>
                </div>
                <table className={styles.errorTable}>
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Field</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {liveDrawerBatch.error_log.map((err, i) => (
                      <tr key={i}>
                        <td>{err.row}</td>
                        <td><code>{err.field}</code></td>
                        <td>{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </AdminLayout>
  );
}
