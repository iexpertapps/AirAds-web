/**
 * AirAd Frontend E2E — Platform Health Dashboard
 *
 * Covers:
 *  - KPI cards render with API mock
 *  - Charts section is present
 *  - Health status indicators
 *  - Analytics KPIs endpoint integration
 */

import type { Page, Route } from '@playwright/test';
import { test, expect } from './fixtures';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_HEALTH = {
  status: 'ok',
  db: 'ok',
  cache: 'ok',
  version: '1.0.0',
};

const MOCK_KPIS = {
  success: true,
  data: {
    total_vendors: 1250,
    vendors_pending_qa: 145,
    vendors_approved_today: 18,
    total_areas: 120,
    total_tags: 45,
    imports_processing: 3,
    daily_vendor_counts: [
      { date: '2025-01-14', count: 12 },
      { date: '2025-01-15', count: 8 },
    ],
    qc_status_breakdown: [
      { status: 'APPROVED', count: 980 },
      { status: 'PENDING', count: 145 },
    ],
    import_activity: [
      { date: '2025-01-15', count: 3 },
    ],
    top_search_terms: [],
    system_alerts: [],
    recent_activity: [],
  },
};

// ---------------------------------------------------------------------------
// Platform Health Dashboard
// ---------------------------------------------------------------------------

test.describe('Platform Health Dashboard', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // Register mocks before navigating so they intercept the initial load
    await page.route('**/api/v1/health/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_HEALTH });
    });
    await page.route('**/api/v1/analytics/kpis/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_KPIS });
    });
    await page.goto('/');
    // Wait for KPI data to be rendered
    await page.waitForLoadState('networkidle').catch(() => {});
  });

  test('renders dashboard page', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page).toHaveURL('/');
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('renders total vendors KPI', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('1,250').first()).toBeVisible();
  });

  test('renders pending QC count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('145').first()).toBeVisible();
  });

  test('renders health status indicator', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/system.*ok|ok/i).first()).toBeVisible();
  });

  test('renders page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /platform health/i }).first()).toBeVisible();
  });

  test('renders health status badge', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/system.*ok|ok/i).first()).toBeVisible();
  });

  test('renders total areas count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('120').first()).toBeVisible();
  });

  test('renders total tags count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('45').first()).toBeVisible();
  });

  test('renders QC status breakdown section', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // QC breakdown chart section heading
    await expect(page.getByText(/qc status breakdown/i)).toBeVisible();
  });

  test('renders imports processing count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('3').first()).toBeVisible();
  });

  test('renders vendors approved today', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('18').first()).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Platform Health — Degraded State
// ---------------------------------------------------------------------------

test.describe('Platform Health Dashboard — Degraded State', () => {
  test('shows degraded status when a service is down', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/health/**', async (route: Route) => {
      await route.fulfill({
        json: {
          status: 'degraded',
          db: 'ok',
          cache: 'unavailable',
          version: '1.0.0',
        },
      });
    });
    await page.route('**/api/v1/analytics/kpis/**', async (route: Route) => {
      await route.fulfill({ json: { success: true, data: { total_vendors: 0, vendors_pending_qa: 0, vendors_approved_today: 0, total_areas: 0, total_tags: 0, imports_processing: 0, daily_vendor_counts: [], qc_status_breakdown: [], import_activity: [], top_search_terms: [], system_alerts: [], recent_activity: [] } } });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByText(/degraded/i)).toBeVisible();
  });

  test('shows error state when health API fails', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/health/**', async (route: Route) => {
      await route.fulfill({ status: 503, json: { status: 'degraded' } });
    });
    await page.route('**/api/v1/analytics/kpis/**', async (route: Route) => {
      await route.fulfill({ json: { success: true, data: {} } });
    });

    await page.goto('/');
    // Page should still render without crashing
    await expect(page).not.toHaveURL(/\/login/);
  });
});
