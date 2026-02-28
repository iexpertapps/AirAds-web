import { useState } from 'react';
import { Bell, FileText, History } from 'lucide-react';
import { AdminLayout } from '@/shared/components/dls/AdminLayout';
import { PageHeader } from '@/shared/components/dls/PageHeader';
import { Badge } from '@/shared/components/dls/Badge';
import { SkeletonTable } from '@/shared/components/dls/SkeletonTable';
import { EmptyState } from '@/shared/components/dls/EmptyState';
import { useNotificationTemplates, useNotificationHistory } from '../queries/useNotifications';
import { formatDateTime, formatLabel } from '@/shared/utils/formatters';
import type { NotificationTemplate, NotificationLog } from '../types/notification';
import styles from './NotificationManagementPage.module.css';

type TabId = 'templates' | 'history';

const STATUS_VARIANT: Record<string, 'success' | 'warning' | 'error'> = {
  SENT: 'success',
  PENDING: 'warning',
  FAILED: 'error',
};

export default function NotificationManagementPage() {
  const [activeTab, setActiveTab] = useState<TabId>('templates');
  const templates = useNotificationTemplates();
  const history = useNotificationHistory();

  return (
    <AdminLayout title="Notifications">
      <PageHeader
        heading="Notification management"
        subheading="Templates and delivery history"
      />

      <div className={styles.tabs} role="tablist" aria-label="Notification sections">
        <button
          className={[styles.tab, activeTab === 'templates' ? styles['tab--active'] : ''].join(' ')}
          role="tab"
          aria-selected={activeTab === 'templates'}
          aria-controls="panel-templates"
          onClick={() => setActiveTab('templates')}
        >
          <FileText size={16} strokeWidth={1.5} aria-hidden="true" />
          Templates
        </button>
        <button
          className={[styles.tab, activeTab === 'history' ? styles['tab--active'] : ''].join(' ')}
          role="tab"
          aria-selected={activeTab === 'history'}
          aria-controls="panel-history"
          onClick={() => setActiveTab('history')}
        >
          <History size={16} strokeWidth={1.5} aria-hidden="true" />
          Delivery history
        </button>
      </div>

      {activeTab === 'templates' ? (
        <TemplatesPanel
          templates={templates.data ?? []}
          isLoading={templates.isLoading}
          hasError={!!templates.error}
          onRetry={() => templates.refetch()}
        />
      ) : (
        <HistoryPanel
          logs={history.data?.results ?? []}
          totalCount={history.data?.count ?? 0}
          isLoading={history.isLoading}
          hasError={!!history.error}
          onRetry={() => history.refetch()}
        />
      )}
    </AdminLayout>
  );
}

interface TemplatesPanelProps {
  templates: NotificationTemplate[];
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
}

function TemplatesPanel({ templates, isLoading, hasError, onRetry }: TemplatesPanelProps) {
  if (isLoading) return <SkeletonTable rows={6} columns={5} />;

  if (hasError) {
    return (
      <EmptyState
        illustration={<Bell size={32} strokeWidth={1.5} />}
        heading="Failed to load templates"
        subheading="Something went wrong while fetching notification templates."
        ctaLabel="Retry"
        onCta={onRetry}
      />
    );
  }

  if (templates.length === 0) {
    return (
      <EmptyState
        illustration={<FileText size={32} strokeWidth={1.5} />}
        heading="No templates configured"
        subheading="Notification templates will appear here once created in the backend."
      />
    );
  }

  return (
    <div id="panel-templates" role="tabpanel" className={styles.tableWrap}>
      <table className={styles.table} aria-label="Notification templates">
        <thead>
          <tr>
            <th scope="col">Slug</th>
            <th scope="col">Title template</th>
            <th scope="col">Type</th>
            <th scope="col">Status</th>
            <th scope="col">Created</th>
          </tr>
        </thead>
        <tbody>
          {templates.map((tpl) => (
            <tr key={tpl.id}>
              <td><span className={styles.slug}>{tpl.slug}</span></td>
              <td><span className={styles.templateText}>{tpl.title_template}</span></td>
              <td><Badge variant="neutral" label={formatLabel(tpl.notification_type)} /></td>
              <td>
                <Badge
                  variant={tpl.is_active ? 'success' : 'neutral'}
                  label={tpl.is_active ? 'Active' : 'Inactive'}
                />
              </td>
              <td>{formatDateTime(tpl.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface HistoryPanelProps {
  logs: NotificationLog[];
  totalCount: number;
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
}

function HistoryPanel({ logs, isLoading, hasError, onRetry }: HistoryPanelProps) {
  if (isLoading) return <SkeletonTable rows={8} columns={6} />;

  if (hasError) {
    return (
      <EmptyState
        illustration={<Bell size={32} strokeWidth={1.5} />}
        heading="Failed to load delivery history"
        subheading="Something went wrong while fetching notification logs."
        ctaLabel="Retry"
        onCta={onRetry}
      />
    );
  }

  if (logs.length === 0) {
    return (
      <EmptyState
        illustration={<History size={32} strokeWidth={1.5} />}
        heading="No notifications sent yet"
        subheading="Delivery history will appear here after the first notification is dispatched."
      />
    );
  }

  return (
    <div id="panel-history" role="tabpanel" className={styles.tableWrap}>
      <table className={styles.table} aria-label="Notification delivery history">
        <thead>
          <tr>
            <th scope="col">Title</th>
            <th scope="col">Channel</th>
            <th scope="col">Recipient</th>
            <th scope="col">Status</th>
            <th scope="col">Sent at</th>
            <th scope="col">Error</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>
                <span className={styles.logTitle}>{log.title}</span>
                <br />
                <span className={styles.logBody}>{log.body}</span>
              </td>
              <td><span className={styles.channelBadge}>{log.channel}</span></td>
              <td>{formatLabel(log.recipient_type)}</td>
              <td>
                <Badge
                  variant={STATUS_VARIANT[log.status] ?? 'neutral'}
                  label={formatLabel(log.status)}
                />
              </td>
              <td>{log.sent_at ? formatDateTime(log.sent_at) : '—'}</td>
              <td>
                {log.error_message ? (
                  <span className={styles.errorText} title={log.error_message}>
                    {log.error_message}
                  </span>
                ) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
