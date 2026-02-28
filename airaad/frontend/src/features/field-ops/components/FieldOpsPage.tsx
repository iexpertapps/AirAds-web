import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, Link } from 'react-router-dom';
import { AlertTriangle, Camera, Upload, X } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { FiltersBar } from '@/shared/components/dls/FiltersBar';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { Badge } from '@/shared/components/dls/Badge';
import { Button } from '@/shared/components/dls/Button';
import { Drawer } from '@/shared/components/dls/Drawer';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { RoleGate } from '@/shared/components/RoleGate';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { useToast } from '@/shared/hooks/useToast';
import styles from './FieldOpsPage.module.css';

interface GPSPoint {
  latitude: number;
  longitude: number;
}

interface FieldVisit {
  id: string;
  vendor_id: string;
  vendor_name: string;
  agent_email: string;
  visited_at: string;
  gps_confirmed: boolean;
  photos_count: number;
  drift_meters?: number;
  notes?: string;
  gps_confirmed_point?: GPSPoint | undefined;
  vendor_gps?: GPSPoint | undefined;
}

interface FieldOpsResponse {
  count: number;
  data: FieldVisit[];
}

interface FieldPhoto {
  id: string;
  photo_url: string;
  caption: string;
  uploaded_at: string;
}

interface FieldPhotoListResponse {
  data: FieldPhoto[];
}

interface GPSSplitMapProps {
  vendorPoint: GPSPoint;
  confirmedPoint: GPSPoint;
}

function GPSSplitMap({ vendorPoint, confirmedPoint }: GPSSplitMapProps) {
  const vendorLatLng: LatLngExpression = [vendorPoint.latitude, vendorPoint.longitude];
  const confirmedLatLng: LatLngExpression = [confirmedPoint.latitude, confirmedPoint.longitude];
  return (
    <div className={styles.splitMapRow}>
      <div className={styles.splitMapPane}>
        <p className={styles.splitMapLabel}>Reported (Vendor GPS)</p>
        <div className={styles.splitMapContainer}>
          <MapContainer
            center={vendorLatLng}
            zoom={16}
            scrollWheelZoom={false}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            <Marker position={vendorLatLng}>
              <Popup>Vendor GPS</Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>
      <div className={styles.splitMapPane}>
        <p className={styles.splitMapLabel}>Confirmed (Field Agent)</p>
        <div className={styles.splitMapContainer}>
          <MapContainer
            center={confirmedLatLng}
            zoom={16}
            scrollWheelZoom={false}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            <Marker position={confirmedLatLng}>
              <Popup>Confirmed GPS</Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>
    </div>
  );
}

const DRIFT_THRESHOLD_METERS = 20;

export default function FieldOpsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedVisit, setSelectedVisit] = useState<FieldVisit | null>(null);
  const [uploadCaption, setUploadCaption] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();
  const toast = useToast();

  const search = searchParams.get('search') ?? '';
  const page = parseInt(searchParams.get('page') ?? '1', 10);
  const debouncedSearch = useDebounce(search);

  function updateParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) { next.set(key, value); } else { next.delete(key); }
      next.set('page', '1');
      return next;
    });
  }

  const filters = {
    search: debouncedSearch || undefined,
    page,
    page_size: 25,
  };

  const { data: visitPhotos } = useQuery({
    queryKey: queryKeys.fieldOps.photos(selectedVisit?.id ?? ''),
    queryFn: () =>
      apiClient
        .get<FieldPhotoListResponse>(`/api/v1/field-ops/${selectedVisit?.id ?? ''}/photos/`)
        .then((r) => r.data.data),
    enabled: !!selectedVisit?.id,
  });

  const uploadPhotoMutation = useMutation({
    mutationFn: ({ visitId, file, caption }: { visitId: string; file: File; caption: string }) => {
      const form = new FormData();
      form.append('file', file);
      if (caption) form.append('caption', caption);
      return apiClient.post(`/api/v1/field-ops/${visitId}/photos/upload/`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      toast.success('Photo uploaded');
      setUploadFile(null);
      setUploadCaption('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      void qc.invalidateQueries({ queryKey: queryKeys.fieldOps.photos(selectedVisit?.id ?? '') });
    },
    onError: () => toast.error('Failed to upload photo'),
  });

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.fieldOps.list(filters),
    queryFn: () =>
      apiClient
        .get<FieldOpsResponse>('/api/v1/field-ops/', { params: filters })
        .then((r) => r.data),
  });

  const columns: ColumnDef<FieldVisit>[] = [
    {
      key: 'vendor_name',
      header: 'Vendor',
      render: (v) => (
        <Link to={`/vendors/${v.vendor_id}`} className={styles.vendorLink}>
          {v.vendor_name}
        </Link>
      ),
    },
    {
      key: 'agent_email',
      header: 'Agent',
      render: (v) => <span>{v.agent_email}</span>,
    },
    {
      key: 'visited_at',
      header: 'Visit Date',
      sortable: true,
      render: (v) => <span>{new Date(v.visited_at).toLocaleDateString()}</span>,
    },
    {
      key: 'gps_confirmed',
      header: 'GPS Confirmed',
      render: (v) => (
        <Badge
          variant={v.gps_confirmed ? 'success' : 'neutral'}
          label={v.gps_confirmed ? 'Confirmed' : 'Pending'}
        />
      ),
    },
    {
      key: 'photos_count',
      header: 'Photos',
      render: (v) => (
        <span className={styles.photoCount}>
          <Camera size={14} aria-hidden="true" />
          {v.photos_count}
        </span>
      ),
    },
    {
      key: 'drift',
      header: 'Drift Alert',
      render: (v) =>
        v.drift_meters != null && v.drift_meters > DRIFT_THRESHOLD_METERS ? (
          <Badge
            variant="warning"
            label={`${v.drift_meters.toFixed(0)}m drift`}
            icon={<AlertTriangle size={12} />}
          />
        ) : (
          <span className={styles.noDrift}>—</span>
        ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (v) => (
        <Button
          variant="ghost"
          size="compact"
          onClick={() => setSelectedVisit(v)}
          aria-label={`View details for visit at ${v.vendor_name}`}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <AdminLayout title="Field Operations">
      <PageHeader
        heading="Field Operations"
        subheading="Field agent visit log and GPS verification"
      />

      <FiltersBar
        search={search}
        onSearchChange={(v) => updateParam('search', v)}
        searchPlaceholder="Search vendors or agents…"
        filters={
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER']}>
            {/* Agent filter hidden for FIELD_AGENT — API enforces own-visits-only */}
            <span className={styles.filterNote}>Showing visits you have access to</span>
          </RoleGate>
        }
      />

      <Table
        aria-label="Field visits table"
        columns={columns}
        data={data?.data ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (data?.data ?? []).length === 0}
        emptyState={
          <EmptyState
            heading="No field visits found"
            subheading="Field agent visits will appear here once submitted."
          />
        }
        pagination={
          data
            ? {
                page,
                pageSize: 25,
                total: data.count,
                onPageChange: (p) => updateParam('page', String(p)),
              }
            : undefined
        }
      />

      <Drawer
        isOpen={selectedVisit !== null}
        onClose={() => { setSelectedVisit(null); setUploadFile(null); setUploadCaption(''); }}
        title={selectedVisit ? `Visit: ${selectedVisit.vendor_name}` : 'Visit Details'}
      >
        {selectedVisit && (
          <div className={styles.visitDetail}>
            <dl className={styles.dl}>
              <dt>Agent</dt>
              <dd>{selectedVisit.agent_email}</dd>
              <dt>Visit Date</dt>
              <dd>{new Date(selectedVisit.visited_at).toLocaleString()}</dd>
              <dt>GPS Confirmed</dt>
              <dd>{selectedVisit.gps_confirmed ? 'Yes' : 'No'}</dd>
              <dt>Photos</dt>
              <dd>{selectedVisit.photos_count}</dd>
              {selectedVisit.drift_meters != null && (
                <>
                  <dt>GPS Drift</dt>
                  <dd className={selectedVisit.drift_meters > DRIFT_THRESHOLD_METERS ? styles.driftWarning : ''}>
                    {selectedVisit.drift_meters.toFixed(1)}m
                    {selectedVisit.drift_meters > DRIFT_THRESHOLD_METERS && ' ⚠ Above threshold'}
                  </dd>
                </>
              )}
              {selectedVisit.notes && (
                <>
                  <dt>Notes</dt>
                  <dd>{selectedVisit.notes}</dd>
                </>
              )}
            </dl>

            {/* GPS Split Map */}
            {selectedVisit.vendor_gps && selectedVisit.gps_confirmed_point && (
              <section className={styles.mapSection}>
                <h3 className={styles.sectionHeading}>GPS Comparison</h3>
                <GPSSplitMap
                  vendorPoint={selectedVisit.vendor_gps}
                  confirmedPoint={selectedVisit.gps_confirmed_point}
                />
              </section>
            )}

            {/* Photo Gallery */}
            {visitPhotos && visitPhotos.length > 0 && (
              <section className={styles.photoSection}>
                <h3 className={styles.sectionHeading}>Photos ({visitPhotos.length})</h3>
                <div className={styles.photoGrid}>
                  {visitPhotos.map((photo) => (
                    <div key={photo.id} className={styles.photoCard}>
                      <img
                        src={photo.photo_url}
                        alt={photo.caption || 'Field visit photo'}
                        className={styles.photoImg}
                      />
                      {photo.caption && (
                        <p className={styles.photoCaption}>{photo.caption}</p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Photo Upload */}
            <RoleGate allowedRoles={['SUPER_ADMIN', 'FIELD_AGENT']}>
              <section className={styles.uploadSection}>
                <h3 className={styles.sectionHeading}>Upload Photo</h3>
                <div className={styles.uploadForm}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className={styles.fileInput}
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                  <button
                    type="button"
                    className={styles.fileLabel}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <span className={styles.fileLabelText}>
                      <Upload size={14} aria-hidden="true" />
                      {uploadFile ? uploadFile.name : 'Choose photo…'}
                    </span>
                  </button>
                  {uploadFile && (
                    <button
                      type="button"
                      className={styles.clearFile}
                      aria-label="Remove selected file"
                      onClick={() => { setUploadFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                    >
                      <X size={14} />
                    </button>
                  )}
                  <input
                    type="text"
                    placeholder="Caption (optional)"
                    value={uploadCaption}
                    onChange={(e) => setUploadCaption(e.target.value)}
                    className={styles.captionInput}
                    aria-label="Photo caption"
                  />
                  <Button
                    variant="primary"
                    size="compact"
                    disabled={!uploadFile}
                    loading={uploadPhotoMutation.isPending}
                    onClick={() => {
                      if (uploadFile) {
                        uploadPhotoMutation.mutate({
                          visitId: selectedVisit.id,
                          file: uploadFile,
                          caption: uploadCaption,
                        });
                      }
                    }}
                  >
                    Upload
                  </Button>
                </div>
              </section>
            </RoleGate>
          </div>
        )}
      </Drawer>
    </AdminLayout>
  );
}
