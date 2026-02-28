export type NotificationType = 'SYSTEM' | 'CLAIM' | 'SUBSCRIPTION' | 'MODERATION' | 'MARKETING';
export type NotificationChannel = 'PUSH' | 'EMAIL' | 'SMS';
export type NotificationStatus = 'PENDING' | 'SENT' | 'FAILED';

export interface NotificationTemplate {
  id: string;
  slug: string;
  title_template: string;
  body_template: string;
  notification_type: NotificationType;
  is_active: boolean;
  created_at: string;
}

export interface NotificationLog {
  id: string;
  recipient_type: string;
  recipient_id: string;
  title: string;
  body: string;
  channel: NotificationChannel;
  status: NotificationStatus;
  sent_at: string | null;
  error_message: string;
  created_at: string;
}

export interface TemplateListResponse {
  success: boolean;
  data: NotificationTemplate[];
}

export interface LogListResponse {
  success: boolean;
  data: {
    results: NotificationLog[];
    count: number;
  };
}
