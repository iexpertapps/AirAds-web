import { useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useChartColors } from '@/shared/hooks/useChartColors';
import {
  CheckCircle, XCircle, Flag, Lock, ArrowLeft,
  Trash2, Plus, AlertTriangle, Camera, MapPin,
  TrendingUp, Eye, BarChart2,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Button } from '@/shared/components/dls/Button';
import { Badge, QCStatusBadge } from '@/shared/components/dls/Badge';
import { Modal } from '@/shared/components/dls/Modal';
import { Textarea } from '@/shared/components/dls/Textarea';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { Select } from '@/shared/components/dls/Select';
import { RoleGate } from '@/shared/components/RoleGate';
import { useAuthStore } from '@/features/auth/store/authStore';
import { useToast } from '@/shared/hooks/useToast';
import { formatStatus, formatLabel } from '@/shared/utils/formatters';
import styles from './VendorDetailPage.module.css';

type QCStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW' | 'FLAGGED';
type TabId = 'overview' | 'photos' | 'visits' | 'tags' | 'analytics' | 'notes';

interface VendorDetail {
  id: string;
  business_name: string;
  description?: string;
  phone?: string;
  website?: string;
  qc_status: QCStatus;
  qc_notes?: string;
  data_source: string;
  city_name?: string;
  area_name?: string;
  created_at: string;
  updated_at: string;
}

interface VendorDetailResponse {
  success: boolean;
  data: VendorDetail;
}

interface FieldPhoto {
  id: string;
  url: string;
  thumbnail_url?: string;
  uploaded_by_email: string;
  created_at: string;
  is_deleted: boolean;
}

interface FieldVisit {
  id: string;
  agent_email: string;
  visit_date: string;
  gps_confirmed: boolean;
  photos_count: number;
  drift_meters?: number;
  notes?: string;
}

interface VendorTag {
  id: string;
  name: string;
  slug: string;
  tag_type: string;
  display_label: string;
  is_active: boolean;
}

interface AvailableTag {
  id: string;
  name: string;
  tag_type: string;
}

interface VendorAnalytics {
  total_views: number;
  views_last_7d: number;
  views_last_30d: number;
  daily_views: Array<{ date: string; count: number }>;
  top_search_terms: Array<{ term: string; count: number }>;
}

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'overview', label: 'Overview' },
  { id: 'photos', label: 'Field Photos' },
  { id: 'visits', label: 'Visit History' },
  { id: 'tags', label: 'Tags' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'notes', label: 'Internal Notes' },
];

export default function VendorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const chartColors = useChartColors();

  const activeTab = (searchParams.get('tab') ?? 'overview') as TabId;
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [qcNotes, setQcNotes] = useState('');
  const [qcNotesError, setQcNotesError] = useState('');
  const [lightboxPhoto, setLightboxPhoto] = useState<FieldPhoto | null>(null);
  const [deletePhotoTarget, setDeletePhotoTarget] = useState<FieldPhoto | null>(null);
  const [addTagId, setAddTagId] = useState('');
  const [addTagModalOpen, setAddTagModalOpen] = useState(false);
  const [notesText, setNotesText] = useState<string | null>(null);
  const [deleteVendorModalOpen, setDeleteVendorModalOpen] = useState(false);

  const { data: vendor, isLoading } = useQuery({
    queryKey: queryKeys.vendors.detail(id ?? ''),
    queryFn: () =>
      apiClient
        .get<VendorDetailResponse>(`/api/v1/vendors/${id}/`)
        .then((r) => r.data.data),
    enabled: !!id,
  });

  const { data: photos, isLoading: photosLoading } = useQuery({
    queryKey: queryKeys.vendors.photos(id ?? ''),
    queryFn: () =>
      apiClient
        .get<{ data: FieldPhoto[] }>(`/api/v1/vendors/${id}/photos/`)
        .then((r) => r.data.data),
    enabled: !!id && activeTab === 'photos',
  });

  const { data: visits, isLoading: visitsLoading } = useQuery({
    queryKey: queryKeys.vendors.visits(id ?? ''),
    queryFn: () =>
      apiClient
        .get<{ data: FieldVisit[] }>(`/api/v1/vendors/${id}/visits/`)
        .then((r) => r.data.data),
    enabled: !!id && activeTab === 'visits',
  });

  const { data: vendorTags, isLoading: tagsLoading } = useQuery({
    queryKey: queryKeys.vendors.tags(id ?? ''),
    queryFn: () =>
      apiClient
        .get<{ data: VendorTag[] }>(`/api/v1/vendors/${id}/tags/`)
        .then((r) => r.data.data),
    enabled: !!id && activeTab === 'tags',
  });

  const { data: allTags } = useQuery({
    queryKey: queryKeys.tags.list(),
    queryFn: () =>
      apiClient
        .get<{ data: AvailableTag[] }>('/api/v1/tags/')
        .then((r) => r.data.data),
    enabled: !!id && activeTab === 'tags',
  });

  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: queryKeys.vendors.analytics(id ?? ''),
    queryFn: () =>
      apiClient
        .get<{ data: VendorAnalytics }>(`/api/v1/vendors/${id}/analytics/`)
        .then((r) => r.data.data),
    enabled: !!id && activeTab === 'analytics',
  });

  const deletePhotoMutation = useMutation({
    mutationFn: (photoId: string) =>
      apiClient.delete(`/api/v1/vendors/${id}/photos/${photoId}/`),
    onSuccess: () => {
      toast.success('Photo deleted');
      setDeletePhotoTarget(null);
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.photos(id ?? '') });
    },
    onError: () => toast.error('Failed to delete photo'),
  });

  const addTagMutation = useMutation({
    mutationFn: (tagId: string) =>
      apiClient.post(`/api/v1/vendors/${id}/tags/`, { tag_id: tagId }),
    onSuccess: () => {
      toast.success('Tag added');
      setAddTagModalOpen(false);
      setAddTagId('');
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.tags(id ?? '') });
    },
    onError: () => toast.error('Failed to add tag'),
  });

  const removeTagMutation = useMutation({
    mutationFn: (vendorTagId: string) =>
      apiClient.delete(`/api/v1/vendors/${id}/tags/${vendorTagId}/`),
    onSuccess: () => {
      toast.success('Tag removed');
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.tags(id ?? '') });
    },
    onError: () => toast.error('Failed to remove tag'),
  });

  const deleteVendorMutation = useMutation({
    mutationFn: () => apiClient.delete(`/api/v1/vendors/${id}/`),
    onSuccess: () => {
      toast.success('Vendor deleted');
      navigate('/vendors', { replace: true });
    },
    onError: () => toast.error('Failed to delete vendor'),
  });

  const saveNotesMutation = useMutation({
    mutationFn: (notes: string) =>
      apiClient.patch(`/api/v1/vendors/${id}/`, { qc_notes: notes }),
    onSuccess: () => {
      toast.success('Notes saved');
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.detail(id ?? '') });
    },
    onError: () => toast.error('Failed to save notes'),
  });

  const qcMutation = useMutation({
    mutationFn: (payload: { qc_status: QCStatus; qc_notes?: string }) =>
      apiClient.patch(`/api/v1/vendors/${id}/qc-status/`, payload),
    onSuccess: (_, vars) => {
      toast.success(`Vendor ${formatStatus(vars.qc_status).toLowerCase()}`);
      setRejectModalOpen(false);
      setQcNotes('');
      void qc.invalidateQueries({ queryKey: queryKeys.vendors.detail(id ?? '') });
    },
  });

  function handleApprove() {
    qcMutation.mutate({ qc_status: 'APPROVED' });
  }

  function handleFlag() {
    qcMutation.mutate({ qc_status: 'FLAGGED' });
  }

  function handleRejectSubmit() {
    if (!qcNotes.trim()) {
      setQcNotesError('QC notes are required when rejecting a vendor.');
      return;
    }
    setQcNotesError('');
    qcMutation.mutate({ qc_status: 'REJECTED', qc_notes: qcNotes });
  }

  function setTab(tab: TabId) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', tab);
      return next;
    });
  }

  const visibleTabs = TABS.filter((t) => {
    if (t.id === 'notes') {
      return user?.role === 'SUPER_ADMIN' || user?.role === 'QA_REVIEWER';
    }
    return true;
  });

  if (isLoading) {
    return (
      <AdminLayout title="Vendor Detail">
        <SkeletonTable rows={8} columns={3} />
      </AdminLayout>
    );
  }

  if (!vendor) {
    return (
      <AdminLayout title="Vendor Not Found">
        <p className={styles.notFound}>Vendor not found.</p>
        <Button variant="secondary" leftIcon={<ArrowLeft size={16} />} onClick={() => navigate('/vendors')}>
          Back to Vendors
        </Button>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout title={vendor.business_name}>
      <PageHeader
        heading={vendor.business_name}
        breadcrumbs={[
          { label: 'Vendors', href: '/vendors' },
          { label: vendor.business_name },
        ]}
        actions={
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER']}>
            <div className={styles.qcActions}>
              <QCStatusBadge status={vendor.qc_status} />
              {vendor.qc_status !== 'APPROVED' && (
                <Button
                  variant="secondary"
                  size="compact"
                  leftIcon={<CheckCircle size={14} />}
                  loading={qcMutation.isPending}
                  onClick={handleApprove}
                >
                  Approve
                </Button>
              )}
              <Button
                variant="secondary"
                size="compact"
                leftIcon={<XCircle size={14} />}
                onClick={() => setRejectModalOpen(true)}
              >
                Reject
              </Button>
              <Button
                variant="secondary"
                size="compact"
                leftIcon={<Flag size={14} />}
                loading={qcMutation.isPending}
                onClick={handleFlag}
              >
                Flag
              </Button>
              <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
                <Button
                  variant="destructive"
                  size="compact"
                  leftIcon={<Trash2 size={14} />}
                  onClick={() => setDeleteVendorModalOpen(true)}
                >
                  Delete
                </Button>
              </RoleGate>
            </div>
          </RoleGate>
        }
      />

      {/* Tab Navigation */}
      <nav className={styles.tabs} aria-label="Vendor detail tabs">
        <div role="tablist" className={styles.tabList}>
          {visibleTabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              className={[styles.tab, activeTab === tab.id ? styles.tabActive : ''].join(' ')}
              onClick={() => setTab(tab.id)}
            >
              {tab.id === 'notes' && <Lock size={12} aria-hidden="true" />}
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Tab Panels */}
      <div
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className={styles.tabPanel}
      >
        {activeTab === 'overview' && (
          <div className={styles.overviewGrid}>
            <div className={styles.infoCard}>
              <h2 className={styles.cardHeading}>Business Information</h2>
              <dl className={styles.dl}>
                <dt>Business Name</dt>
                <dd>{vendor.business_name}</dd>
                {vendor.description && (
                  <>
                    <dt>Description</dt>
                    <dd>{vendor.description}</dd>
                  </>
                )}
                {vendor.phone && (
                  <>
                    <dt>Phone</dt>
                    <dd>{vendor.phone}</dd>
                  </>
                )}
                {vendor.website && (
                  <>
                    <dt>Website</dt>
                    <dd>
                      <a href={vendor.website} target="_blank" rel="noopener noreferrer" className={styles.link}>
                        {vendor.website}
                      </a>
                    </dd>
                  </>
                )}
                <dt>Location</dt>
                <dd>{[vendor.city_name, vendor.area_name].filter(Boolean).join(' › ') || '—'}</dd>
                <dt>Data Source</dt>
                <dd>{formatLabel(vendor.data_source)}</dd>
                <dt>Created</dt>
                <dd>{new Date(vendor.created_at).toLocaleString()}</dd>
              </dl>
            </div>
          </div>
        )}

        {activeTab === 'photos' && (
          <div className={styles.tabSection}>
            {photosLoading ? (
              <SkeletonTable rows={2} columns={4} showHeader={false} />
            ) : !photos || photos.length === 0 ? (
              <EmptyState
                heading="No field photos"
                subheading="Photos uploaded during field visits will appear here."
                illustration={<Camera size={40} strokeWidth={1} />}
              />
            ) : (
              <>
                <div className={styles.photoGrid}>
                  {photos.filter((p) => !p.is_deleted).map((photo) => (
                    <div key={photo.id} className={styles.photoCard}>
                      <button
                        className={styles.photoThumb}
                        onClick={() => setLightboxPhoto(photo)}
                        aria-label={`View photo uploaded by ${photo.uploaded_by_email}`}
                      >
                        <img
                          src={photo.thumbnail_url ?? photo.url}
                          alt={`Field photo by ${photo.uploaded_by_email}`}
                          className={styles.photoImg}
                          loading="lazy"
                        />
                      </button>
                      <div className={styles.photoMeta}>
                        <span className={styles.photoAgent}>{photo.uploaded_by_email}</span>
                        <span className={styles.photoDate}>
                          {new Date(photo.created_at).toLocaleDateString()}
                        </span>
                        <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER']}>
                          <Button
                            variant="ghost"
                            size="compact"
                            aria-label="Delete photo"
                            onClick={() => setDeletePhotoTarget(photo)}
                          >
                            <Trash2 size={12} strokeWidth={1.5} />
                          </Button>
                        </RoleGate>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'visits' && (
          <div className={styles.tabSection}>
            {visitsLoading ? (
              <SkeletonTable rows={4} columns={5} />
            ) : !visits || visits.length === 0 ? (
              <EmptyState
                heading="No visits recorded"
                subheading="Field agent visits for this vendor will appear here."
                illustration={<MapPin size={40} strokeWidth={1} />}
              />
            ) : (
              <div className={styles.timeline}>
                {visits.map((visit) => {
                  const hasDrift = visit.drift_meters !== undefined && visit.drift_meters > 20;
                  return (
                    <div key={visit.id} className={styles.timelineItem}>
                      <div className={styles.timelineDot} aria-hidden="true" />
                      <div className={styles.timelineCard}>
                        <div className={styles.timelineHeader}>
                          <span className={styles.timelineDate}>
                            {new Date(visit.visit_date).toLocaleString()}
                          </span>
                          <div className={styles.timelineBadges}>
                            <Badge
                              variant={visit.gps_confirmed ? 'success' : 'neutral'}
                              label={visit.gps_confirmed ? 'GPS Confirmed' : 'GPS Pending'}
                            />
                            {hasDrift && (
                              <Badge
                                variant="warning"
                                label={`${visit.drift_meters!.toFixed(0)}m drift`}
                                icon={<AlertTriangle size={12} strokeWidth={1.5} />}
                              />
                            )}
                          </div>
                        </div>
                        <dl className={styles.visitDl}>
                          <dt>Agent</dt>
                          <dd>{visit.agent_email}</dd>
                          <dt>Photos</dt>
                          <dd>{visit.photos_count}</dd>
                          {visit.notes && (
                            <>
                              <dt>Notes</dt>
                              <dd>{visit.notes}</dd>
                            </>
                          )}
                        </dl>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === 'tags' && (
          <div className={styles.tabSection}>
            <div className={styles.tabSectionHeader}>
              <h2 className={styles.cardHeading}>Assigned Tags</h2>
              <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER']}>
                <Button
                  variant="primary"
                  size="compact"
                  leftIcon={<Plus size={14} strokeWidth={1.5} />}
                  onClick={() => setAddTagModalOpen(true)}
                >
                  Add Tag
                </Button>
              </RoleGate>
            </div>
            {tagsLoading ? (
              <SkeletonTable rows={3} columns={4} />
            ) : !vendorTags || vendorTags.length === 0 ? (
              <EmptyState
                heading="No tags assigned"
                subheading="Add tags to help classify this vendor."
                ctaLabel="Add Tag"
                onCta={() => setAddTagModalOpen(true)}
              />
            ) : (
              <div className={styles.tagsList}>
                {vendorTags.map((vt) => (
                  <div key={vt.id} className={styles.tagRow}>
                    <Badge variant="info" label={vt.display_label || vt.name} />
                    <span className={styles.tagType}>{formatLabel(vt.tag_type)}</span>
                    <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER']}>
                      <Button
                        variant="ghost"
                        size="compact"
                        aria-label={`Remove tag ${vt.name}`}
                        loading={removeTagMutation.isPending && removeTagMutation.variables === vt.id}
                        onClick={() => removeTagMutation.mutate(vt.id)}
                      >
                        <Trash2 size={12} strokeWidth={1.5} />
                      </Button>
                    </RoleGate>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className={styles.tabSection}>
            {analyticsLoading ? (
              <SkeletonTable rows={3} columns={3} showHeader={false} />
            ) : !analytics ? (
              <EmptyState
                heading="No analytics data"
                subheading="Analytics will appear once this vendor starts receiving views."
                illustration={<BarChart2 size={40} strokeWidth={1} />}
              />
            ) : (
              <>
                <div className={styles.analyticsMetrics}>
                  <div className={styles.analyticsCard}>
                    <Eye size={20} strokeWidth={1.5} className={styles.analyticsIcon} aria-hidden="true" />
                    <p className={styles.analyticsValue}>{(analytics.total_views ?? 0).toLocaleString()}</p>
                    <p className={styles.analyticsLabel}>Total Views</p>
                  </div>
                  <div className={styles.analyticsCard}>
                    <TrendingUp size={20} strokeWidth={1.5} className={styles.analyticsIcon} aria-hidden="true" />
                    <p className={styles.analyticsValue}>{(analytics.views_last_7d ?? 0).toLocaleString()}</p>
                    <p className={styles.analyticsLabel}>Last 7 Days</p>
                  </div>
                  <div className={styles.analyticsCard}>
                    <BarChart2 size={20} strokeWidth={1.5} className={styles.analyticsIcon} aria-hidden="true" />
                    <p className={styles.analyticsValue}>{(analytics.views_last_30d ?? 0).toLocaleString()}</p>
                    <p className={styles.analyticsLabel}>Last 30 Days</p>
                  </div>
                </div>

                {(analytics.daily_views?.length ?? 0) > 0 && (
                  <div className={styles.analyticsChart}>
                    <h3 className={styles.cardHeading}>Daily Views — Last 14 Days</h3>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={analytics.daily_views} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={chartColors.gridStroke} />
                        <XAxis dataKey="date" tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: chartColors.tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
                        <Tooltip contentStyle={{ background: chartColors.tooltipBg, border: `1px solid ${chartColors.tooltipBorder}`, borderRadius: '8px', fontSize: 12, color: chartColors.tickFill }} />
                        <Bar dataKey="count" fill={chartColors.barTeal} radius={[3, 3, 0, 0]} name="Views" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {(analytics.top_search_terms?.length ?? 0) > 0 && (
                  <div className={styles.analyticsChart}>
                    <h3 className={styles.cardHeading}>Top Search Terms</h3>
                    <ol className={styles.searchTermsList}>
                      {(analytics.top_search_terms ?? []).slice(0, 10).map((t, i) => (
                        <li key={t.term} className={styles.searchTermRow}>
                          <span className={styles.searchTermRank}>{i + 1}</span>
                          <span className={styles.searchTermText}>{t.term}</span>
                          <span className={styles.searchTermCount}>{(t.count ?? 0).toLocaleString()}</span>
                          <div
                            className={styles.searchTermBar}
                            style={{ ['--search-term-bar-width' as string]: `${(t.count / ((analytics.top_search_terms ?? [])[0]?.count || 1)) * 100}%` } as React.CSSProperties}
                            aria-hidden="true"
                          />
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'notes' && (
          <RoleGate allowedRoles={['SUPER_ADMIN', 'QA_REVIEWER']}>
            <div className={styles.notesPanel}>
              <h2 className={styles.cardHeading}>Internal QC Notes</h2>
              <p className={styles.notesHint}>These notes are only visible to Super Admins and QA Reviewers.</p>
              <Textarea
                id="qc-notes-edit"
                label="QC Notes"
                value={notesText ?? (vendor.qc_notes ?? '')}
                onChange={(e) => setNotesText(e.target.value)}
                rows={6}
              />
              <div className={styles.notesActions}>
                <Button
                  variant="primary"
                  size="compact"
                  loading={saveNotesMutation.isPending}
                  onClick={() => saveNotesMutation.mutate(notesText ?? (vendor.qc_notes ?? ''))}
                >
                  Save Notes
                </Button>
              </div>
            </div>
          </RoleGate>
        )}
      </div>

      {/* Lightbox Modal */}
      <Modal
        isOpen={lightboxPhoto !== null}
        onClose={() => setLightboxPhoto(null)}
        title="Field Photo"
        footer={<Button variant="secondary" onClick={() => setLightboxPhoto(null)}>Close</Button>}
      >
        {lightboxPhoto && (
          <img
            src={lightboxPhoto.url}
            alt={`Field photo by ${lightboxPhoto.uploaded_by_email}`}
            className={styles.lightboxImg}
          />
        )}
      </Modal>

      {/* Delete Photo Confirmation */}
      <Modal
        isOpen={deletePhotoTarget !== null}
        onClose={() => setDeletePhotoTarget(null)}
        title="Delete Photo"
        description="Are you sure you want to soft-delete this photo?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeletePhotoTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={deletePhotoMutation.isPending}
              onClick={() => deletePhotoTarget && deletePhotoMutation.mutate(deletePhotoTarget.id)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>This will soft-delete the photo. It can be recovered by an admin.</p>
      </Modal>

      {/* Add Tag Modal */}
      <Modal
        isOpen={addTagModalOpen}
        onClose={() => { setAddTagModalOpen(false); setAddTagId(''); }}
        title="Add Tag"
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddTagModalOpen(false)}>Cancel</Button>
            <Button
              variant="primary"
              loading={addTagMutation.isPending}
              disabled={!addTagId}
              onClick={() => addTagId && addTagMutation.mutate(addTagId)}
            >
              Add Tag
            </Button>
          </>
        }
      >
        <Select
          id="add-tag-select"
          label="Select tag"
          required
          options={(allTags ?? []).map((t) => ({ value: t.id, label: `${t.name} (${formatLabel(t.tag_type)})` }))}
          placeholder="Choose a tag…"
          value={addTagId}
          onChange={(e) => setAddTagId(e.target.value)}
        />
      </Modal>

      {/* Delete Vendor Modal */}
      <Modal
        isOpen={deleteVendorModalOpen}
        onClose={() => setDeleteVendorModalOpen(false)}
        title="Delete Vendor"
        description={`Are you sure you want to delete "${vendor.business_name}"? This action cannot be undone.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteVendorModalOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={deleteVendorMutation.isPending}
              onClick={() => deleteVendorMutation.mutate()}
            >
              Delete Vendor
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>The vendor will be soft-deleted and removed from all public listings.</p>
      </Modal>

      {/* Reject Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => { setRejectModalOpen(false); setQcNotes(''); setQcNotesError(''); }}
        title="Reject Vendor"
        description="Provide QC notes explaining the reason for rejection."
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectModalOpen(false)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={qcMutation.isPending}
              onClick={handleRejectSubmit}
            >
              Reject Vendor
            </Button>
          </>
        }
      >
        <Textarea
          id="reject-qc-notes"
          label="QC Notes"
          required
          rows={4}
          value={qcNotes}
          onChange={(e) => setQcNotes(e.target.value)}
          error={qcNotesError}
          placeholder="Explain why this vendor is being rejected…"
        />
      </Modal>
    </AdminLayout>
  );
}
