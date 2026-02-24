import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Lock, Trash2, Pencil } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { FiltersBar } from '@/shared/components/dls/FiltersBar';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { Badge } from '@/shared/components/dls/Badge';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { Toggle } from '@/shared/components/dls/Toggle';
import { Drawer } from '@/shared/components/dls/Drawer';
import { Modal } from '@/shared/components/dls/Modal';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { RoleGate } from '@/shared/components/RoleGate';
import { useToast } from '@/shared/hooks/useToast';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { formatLabel } from '@/shared/utils/formatters';
import styles from './TagsPage.module.css';

type TagType = 'LOCATION' | 'CATEGORY' | 'INTENT' | 'PROMOTION' | 'TIME' | 'SYSTEM';

interface Tag {
  id: string;
  name: string;
  slug: string;
  tag_type: TagType;
  display_order: number;
  is_active: boolean;
  usage_count: number;
}

const TAG_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'LOCATION', label: 'Location' },
  { value: 'CATEGORY', label: 'Category' },
  { value: 'INTENT', label: 'Intent' },
  { value: 'PROMOTION', label: 'Promotion' },
  { value: 'TIME', label: 'Time' },
];

const TAG_TYPE_VARIANT: Record<TagType, 'info' | 'success' | 'warning' | 'neutral'> = {
  LOCATION: 'info',
  CATEGORY: 'info',
  INTENT: 'success',
  PROMOTION: 'warning',
  TIME: 'neutral',
  SYSTEM: 'neutral',
};

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  tag_type: z.enum(['LOCATION', 'CATEGORY', 'INTENT', 'PROMOTION', 'TIME']),
  display_order: z.coerce.number().int().min(0),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export default function TagsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editTag, setEditTag] = useState<Tag | null>(null);
  const [deleteTag, setDeleteTag] = useState<Tag | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkAction, setBulkAction] = useState<'activate' | 'deactivate' | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  const { data: tags, isLoading } = useQuery({
    queryKey: queryKeys.tags.list({ search: debouncedSearch }),
    queryFn: () =>
      apiClient
        .get<{ data: Tag[] }>('/api/v1/tags/', { params: { search: debouncedSearch || undefined } })
        .then((r) => r.data.data),
  });

  const { register, handleSubmit, reset, setValue, control, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { is_active: true, display_order: 0 },
  });

  const isActiveValue = useWatch({ control, name: 'is_active' });

  function openCreate() {
    setEditTag(null);
    reset({ name: '', tag_type: 'LOCATION', display_order: 0, is_active: true });
    setDrawerOpen(true);
  }

  function openEdit(tag: Tag) {
    if (tag.tag_type === 'SYSTEM') return;
    setEditTag(tag);
    reset({ name: tag.name, tag_type: tag.tag_type as FormValues['tag_type'], display_order: tag.display_order, is_active: tag.is_active });
    setDrawerOpen(true);
  }

  const createMutation = useMutation({
    mutationFn: (d: FormValues) => apiClient.post('/api/v1/tags/', d),
    onSuccess: () => {
      toast.success('Tag created');
      setDrawerOpen(false);
      void qc.invalidateQueries({ queryKey: queryKeys.tags.list() });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...d }: FormValues & { id: string }) => apiClient.patch(`/api/v1/tags/${id}/`, d),
    onSuccess: () => {
      toast.success('Tag updated');
      setDrawerOpen(false);
      void qc.invalidateQueries({ queryKey: queryKeys.tags.list() });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/v1/tags/${id}/`),
    onSuccess: () => {
      toast.success('Tag deleted');
      setDeleteTag(null);
      void qc.invalidateQueries({ queryKey: queryKeys.tags.list() });
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      apiClient.patch(`/api/v1/tags/${id}/`, { is_active }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: queryKeys.tags.list() }),
  });

  async function handleBulkToggle(activate: boolean) {
    setBulkLoading(true);
    setBulkAction(null);
    let count = 0;
    for (const id of selectedIds) {
      try {
        await apiClient.patch(`/api/v1/tags/${id}/`, { is_active: activate });
        count++;
      } catch { /* continue */ }
    }
    toast.success(`${count} tag(s) ${activate ? 'activated' : 'deactivated'}`);
    setSelectedIds([]);
    setBulkLoading(false);
    void qc.invalidateQueries({ queryKey: queryKeys.tags.list() });
  }

  function onSubmit(values: FormValues) {
    if (editTag) {
      updateMutation.mutate({ ...values, id: editTag.id });
    } else {
      createMutation.mutate(values);
    }
  }

  const userTags = (tags ?? []).filter((t) => t.tag_type !== 'SYSTEM');
  const systemTags = (tags ?? []).filter((t) => t.tag_type === 'SYSTEM');

  const columns: ColumnDef<Tag>[] = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (t) => <span className={styles.tagName}>{t.name}</span>,
    },
    {
      key: 'slug',
      header: 'Slug',
      render: (t) => <code className={styles.slug}>{t.slug}</code>,
    },
    {
      key: 'tag_type',
      header: 'Type',
      render: (t) => (
        <Badge
          variant={TAG_TYPE_VARIANT[t.tag_type]}
          label={formatLabel(t.tag_type)}
          icon={t.tag_type === 'SYSTEM' ? <Lock size={10} /> : undefined}
        />
      ),
    },
    {
      key: 'display_order',
      header: 'Order',
      sortable: true,
      render: (t) => <span>{t.display_order}</span>,
    },
    {
      key: 'is_active',
      header: 'Active',
      render: (t) => (
        t.tag_type === 'SYSTEM' ? (
          <span className={styles.systemLock}><Lock size={14} /></span>
        ) : (
          <Toggle
            id={`toggle-${t.id}`}
            label=""
            checked={t.is_active}
            onChange={(checked) => toggleActiveMutation.mutate({ id: t.id, is_active: checked })}
          />
        )
      ),
    },
    {
      key: 'usage_count',
      header: 'Usage',
      sortable: true,
      render: (t) => <span>{t.usage_count.toLocaleString()}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (t) =>
        t.tag_type === 'SYSTEM' ? (
          <span className={styles.systemLock} aria-label="System tag — read only"><Lock size={14} /></span>
        ) : (
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY']}>
            <div className={styles.actions}>
              <Button variant="ghost" size="compact" aria-label={`Edit ${t.name}`} onClick={() => openEdit(t)}>
                <Pencil size={14} />
              </Button>
              <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER']}>
                <Button variant="ghost" size="compact" aria-label={`Delete ${t.name}`} onClick={() => setDeleteTag(t)}>
                  <Trash2 size={14} />
                </Button>
              </RoleGate>
            </div>
          </RoleGate>
        ),
    },
  ];

  return (
    <AdminLayout title="Tag Management">
      <PageHeader
        heading="Tag Management"
        subheading="Manage vendor classification tags"
        actions={
          <RoleGate allowedRoles={['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY']}>
            <div className={styles.headerActions}>
              {selectedIds.length > 0 && (
                <>
                  <Button
                    variant="secondary"
                    size="compact"
                    loading={bulkLoading}
                    onClick={() => setBulkAction('activate')}
                  >
                    Activate {selectedIds.length}
                  </Button>
                  <Button
                    variant="secondary"
                    size="compact"
                    loading={bulkLoading}
                    onClick={() => setBulkAction('deactivate')}
                  >
                    Deactivate {selectedIds.length}
                  </Button>
                </>
              )}
              <Button variant="primary" leftIcon={<Plus size={16} />} onClick={openCreate}>
                Add Tag
              </Button>
            </div>
          </RoleGate>
        }
      />

      <FiltersBar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search tags…"
      />

      <Table
        aria-label="Tags table"
        columns={columns}
        data={userTags}
        isLoading={isLoading}
        isEmpty={!isLoading && userTags.length === 0}
        emptyState={
          <EmptyState
            heading="No tags found"
            subheading="Create your first tag to classify vendors."
            ctaLabel="Add Tag"
            onCta={openCreate}
          />
        }
        selectable
        selectedIds={selectedIds}
        onSelectionChange={setSelectedIds}
      />

      {systemTags.length > 0 && (
        <section className={styles.systemSection} aria-label="System tags (read-only)">
          <h2 className={styles.systemHeading}>
            <Lock size={14} aria-hidden="true" /> System Tags (read-only)
          </h2>
          <Table
            aria-label="System tags table"
            columns={columns}
            data={systemTags}
            isLoading={false}
            isEmpty={systemTags.length === 0}
            emptyState={<></>}
          />
        </section>
      )}

      {/* Create / Edit Drawer */}
      <Drawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editTag ? 'Edit Tag' : 'Create Tag'}
        footer={
          <Button
            variant="primary"
            loading={createMutation.isPending || updateMutation.isPending}
            onClick={handleSubmit(onSubmit)}
          >
            {editTag ? 'Save Changes' : 'Create Tag'}
          </Button>
        }
      >
        <form className={styles.drawerForm} onSubmit={handleSubmit(onSubmit)}>
          <Input id="tag-name" label="Tag name" required error={errors.name?.message} {...register('name')} />
          {editTag && (
            <div className={styles.slugRow}>
              <span className={styles.slugLabel}>Slug</span>
              <code className={styles.slug}>{editTag.slug}</code>
              <span className={styles.slugHint}>(read-only after creation)</span>
            </div>
          )}
          <Select
            id="tag-type"
            label="Tag type"
            required
            options={TAG_TYPE_OPTIONS}
            placeholder="Select type…"
            error={errors.tag_type?.message}
            {...register('tag_type')}
          />
          <Input id="tag-order" label="Display order" type="number" min={0} error={errors.display_order?.message} {...register('display_order')} />
          <Toggle
            id="tag-active"
            label="Active"
            checked={isActiveValue}
            onChange={(v) => setValue('is_active', v)}
          />
        </form>
      </Drawer>

      {/* Bulk Action Confirmation */}
      <Modal
        isOpen={bulkAction !== null}
        onClose={() => setBulkAction(null)}
        title={bulkAction === 'activate' ? 'Bulk Activate' : 'Bulk Deactivate'}
        description={`${bulkAction === 'activate' ? 'Activate' : 'Deactivate'} ${selectedIds.length} tag(s)?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setBulkAction(null)}>Cancel</Button>
            <Button
              variant="primary"
              loading={bulkLoading}
              onClick={() => bulkAction && void handleBulkToggle(bulkAction === 'activate')}
            >
              Confirm
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>
          This will {bulkAction === 'activate' ? 'activate' : 'deactivate'} {selectedIds.length} selected tag(s).
        </p>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteTag !== null}
        onClose={() => setDeleteTag(null)}
        title="Delete Tag"
        description={`Are you sure you want to delete "${deleteTag?.name}"? This cannot be undone.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteTag(null)}>Cancel</Button>
            <Button
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => deleteTag && deleteMutation.mutate(deleteTag.id)}
            >
              Delete
            </Button>
          </>
        }
      >
        <p className={styles.deleteWarning}>
          This tag has been used on <strong>{deleteTag?.usage_count ?? 0}</strong> vendor(s).
          Removing it will unlink it from all associated vendors.
        </p>
      </Modal>
    </AdminLayout>
  );
}
