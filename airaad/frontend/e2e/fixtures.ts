/**
 * AirAd Frontend E2E — Shared Fixtures & Helpers
 *
 * Provides:
 *  - Typed test fixture with pre-authenticated page
 *  - Login helper that sets sessionStorage auth state directly
 *  - API mock helpers for offline / CI runs
 */

import { test as base, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  full_name: string;
}

export interface TestFixtures {
  authenticatedPage: Page;
  superAdminPage: Page;
  dataEntryPage: Page;
  qaReviewerPage: Page;
}

// ---------------------------------------------------------------------------
// Seed auth state directly into sessionStorage (bypasses real login API)
// ---------------------------------------------------------------------------

export async function seedAuthState(
  page: Page,
  user: AuthUser,
  tokens = { access: 'fake-access-token', refresh: 'fake-refresh-token' },
) {
  // Register an init script on the browser context so it fires before page JS
  // on every navigation (including the very first goto). This ensures Zustand
  // hydrates with the seeded user before ProtectedRoute checks auth state.
  const authState = JSON.stringify({
    state: { user, refreshToken: tokens.refresh, accessToken: tokens.access },
    version: 0,
  });
  await page.context().addInitScript((serialised) => {
    sessionStorage.setItem('airaad-auth', serialised);
  }, authState);
}

// ---------------------------------------------------------------------------
// Perform a real login via the UI form
// ---------------------------------------------------------------------------

export async function loginViaUI(
  page: Page,
  email: string,
  password: string,
) {
  await page.goto('/login');
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign In' }).click();
}

// ---------------------------------------------------------------------------
// Extended test fixture
// ---------------------------------------------------------------------------

export const test = base.extend<TestFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await seedAuthState(page, {
      id: 'test-super-admin-id',
      email: 'superadmin@test.airaad.com',
      role: 'SUPER_ADMIN',
      full_name: 'Test Super Admin',
    });
    await use(page);
  },

  superAdminPage: async ({ page }, use) => {
    await seedAuthState(page, {
      id: 'test-super-admin-id',
      email: 'superadmin@test.airaad.com',
      role: 'SUPER_ADMIN',
      full_name: 'Test Super Admin',
    });
    await use(page);
  },

  dataEntryPage: async ({ page }, use) => {
    await seedAuthState(page, {
      id: 'test-data-entry-id',
      email: 'dataentry@test.airaad.com',
      role: 'DATA_ENTRY',
      full_name: 'Test Data Entry',
    });
    await use(page);
  },

  qaReviewerPage: async ({ page }, use) => {
    await seedAuthState(page, {
      id: 'test-qa-reviewer-id',
      email: 'qareviewer@test.airaad.com',
      role: 'QA_REVIEWER',
      full_name: 'Test QA Reviewer',
    });
    await use(page);
  },
});

export { expect };
