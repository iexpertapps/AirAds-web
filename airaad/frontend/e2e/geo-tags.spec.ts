/**
 * AirAd Frontend E2E — Geo & Tags Pages
 *
 * Covers:
 *  - Countries, Cities, Areas, Landmarks list rendering
 *  - Add forms open and validate
 *  - Tags list rendering with type badges
 *  - Tag create/edit drawer
 */

import type { Page, Route } from '@playwright/test';
import { test, expect } from './fixtures';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_COUNTRIES = {
  data: [
    { id: 'country-pk', code: 'PK', name: 'Pakistan', is_active: true },
    { id: 'country-ae', code: 'AE', name: 'UAE', is_active: true },
  ],
};

const MOCK_CITIES = {
  data: [
    { id: 'city-khi', slug: 'karachi', name: 'Karachi', country_name: 'Pakistan', is_active: true, display_order: 1 },
    { id: 'city-lhe', slug: 'lahore', name: 'Lahore', country_name: 'Pakistan', is_active: true, display_order: 2 },
  ],
};

const MOCK_AREAS = {
  data: [
    { id: 'area-dha', slug: 'dha-phase-6', name: 'DHA Phase 6', city_name: 'Karachi', is_active: true },
    { id: 'area-clifton', slug: 'clifton', name: 'Clifton', city_name: 'Karachi', is_active: true },
  ],
};

const MOCK_LANDMARKS = {
  data: [
    { id: 'lm-zamzama', slug: 'zamzama', name: 'Zamzama Boulevard', area_name: 'DHA Phase 6', is_active: true },
  ],
};

const MOCK_TAGS = {
  data: [
    { id: 'tag-001', slug: 'restaurant', name: 'Restaurant', tag_type: 'CATEGORY', display_label: 'Restaurant', is_active: true },
    { id: 'tag-002', slug: 'happy-hour', name: 'Happy Hour', tag_type: 'TIME', display_label: 'Happy Hour', is_active: true },
    { id: 'tag-003', slug: 'delivery', name: 'Delivery Available', tag_type: 'FEATURE', display_label: 'Delivery', is_active: true },
    { id: 'tag-sys', slug: 'system-tag', name: 'System Tag', tag_type: 'SYSTEM', display_label: 'System', is_active: true },
  ],
};

// ---------------------------------------------------------------------------
// Geo Page
// ---------------------------------------------------------------------------

test.describe('Geo Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/geo/countries/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_COUNTRIES });
    });
    await page.route('**/api/v1/geo/cities/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_CITIES });
    });
    await page.route('**/api/v1/geo/areas/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_AREAS });
    });
    await page.route('**/api/v1/geo/landmarks/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_LANDMARKS });
    });
    await page.goto('/geo');
  });

  test('renders geo page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /geo|geography|locations/i })).toBeVisible();
  });

  test('renders countries data', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Pakistan')).toBeVisible();
    await expect(page.getByText('PK')).toBeVisible();
  });

  test('renders cities data', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Karachi')).toBeVisible();
    await expect(page.getByText('Lahore')).toBeVisible();
  });

  test('renders areas data', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('DHA Phase 6')).toBeVisible();
    await expect(page.getByText('Clifton')).toBeVisible();
  });

  test('renders landmarks data', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Zamzama Boulevard')).toBeVisible();
  });

  test('has add country button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('button', { name: /add country/i })).toBeVisible();
  });

  test('has add city button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('button', { name: /add city/i })).toBeVisible();
  });

  test('opens add city form on button click', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add city/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('add city form validates required fields', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add city/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /save|submit|create/i }).click();
    await expect(page.getByText(/required/i).first()).toBeVisible();
  });

  test('has add area button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('button', { name: /add area/i })).toBeVisible();
  });

  test('opens add area form on button click', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add area/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('has add landmark button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('button', { name: /add landmark/i })).toBeVisible();
  });

  test('opens add landmark form on button click', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add landmark/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('renders country active status', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/active/i).first()).toBeVisible();
  });

  test('renders city display order', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // display_order 1 and 2 should be visible
    await expect(page.getByText('1').first()).toBeVisible();
  });

  test('cancel on add city form closes dialog', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add city/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /cancel|close/i }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Tags Page
// ---------------------------------------------------------------------------

test.describe('Tags Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.route('**/api/v1/tags/**', async (route: Route) => {
      await route.fulfill({ json: MOCK_TAGS });
    });
    await page.goto('/tags');
  });

  test('renders tags page heading', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('heading', { name: /tags/i })).toBeVisible();
  });

  test('renders tag names', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('Restaurant')).toBeVisible();
    await expect(page.getByText('Happy Hour')).toBeVisible();
    await expect(page.getByText('Delivery Available')).toBeVisible();
  });

  test('renders tag type badges', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText('CATEGORY')).toBeVisible();
    await expect(page.getByText('TIME')).toBeVisible();
    await expect(page.getByText('FEATURE')).toBeVisible();
    await expect(page.getByText('SYSTEM')).toBeVisible();
  });

  test('has add tag button', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByRole('button', { name: /add tag/i })).toBeVisible();
  });

  test('opens add tag form on button click', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add tag/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('add tag form validates required fields', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add tag/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /save|submit|create/i }).click();
    await expect(page.getByText(/required/i).first()).toBeVisible();
  });

  test('cancel on add tag form closes dialog', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await page.getByRole('button', { name: /add tag/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /cancel|close/i }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('has tag type filter', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const filterSelect = page.getByRole('combobox');
    const searchInput = page.getByPlaceholder(/search|filter/i);
    const hasFilter = (await filterSelect.count()) + (await searchInput.count()) > 0;
    expect(hasFilter).toBe(true);
  });

  test('renders is_active status for tags', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    await expect(page.getByText(/active/i).first()).toBeVisible();
  });

  test('tag row has edit button or action', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    const editBtn = page.getByRole('button', { name: /edit|actions|more/i }).first();
    const hasAction = (await editBtn.count()) > 0;
    expect(hasAction).toBe(true);
  });

  test('renders display_label for tags', async ({ authenticatedPage: page }: { authenticatedPage: Page }) => {
    // display_label values from mock: Restaurant, Happy Hour, Delivery, System
    await expect(page.getByText('Delivery').first()).toBeVisible();
  });
});
