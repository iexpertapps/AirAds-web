/**
 * AirAd Frontend E2E — Navigation & Role-Based Access Control
 *
 * Covers:
 *  - Sidebar navigation links render for SUPER_ADMIN
 *  - Role-gated routes redirect non-permitted roles
 *  - SUPER_ADMIN can access all routes
 *  - DATA_ENTRY cannot access /system/users (SUPER_ADMIN only)
 *  - QA_REVIEWER cannot access /imports
 *  - FIELD_AGENT cannot access /geo
 */

import { test, expect, seedAuthState } from './fixtures';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function navigateAuthenticated(page: import('@playwright/test').Page, role: string, path: string) {
  await seedAuthState(page, {
    id: `test-${role.toLowerCase()}-id`,
    email: `${role.toLowerCase()}@test.airaad.com`,
    role,
    full_name: `Test ${role}`,
  });
  await page.goto(path);
}

// ---------------------------------------------------------------------------
// Dashboard / Home
// ---------------------------------------------------------------------------

test.describe('Dashboard — Platform Health', () => {
  test('SUPER_ADMIN sees platform health page at /', async ({ page }) => {
    await navigateAuthenticated(page, 'SUPER_ADMIN', '/');
    await expect(page).toHaveURL('/');
    // Should not be redirected to login
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('DATA_ENTRY can access dashboard', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/');
    await expect(page).toHaveURL('/');
    await expect(page).not.toHaveURL(/\/login/);
  });
});

// ---------------------------------------------------------------------------
// SUPER_ADMIN — full access
// ---------------------------------------------------------------------------

test.describe('SUPER_ADMIN — Full Route Access', () => {
  const routes = [
    '/',
    '/geo',
    '/tags',
    '/vendors',
    '/imports',
    '/field-ops',
    '/qa',
    '/system/audit',
    '/system/users',
  ];

  for (const route of routes) {
    test(`can access ${route}`, async ({ page }) => {
      await navigateAuthenticated(page, 'SUPER_ADMIN', route);
      await expect(page).not.toHaveURL(/\/login/);
      // Should not be redirected away (no 403 redirect to /)
      await expect(page).toHaveURL(route);
    });
  }
});

// ---------------------------------------------------------------------------
// DATA_ENTRY — restricted routes
// ---------------------------------------------------------------------------

test.describe('DATA_ENTRY — Role-Based Restrictions', () => {
  test('can access /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/vendors');
    await expect(page).toHaveURL('/vendors');
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('can access /geo', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/geo');
    await expect(page).toHaveURL('/geo');
  });

  test('can access /imports', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/imports');
    await expect(page).toHaveURL('/imports');
  });

  test('is redirected from /system/users (SUPER_ADMIN only)', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/system/users');
    // RequireRole redirects to /
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /field-ops (SUPER_ADMIN, CITY_MANAGER, FIELD_AGENT only)', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/field-ops');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /qa (SUPER_ADMIN, CITY_MANAGER, QA_REVIEWER only)', async ({ page }) => {
    await navigateAuthenticated(page, 'DATA_ENTRY', '/qa');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// QA_REVIEWER — restricted routes
// ---------------------------------------------------------------------------

test.describe('QA_REVIEWER — Role-Based Restrictions', () => {
  test('can access /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'QA_REVIEWER', '/vendors');
    await expect(page).toHaveURL('/vendors');
  });

  test('can access /qa', async ({ page }) => {
    await navigateAuthenticated(page, 'QA_REVIEWER', '/qa');
    await expect(page).toHaveURL('/qa');
  });

  test('is redirected from /imports', async ({ page }) => {
    await navigateAuthenticated(page, 'QA_REVIEWER', '/imports');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /geo', async ({ page }) => {
    await navigateAuthenticated(page, 'QA_REVIEWER', '/geo');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /system/users', async ({ page }) => {
    await navigateAuthenticated(page, 'QA_REVIEWER', '/system/users');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// FIELD_AGENT — restricted routes
// ---------------------------------------------------------------------------

test.describe('FIELD_AGENT — Role-Based Restrictions', () => {
  test('can access /field-ops', async ({ page }) => {
    await navigateAuthenticated(page, 'FIELD_AGENT', '/field-ops');
    await expect(page).toHaveURL('/field-ops');
  });

  test('is redirected from /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'FIELD_AGENT', '/vendors');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /geo', async ({ page }) => {
    await navigateAuthenticated(page, 'FIELD_AGENT', '/geo');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /imports', async ({ page }) => {
    await navigateAuthenticated(page, 'FIELD_AGENT', '/imports');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// CITY_MANAGER — restricted routes
// ---------------------------------------------------------------------------

test.describe('CITY_MANAGER — Role-Based Restrictions', () => {
  test('can access /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/vendors');
    await expect(page).toHaveURL('/vendors');
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('can access /geo', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/geo');
    await expect(page).toHaveURL('/geo');
  });

  test('can access /imports', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/imports');
    await expect(page).toHaveURL('/imports');
  });

  test('can access /field-ops', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/field-ops');
    await expect(page).toHaveURL('/field-ops');
  });

  test('can access /qa', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/qa');
    await expect(page).toHaveURL('/qa');
  });

  test('is redirected from /system/users (SUPER_ADMIN only)', async ({ page }) => {
    await navigateAuthenticated(page, 'CITY_MANAGER', '/system/users');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// ANALYST — restricted routes
// ---------------------------------------------------------------------------

test.describe('ANALYST — Role-Based Restrictions', () => {
  test('can access /system/audit', async ({ page }) => {
    await navigateAuthenticated(page, 'ANALYST', '/system/audit');
    await expect(page).toHaveURL('/system/audit');
  });

  test('is redirected from /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'ANALYST', '/vendors');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /system/users', async ({ page }) => {
    await navigateAuthenticated(page, 'ANALYST', '/system/users');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// SUPPORT — restricted routes
// ---------------------------------------------------------------------------

test.describe('SUPPORT — Role-Based Restrictions', () => {
  test('can access /vendors', async ({ page }) => {
    await navigateAuthenticated(page, 'SUPPORT', '/vendors');
    await expect(page).toHaveURL('/vendors');
  });

  test('is redirected from /geo', async ({ page }) => {
    await navigateAuthenticated(page, 'SUPPORT', '/geo');
    await expect(page).toHaveURL('/');
  });

  test('is redirected from /imports', async ({ page }) => {
    await navigateAuthenticated(page, 'SUPPORT', '/imports');
    await expect(page).toHaveURL('/');
  });
});
