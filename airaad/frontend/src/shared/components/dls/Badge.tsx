import { CheckCircle, XCircle, AlertTriangle, Flag, Clock, Loader, Info } from 'lucide-react';
import { formatStatus, formatRole } from '@/shared/utils/formatters';
import styles from './Badge.module.css';

interface BadgeProps {
  variant: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  label: string;
  icon?: React.ReactNode;
  size?: 'sm' | 'md';
}

export function Badge({ variant, label, icon, size = 'md' }: BadgeProps) {
  return (
    <span
      className={[styles.badge, styles[variant], styles[size]].join(' ')}
      aria-label={`Status: ${label}`}
    >
      {icon && (
        <span className={styles.icon} aria-hidden="true">
          {icon}
        </span>
      )}
      {label}
    </span>
  );
}

type QCStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'NEEDS_REVIEW' | 'FLAGGED';

export function QCStatusBadge({ status }: { status: QCStatus }) {
  const map: Record<QCStatus, { variant: BadgeProps['variant']; icon: React.ReactNode; label: string }> = {
    PENDING: { variant: 'neutral', icon: <Clock size={12} strokeWidth={1.5} />, label: formatStatus('PENDING') },
    APPROVED: { variant: 'success', icon: <CheckCircle size={12} strokeWidth={1.5} />, label: formatStatus('APPROVED') },
    REJECTED: { variant: 'error', icon: <XCircle size={12} strokeWidth={1.5} />, label: formatStatus('REJECTED') },
    NEEDS_REVIEW: { variant: 'warning', icon: <AlertTriangle size={12} strokeWidth={1.5} />, label: formatStatus('NEEDS_REVIEW') },
    FLAGGED: { variant: 'error', icon: <Flag size={12} strokeWidth={1.5} />, label: formatStatus('FLAGGED') },
  };
  const cfg = map[status];
  return <Badge variant={cfg.variant} icon={cfg.icon} label={cfg.label} />;
}

type ImportStatus = 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED';

export function ImportStatusBadge({ status }: { status: ImportStatus }) {
  const map: Record<ImportStatus, { variant: BadgeProps['variant']; icon: React.ReactNode; label: string }> = {
    QUEUED: { variant: 'neutral', icon: <Clock size={12} strokeWidth={1.5} />, label: formatStatus('PENDING') },
    PROCESSING: { variant: 'info', icon: <Loader size={12} strokeWidth={1.5} className={styles.spin} />, label: formatStatus('IN_PROGRESS') },
    DONE: { variant: 'success', icon: <CheckCircle size={12} strokeWidth={1.5} />, label: formatStatus('DONE') },
    FAILED: { variant: 'error', icon: <XCircle size={12} strokeWidth={1.5} />, label: formatStatus('FAILED') },
  };
  const cfg = map[status];
  return <Badge variant={cfg.variant} icon={cfg.icon} label={cfg.label} />;
}

export function RoleBadge({ role }: { role: string }) {
  return <Badge variant="info" icon={<Info size={12} strokeWidth={1.5} />} label={formatRole(role)} />;
}
