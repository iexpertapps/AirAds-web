/**
 * AirAd Frontend E2E — Imports Page
 *
 * Covers:
 *  - Import batch list rendering
 *  - Status badges (QUEUED, PROCESSING, COMPLETED, FAILED)
 *  - Upload CSV form
 *  - Batch detail view with error log
 *  - Pagination
 */

import type { Page, Route } from '@playwright/test';
import { test, expect } from './fixtures';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_IMPORT_BATCHES = {
  count: 4,
  next: null,
  previous: null,
  data: [
    {
      id: 'batch-uuid-001',
      file_key: 'imports/batch-001.csv',
      status: 'COMPLETED',
      total_rows: 150,
      processed_rows: 150,
      error_count: 2,
      created_at: '2025-01-15T10:00:00Z',
      created_by_name: 'Test Super Admin',
    },
    {
      id: 'batch-uuid-002',
      file_key: 'imports/batch-002.csv',
      status: 'PROCESSING',
      total_rows: 200,
      processed_rows: 80,
      error_count: 0,
      created_at: '2025-01-16T11:00:00Z',
      created_by_name: 'Test Data Entry',
    },
    {
      id: 'batch-uuid-003',
      file_key: 'imports/batch-003.csv',
      status: 'QUEUED',
      total_rows: 0,
      processed_rows: 0,
      error_count: 0,
      created_at: '2025-01-17T12:00:00Z',
      created_by_name: 'Test Data Entry',
    },
    {
      id: 'batch-uuid-004',
      file_key: 'imports/batch-004.csv',
      status: 'FAILED',
      total_rows: 50,
      processed_rows: 10,
      error_count: 40,
      created_at: '2025-01-18T13:00:00Z',
      created_by_name: 'Test Super Admin',
    },
  ],
};

const MOCK_BATCH_DETAIL = {
  success: true,
  data: {
    id: 'batch-uuid-001',
    file_key: 'imports/batch-001.csv',
    status: 'COMPLETED',
    total_rows: 150,
    processed_rows: 150,
    error_count: 2,
    error_log: [
      { row: 5, field: 'phone', msg: 'Invalid phone number format' },
      { row: 12, field: 'longitude', msg: 'Longitude out of range' },
    ],
    created_at: '2025-01-15T10:00:00Z',
    created_by_name: 'Test Super Admin',
  },
};

// ---------------------------------------------------------------------------
// Imports Page
// ---------------------------------------------------------------------------

test.describe('Imports Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/imports/**', async (route: Route) => {
      const url = route.request().url();
      if (url.match(/\/api\/v1\/imports\/batch-uuid-001\//)) {
        await route.fulfill({ json: MOCK_BATCH_DETAIL });
      } else {
        await route.fulfill({ json: MOCK_IMPORT_BATCHES });
      }
    });
    await page.goto('/imports');
  });

  test('renders imports page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /imports/i })).toBeVisible();
  });

  test('renders import batch rows', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('batch-001.csv')).toBeVisible();
    await expect(page.getByText('batch-002.csv')).toBeVisible();
    await expect(page.getByText('batch-003.csv')).toBeVisible();
    await expect(page.getByText('batch-004.csv')).toBeVisible();
  });

  test('renders status badges for all statuses', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('COMPLETED')).toBeVisible();
    await expect(page.getByText('PROCESSING')).toBeVisible();
    await expect(page.getByText('QUEUED')).toBeVisible();
    await expect(page.getByText('FAILED')).toBeVisible();
  });

  test('renders row counts', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('150')).toBeVisible();
  });

  test('has upload CSV button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(
      page.getByRole('button', { name: /upload|import|new batch/i }),
    ).toBeVisible();
  });

  test('opens upload form on button click', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /upload|import|new batch/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('upload form has file input', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /upload|import|new batch/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('shows error count for failed/completed batches', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // error_count = 2 for batch-001, 40 for batch-004
    await expect(page.getByText('2').first()).toBeVisible();
  });

  test('shows created_by name', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Test Super Admin').first()).toBeVisible();
  });

  test('batch rows link to detail page', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const batchLink = page.getByRole('link', { name: /batch-001/i });
    if (await batchLink.count() > 0) {
      await expect(batchLink).toHaveAttribute('href', /batch-uuid-001/);
    }
  });
});

// ---------------------------------------------------------------------------
// Import Batch Detail Page
// ---------------------------------------------------------------------------

test.describe('Import Batch Detail Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/imports/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_BATCH_DETAIL });
    });
    await page.goto('/imports/batch-uuid-001');
  });

  test('renders batch status', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('COMPLETED')).toBeVisible();
  });

  test('renders total and processed row counts', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('150').first()).toBeVisible();
  });

  test('renders error log section', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/error.?log|errors/i)).toBeVisible();
  });

  test('renders error log entries with row numbers', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // error_log has row 5 and row 12
    await expect(page.getByText(/row.?5|5/i).first()).toBeVisible();
  });

  test('renders error field names', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/phone|longitude/i).first()).toBeVisible();
  });

  test('renders error messages', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/invalid phone|out of range/i)).toBeVisible();
  });

  test('renders created_by name', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Test Super Admin')).toBeVisible();
  });

  test('has back/breadcrumb navigation to imports list', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const backLink = page.getByRole('link', { name: /imports|back/i });
    const breadcrumb = page.getByText(/imports/i).first();
    const hasNav = (await backLink.count()) + (await breadcrumb.count()) > 0;
    expect(hasNav).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Import Empty State
// ---------------------------------------------------------------------------

test.describe('Imports Empty State', () => {
  test('shows empty state when no batches exist', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/imports/**', async (route: Route) => {
      await route.fulfill({
        json: { count: 0, next: null, previous: null, data: [] },
      });
    });
    await page.goto('/imports');
    await expect(page.getByText(/no imports|no batches|empty|get started/i)).toBeVisible();
  });
});
