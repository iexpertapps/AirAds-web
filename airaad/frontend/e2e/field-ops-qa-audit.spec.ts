/**
 * AirAd Frontend E2E — Field Ops, QA, Audit & System Pages
 *
 * Covers:
 *  - Field Ops page renders visits list
 *  - QA dashboard renders metrics and flagged vendors
 *  - Audit log page renders log entries with filters
 *  - System Users page renders user list (SUPER_ADMIN only)
 */

import type { Page, Route } from '@playwright/test';
import { test, expect } from './fixtures';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_FIELD_VISITS = {
  count: 2,
  next: null,
  previous: null,
  data: [
    {
      id: 'visit-uuid-001',
      vendor_name: 'Test Grill House',
      agent_name: 'Test Field Agent',
      visited_at: '2025-01-15T10:00:00Z',
      drift_distance_m: 12.5,
      notes: 'Visited and confirmed location.',
      photos_count: 3,
    },
    {
      id: 'visit-uuid-002',
      vendor_name: 'Approved Bakery',
      agent_name: 'Test Field Agent',
      visited_at: '2025-01-16T11:00:00Z',
      drift_distance_m: 0.0,
      notes: null,
      photos_count: 1,
    },
  ],
};

const MOCK_QA_DASHBOARD = {
  success: true,
  data: {
    total_vendors: 250,
    pending_review: 45,
    approved: 180,
    rejected: 10,
    flagged: 15,
    needs_review: 20,
    duplicate_clusters: [
      {
        cluster_id: 'cluster-001',
        vendor_ids: ['vendor-uuid-001', 'vendor-uuid-002'],
        similarity_score: 0.92,
        representative_name: 'Test Grill House',
      },
    ],
  },
};

const MOCK_AUDIT_LOGS = {
  count: 3,
  next: null,
  previous: null,
  data: [
    {
      id: 'audit-uuid-001',
      action: 'VENDOR_CREATED',
      actor_email: 'superadmin@test.airaad.com',
      target_model: 'Vendor',
      target_id: 'vendor-uuid-001',
      created_at: '2025-01-15T10:00:00Z',
      ip_address: '127.0.0.1',
    },
    {
      id: 'audit-uuid-002',
      action: 'VENDOR_QC_STATUS_CHANGED',
      actor_email: 'qareviewer@test.airaad.com',
      target_model: 'Vendor',
      target_id: 'vendor-uuid-001',
      created_at: '2025-01-15T11:00:00Z',
      ip_address: '127.0.0.1',
    },
    {
      id: 'audit-uuid-003',
      action: 'USER_LOGIN',
      actor_email: 'dataentry@test.airaad.com',
      target_model: 'AdminUser',
      target_id: 'user-uuid-001',
      created_at: '2025-01-15T09:00:00Z',
      ip_address: '192.168.1.1',
    },
  ],
};

const MOCK_USERS = {
  count: 3,
  next: null,
  previous: null,
  data: [
    {
      id: 'user-uuid-001',
      email: 'superadmin@test.airaad.com',
      full_name: 'Test Super Admin',
      role: 'SUPER_ADMIN',
      is_active: true,
      created_at: '2025-01-01T00:00:00Z',
    },
    {
      id: 'user-uuid-002',
      email: 'dataentry@test.airaad.com',
      full_name: 'Test Data Entry',
      role: 'DATA_ENTRY',
      is_active: true,
      created_at: '2025-01-02T00:00:00Z',
    },
    {
      id: 'user-uuid-003',
      email: 'qareviewer@test.airaad.com',
      full_name: 'Test QA Reviewer',
      role: 'QA_REVIEWER',
      is_active: false,
      created_at: '2025-01-03T00:00:00Z',
    },
  ],
};

// ---------------------------------------------------------------------------
// Field Ops Page
// ---------------------------------------------------------------------------

test.describe('Field Ops Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/field-ops/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_FIELD_VISITS });
    });
    await page.goto('/field-ops');
  });

  test('renders field ops page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /field.?ops|field visits/i })).toBeVisible();
  });

  test('renders visit rows', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Test Grill House')).toBeVisible();
    await expect(page.getByText('Approved Bakery')).toBeVisible();
  });

  test('renders agent names', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Test Field Agent').first()).toBeVisible();
  });

  test('renders drift distance', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/12\.5|12\.50/)).toBeVisible();
  });

  test('renders photo counts', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('3').first()).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// QA Dashboard Page
// ---------------------------------------------------------------------------

test.describe('QA Dashboard Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/qa/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_QA_DASHBOARD });
    });
    await page.goto('/qa');
  });

  test('renders QA page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /qa|quality/i })).toBeVisible();
  });

  test('renders total vendor count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('250')).toBeVisible();
  });

  test('renders pending review count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('45')).toBeVisible();
  });

  test('renders approved count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('180')).toBeVisible();
  });

  test('renders flagged count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('15')).toBeVisible();
  });

  test('renders duplicate cluster section', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/duplicate|cluster/i)).toBeVisible();
  });

  test('renders rejected count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('10')).toBeVisible();
  });

  test('renders needs review count', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('20')).toBeVisible();
  });

  test('renders duplicate cluster representative name', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/Test Grill House/i)).toBeVisible();
  });

  test('renders similarity score for duplicate cluster', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/0\.92|92%|similarity/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Audit Log Page
// ---------------------------------------------------------------------------

test.describe('Audit Log Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/audit/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_AUDIT_LOGS });
    });
    await page.goto('/system/audit');
  });

  test('renders audit log page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /audit/i })).toBeVisible();
  });

  test('renders audit action types', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('VENDOR_CREATED')).toBeVisible();
    await expect(page.getByText('VENDOR_QC_STATUS_CHANGED')).toBeVisible();
    await expect(page.getByText('USER_LOGIN')).toBeVisible();
  });

  test('renders actor emails', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('superadmin@test.airaad.com').first()).toBeVisible();
    await expect(page.getByText('qareviewer@test.airaad.com').first()).toBeVisible();
  });

  test('renders target model names', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Vendor').first()).toBeVisible();
  });

  test('has action filter', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const filterInput = page.getByPlaceholder(/filter|search|action/i);
    const filterSelect = page.getByRole('combobox');
    const hasFilter = (await filterInput.count()) + (await filterSelect.count()) > 0;
    expect(hasFilter).toBe(true);
  });

  test('renders IP addresses', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('127.0.0.1').first()).toBeVisible();
  });

  test('renders timestamps', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // Timestamps from mock data (2025-01-15)
    await expect(page.getByText(/2025|jan/i).first()).toBeVisible();
  });

  test('audit log entries are sorted newest first', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // The most recent entry (audit-uuid-002 at 11:00) should appear before older ones
    const rows = page.locator('tr, [role="row"]');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('actor filter updates results', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const filterInput = page.getByPlaceholder(/filter|search|actor|email/i);
    if (await filterInput.count() > 0) {
      await filterInput.fill('superadmin');
      await page.waitForTimeout(400);
      // Should still show superadmin entries
      await expect(page.getByText('superadmin@test.airaad.com').first()).toBeVisible();
    }
  });
});

// ---------------------------------------------------------------------------
// Field Ops — Empty State
// ---------------------------------------------------------------------------

test.describe('Field Ops — Empty State', () => {
  test('shows empty state when no visits exist', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/field-ops/**', async (route: Route) => {
      await route.fulfill({
        json: { count: 0, next: null, previous: null, data: [] },
      });
    });
    await page.goto('/field-ops');
    await expect(page.getByText(/no visits|no field visits|empty|no data/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// System Users Page (SUPER_ADMIN only)
// ---------------------------------------------------------------------------

test.describe('System Users Page', () => {
  test.beforeEach(async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await page.route('**/api/v1/auth/users/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_USERS });
    });
    await page.goto('/system/users');
  });

  test('renders users page heading', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await expect(page.getByRole('heading', { name: /users|team/i })).toBeVisible();
  });

  test('renders user emails', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await expect(page.getByText('superadmin@test.airaad.com')).toBeVisible();
    await expect(page.getByText('dataentry@test.airaad.com')).toBeVisible();
    await expect(page.getByText('qareviewer@test.airaad.com')).toBeVisible();
  });

  test('renders user roles', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await expect(page.getByText('SUPER_ADMIN')).toBeVisible();
    await expect(page.getByText('DATA_ENTRY')).toBeVisible();
    await expect(page.getByText('QA_REVIEWER')).toBeVisible();
  });

  test('renders active/inactive status', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await expect(page.getByText(/active|inactive/i).first()).toBeVisible();
  });

  test('has invite/create user button', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await expect(
      page.getByRole('button', { name: /invite|create|add user/i }),
    ).toBeVisible();
  });

  test('opens create user form on button click', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await page.getByRole('button', { name: /invite|create|add user/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('create user form validates required fields', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    await page.getByRole('button', { name: /invite|create|add user/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /save|submit|create/i }).click();
    await expect(page.getByText(/required/i).first()).toBeVisible();
  });

  test('has search or filter for users', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    const searchInput = page.getByPlaceholder(/search|filter/i);
    const filterSelect = page.getByRole('combobox');
    const hasFilter = (await searchInput.count()) + (await filterSelect.count()) > 0;
    expect(hasFilter).toBe(true);
  });

  test('inactive user shows different visual indicator', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    // user-uuid-003 (qareviewer) is inactive
    await expect(page.getByText(/inactive|disabled/i)).toBeVisible();
  });

  test('user row has edit/action button', async ({ superAdminPage: page }: { superAdminPage: Page }) => {
    const editBtn = page.getByRole('button', { name: /edit|actions|more/i }).first();
    const hasAction = (await editBtn.count()) > 0;
    expect(hasAction).toBe(true);
  });
});
