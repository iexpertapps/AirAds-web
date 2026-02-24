import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Copy, Check, Unlock } from 'lucide-react';
import { apiClient } from '@/lib/axios';
import { queryKeys } from '@/queryKeys';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Table } from '@/shared/components/dls/Table';
import type { ColumnDef } from '@/shared/components/dls/Table';
import { RoleBadge } from '@/shared/components/dls/Badge';
import { Button } from '@/shared/components/dls/Button';
import { Input } from '@/shared/components/dls/Input';
import { Select } from '@/shared/components/dls/Select';
import { Toggle } from '@/shared/components/dls/Toggle';
import { Drawer } from '@/shared/components/dls/Drawer';
import { Modal } from '@/shared/components/dls/Modal';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useToast } from '@/shared/hooks/useToast';
import { formatActiveStatus } from '@/shared/utils/formatters';
import styles from './UsersPage.module.css';

type Role = 'SUPER_ADMIN' | 'CITY_MANAGER' | 'DATA_ENTRY' | 'QA_REVIEWER' | 'FIELD_AGENT' | 'ANALYST' | 'SUPPORT';

interface SystemUser {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  last_login?: string;
  failed_attempts: number;
  is_active: boolean;
  is_locked: boolean;
  locked_until?: string;
}

interface UserListResponse {
  data: SystemUser[];
}

interface CreateUserResponse {
  data: { id: string; role: Role; temp_password: string };
}

const ROLE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'SUPER_ADMIN', label: 'Super Admin' },
  { value: 'CITY_MANAGER', label: 'City Manager' },
  { value: 'DATA_ENTRY', label: 'Data Entry' },
  { value: 'QA_REVIEWER', label: 'QA Reviewer' },
  { value: 'FIELD_AGENT', label: 'Field Agent' },
  { value: 'ANALYST', label: 'Analyst' },
  { value: 'SUPPORT', label: 'Support' },
];

const createSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  email: z.string().min(1, 'Email is required').email('Enter a valid email'),
  role: z.enum(['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER', 'FIELD_AGENT', 'ANALYST', 'SUPPORT']),
});

const editSchema = z.object({
  full_name: z.string().min(1, 'Full name is required'),
  role: z.enum(['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER', 'FIELD_AGENT', 'ANALYST', 'SUPPORT']),
  is_active: z.boolean(),
});

type CreateForm = z.infer<typeof createSchema>;
type EditForm = z.infer<typeof editSchema>;

export default function UsersPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [editUser, setEditUser] = useState<SystemUser | null>(null);
  const [unlockUser, setUnlockUser] = useState<SystemUser | null>(null);
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: queryKeys.system.users(),
    queryFn: () =>
      apiClient.get<UserListResponse>('/api/v1/auth/users/').then((r) => r.data.data),
  });

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema) });
  const editForm = useForm<EditForm>({ resolver: zodResolver(editSchema) });

  const createMutation = useMutation({
    mutationFn: (d: CreateForm) =>
      apiClient.post<CreateUserResponse>('/api/v1/auth/users/', d).then((r) => r.data),
    onSuccess: (resp) => {
      setCreatedPassword(resp.data.temp_password);
      setCreateDrawerOpen(false);
      createForm.reset();
      void qc.invalidateQueries({ queryKey: queryKeys.system.users() });
    },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, ...d }: EditForm & { id: string }) =>
      apiClient.patch(`/api/v1/auth/users/${id}/`, d),
    onSuccess: () => {
      toast.success('User updated');
      setEditUser(null);
      void qc.invalidateQueries({ queryKey: queryKeys.system.users() });
    },
  });

  const unlockMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient.patch(`/api/v1/auth/users/${id}/`, { is_locked: false, failed_attempts: 0 }),
    onSuccess: () => {
      toast.success('Account unlocked');
      setUnlockUser(null);
      void qc.invalidateQueries({ queryKey: queryKeys.system.users() });
    },
  });

  function openEdit(user: SystemUser) {
    setEditUser(user);
    editForm.reset({ full_name: user.full_name, role: user.role, is_active: user.is_active });
  }

  function handleCopyPassword() {
    if (!createdPassword) return;
    void navigator.clipboard.writeText(createdPassword).then(() => {
      setCopied(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopied(false), 2000);
    });
  }

  const isActiveValue = useWatch({ control: editForm.control, name: 'is_active' });

  const columns: ColumnDef<SystemUser>[] = [
    {
      key: 'full_name',
      header: 'Full Name',
      render: (u) => <span className={styles.name}>{u.full_name}</span>,
    },
    {
      key: 'email',
      header: 'Email',
      render: (u) => <span className={styles.email}>{u.email}</span>,
    },
    {
      key: 'role',
      header: 'Role',
      render: (u) => <RoleBadge role={u.role} />,
    },
    {
      key: 'last_login',
      header: 'Last Login',
      render: (u) => (
        <span className={styles.date}>
          {u.last_login ? new Date(u.last_login).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'failed_attempts',
      header: 'Failed Attempts',
      render: (u) => (
        <span className={u.failed_attempts > 0 ? styles.failedAttempts : ''}>
          {u.failed_attempts}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (u) => {
        if (u.is_locked) {
          const lockedUntil = u.locked_until ? new Date(u.locked_until).toLocaleTimeString() : '';
          return (
            <span className={styles.locked}>
              Locked{lockedUntil ? ` until ${lockedUntil}` : ''}
            </span>
          );
        }
        return (
          <span className={u.is_active ? styles.active : styles.inactive}>
            {formatActiveStatus(u.is_active)}
          </span>
        );
      },
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <div className={styles.actions}>
          <Button variant="ghost" size="compact" onClick={() => openEdit(u)} aria-label={`Edit ${u.full_name}`}>
            Edit
          </Button>
          {u.is_locked && (
            <Button
              variant="secondary"
              size="compact"
              leftIcon={<Unlock size={14} />}
              onClick={() => setUnlockUser(u)}
              aria-label={`Unlock ${u.email}`}
            >
              Unlock
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <AdminLayout title="User Management">
      <PageHeader
        heading="User Management"
        subheading="Manage internal portal users and roles"
        actions={
          <Button variant="primary" leftIcon={<Plus size={16} />} onClick={() => setCreateDrawerOpen(true)}>
            Add User
          </Button>
        }
      />

      <Table
        aria-label="Users table"
        columns={columns}
        data={users ?? []}
        isLoading={isLoading}
        isEmpty={!isLoading && (users ?? []).length === 0}
        emptyState={
          <EmptyState
            heading="No users found"
            subheading="Add the first user to get started."
            ctaLabel="Add User"
            onCta={() => setCreateDrawerOpen(true)}
          />
        }
      />

      {/* Create User Drawer */}
      <Drawer
        isOpen={createDrawerOpen}
        onClose={() => setCreateDrawerOpen(false)}
        title="Add User"
        footer={
          <Button
            variant="primary"
            loading={createMutation.isPending}
            onClick={createForm.handleSubmit((d) => createMutation.mutate(d))}
          >
            Create User
          </Button>
        }
      >
        <form
          className={styles.drawerForm}
          onSubmit={createForm.handleSubmit((d) => createMutation.mutate(d))}
        >
          <Input
            id="user-name"
            label="Full name"
            required
            error={createForm.formState.errors.full_name?.message}
            {...createForm.register('full_name')}
          />
          <Input
            id="user-email"
            label="Email address"
            type="email"
            required
            error={createForm.formState.errors.email?.message}
            {...createForm.register('email')}
          />
          <Select
            id="user-role"
            label="Role"
            required
            options={ROLE_OPTIONS}
            placeholder="Select role…"
            error={createForm.formState.errors.role?.message}
            {...createForm.register('role')}
          />
        </form>
      </Drawer>

      {/* Edit User Drawer */}
      <Drawer
        isOpen={editUser !== null}
        onClose={() => setEditUser(null)}
        title="Edit User"
        footer={
          <Button
            variant="primary"
            loading={editMutation.isPending}
            onClick={editForm.handleSubmit((d) => editUser && editMutation.mutate({ ...d, id: editUser.id }))}
          >
            Save Changes
          </Button>
        }
      >
        {editUser && (
          <form
            className={styles.drawerForm}
            onSubmit={editForm.handleSubmit((d) => editMutation.mutate({ ...d, id: editUser.id }))}
          >
            <Input
              id="edit-user-name"
              label="Full name"
              required
              error={editForm.formState.errors.full_name?.message}
              {...editForm.register('full_name')}
            />
            <div className={styles.readOnlyField}>
              <span className={styles.readOnlyLabel}>Email (read-only)</span>
              <span className={styles.readOnlyValue}>{editUser.email}</span>
            </div>
            <Select
              id="edit-user-role"
              label="Role"
              required
              options={ROLE_OPTIONS}
              error={editForm.formState.errors.role?.message}
              {...editForm.register('role')}
            />
            <Toggle
              id="edit-user-active"
              label="Active"
              checked={isActiveValue}
              onChange={(v) => editForm.setValue('is_active', v)}
            />
          </form>
        )}
      </Drawer>

      {/* Created Password Modal */}
      <Modal
        isOpen={createdPassword !== null}
        onClose={() => setCreatedPassword(null)}
        title="User Created"
        description="Save this temporary password — it will not be shown again."
        footer={
          <Button variant="primary" onClick={() => setCreatedPassword(null)}>
            Done
          </Button>
        }
      >
        <div className={styles.passwordBox}>
          <code className={styles.tempPassword}>{createdPassword}</code>
          <Button
            variant="secondary"
            size="compact"
            leftIcon={copied ? <Check size={14} /> : <Copy size={14} />}
            onClick={handleCopyPassword}
            aria-label="Copy password to clipboard"
            aria-live="polite"
          >
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      </Modal>

      {/* Unlock Confirmation Modal */}
      <Modal
        isOpen={unlockUser !== null}
        onClose={() => setUnlockUser(null)}
        title="Unlock Account"
        description={`Are you sure you want to unlock ${unlockUser?.email ?? ''}?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setUnlockUser(null)}>Cancel</Button>
            <Button
              variant="primary"
              loading={unlockMutation.isPending}
              onClick={() => unlockUser && unlockMutation.mutate(unlockUser.id)}
            >
              Unlock Account
            </Button>
          </>
        }
      >
        <p className={styles.unlockNote}>
          This will reset the failed login counter and allow the user to sign in immediately.
        </p>
      </Modal>
    </AdminLayout>
  );
}
