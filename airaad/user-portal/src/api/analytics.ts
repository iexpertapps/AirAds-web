import { apiClient } from './client';

interface TrackEventPayload {
  event_type: string;
  vendor_id?: string;
  metadata?: Record<string, string | number | boolean>;
}

export async function trackEvent(payload: TrackEventPayload): Promise<void> {
  try {
    await apiClient.post('/api/v1/user-portal/analytics/track/', payload);
  } catch {
    // fire-and-forget — never block UI for analytics
  }
}

export async function startSession(): Promise<void> {
  try {
    await apiClient.post('/api/v1/user-portal/analytics/session/start/');
  } catch {
    // fire-and-forget
  }
}
