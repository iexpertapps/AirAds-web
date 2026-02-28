import { apiClient } from './client';

interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface SubscriptionStatus {
  vendor_id: string;
  current_plan: string;
  stripe_subscription_id: string | null;
  status: 'ACTIVE' | 'PAST_DUE' | 'CANCELED' | 'NONE';
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  invoice_pdf_url: string | null;
  plan: string;
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  const { data } = await apiClient.get<ApiResponse<SubscriptionStatus>>(
    '/api/v1/payments/subscription-status/',
  );
  return data.data;
}

export async function getInvoices(): Promise<Invoice[]> {
  const { data } = await apiClient.get<ApiResponse<Invoice[]>>(
    '/api/v1/payments/invoices/',
  );
  return data.data;
}

export async function createCheckoutSession(packageLevel: string): Promise<{ checkout_url: string }> {
  const { data } = await apiClient.post<ApiResponse<{ checkout_url: string }>>(
    '/api/v1/payments/create-checkout/',
    {
      level: packageLevel,
      success_url: `${window.location.origin}/portal/subscription?success=true`,
      cancel_url: `${window.location.origin}/portal/subscription?canceled=true`,
    },
  );
  return data.data;
}

export async function cancelSubscription(): Promise<{ message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/payments/cancel/',
  );
  return data.data;
}

export async function resumeSubscription(): Promise<{ message: string }> {
  const { data } = await apiClient.post<ApiResponse<{ message: string }>>(
    '/api/v1/payments/resume/',
  );
  return data.data;
}

export async function createPortalSession(): Promise<{ portal_url: string }> {
  const { data } = await apiClient.post<ApiResponse<{ portal_url: string }>>(
    '/api/v1/payments/create-portal-session/',
  );
  return data.data;
}
