/**
 * AirAd Frontend E2E — Vendor Management Flows
 *
 * Covers:
 *  - Vendor list page renders with API mock
 *  - Search/filter controls are present
 *  - Add vendor drawer opens and validates
 *  - Vendor detail page renders
 *  - QC status badge rendering
 *  - Delete confirmation modal
 *  - Pagination controls
 */

import { test, expect } from './fixtures';

// ---------------------------------------------------------------------------
// Mock API responses
// ---------------------------------------------------------------------------

const MOCK_VENDORS = {
  count: 3,
  next: null,
  previous: null,
  data: [
    {
      id: 'vendor-uuid-001',
      business_name: 'Test Grill House',
      city_name: 'Karachi',
      area_name: 'DHA Phase 6',
      qc_status: 'PENDING',
      data_source: 'MANUAL_ENTRY',
      phone: '+923001234567',
      created_at: '2025-01-15T10:00:00Z',
    },
    {
      id: 'vendor-uuid-002',
      business_name: 'Approved Bakery',
      city_name: 'Karachi',
      area_name: 'Clifton',
      qc_status: 'APPROVED',
      data_source: 'CSV_IMPORT',
      phone: '+923009876543',
      created_at: '2025-01-16T11:00:00Z',
    },
    {
      id: 'vendor-uuid-003',
      business_name: 'Flagged Pharmacy',
      city_name: 'Lahore',
      area_name: 'Gulberg',
      qc_status: 'FLAGGED',
      data_source: 'FIELD_AGENT',
      phone: '+923005551234',
      created_at: '2025-01-17T12:00:00Z',
    },
  ],
};

const MOCK_CITIES = {
  data: [
    { id: 'city-uuid-001', name: 'Karachi' },
    { id: 'city-uuid-002', name: 'Lahore' },
  ],
};

const MOCK_AREAS = {
  data: [
    { id: 'area-uuid-001', name: 'DHA Phase 6', city_id: 'city-uuid-001' },
    { id: 'area-uuid-002', name: 'Clifton', city_id: 'city-uuid-001' },
  ],
};

const MOCK_VENDOR_DETAIL = {
  success: true,
  data: {
    id: 'vendor-uuid-001',
    business_name: 'Test Grill House',
    slug: 'test-grill-house',
    city_name: 'Karachi',
    area_name: 'DHA Phase 6',
    landmark_name: 'Zamzama Boulevard',
    qc_status: 'PENDING',
    qc_notes: null,
    data_source: 'MANUAL_ENTRY',
    phone_number: '+923001234567',
    description: 'A test vendor for E2E tests.',
    address_text: 'Test Address, DHA Phase 6, Karachi',
    gps_point: { type: 'Point', coordinates: [67.0601, 24.8271] },
    business_hours: {
      MON: { open: '09:00', close: '22:00', is_closed: false },
      TUE: { open: '09:00', close: '22:00', is_closed: false },
      WED: { open: '09:00', close: '22:00', is_closed: false },
      THU: { open: '09:00', close: '22:00', is_closed: false },
      FRI: { open: '09:00', close: '23:00', is_closed: false },
      SAT: { open: '10:00', close: '23:00', is_closed: false },
      SUN: { open: '00:00', close: '00:00', is_closed: true },
    },
    tags: [],
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
  },
};

// ---------------------------------------------------------------------------
// Setup: intercept API calls with mocks
// ---------------------------------------------------------------------------

async function setupVendorMocks(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/vendors/**', async (route) => {
    const url = route.request().url();
    if (url.match(/\/api\/v1\/vendors\/vendor-uuid-001\//)) {
      await route.fulfill({ json: MOCK_VENDOR_DETAIL });
    } else {
      await route.fulfill({ json: MOCK_VENDORS });
    }
  });

  await page.route('**/api/v1/geo/cities/**', async (route) => {
    await route.fulfill({ json: MOCK_CITIES });
  });

  await page.route('**/api/v1/geo/areas/**', async (route) => {
    await route.fulfill({ json: MOCK_AREAS });
  });

  await page.route('**/api/v1/geo/landmarks/**', async (route) => {
    await route.fulfill({ json: { data: [] } });
  });

  await page.route('**/api/v1/tags/**', async (route) => {
    await route.fulfill({ json: { data: [] } });
  });
}

// ---------------------------------------------------------------------------
// Vendor List Page
// ---------------------------------------------------------------------------

test.describe('Vendor List Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors');
  });

  test('renders page heading', async ({ authenticatedPage: page }) => {
    await expect(page.getByRole('heading', { name: /vendors/i })).toBeVisible();
  });

  test('renders vendor rows from API', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('Test Grill House')).toBeVisible();
    await expect(page.getByText('Approved Bakery')).toBeVisible();
    await expect(page.getByText('Flagged Pharmacy')).toBeVisible();
  });

  test('renders QC status badges', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('PENDING')).toBeVisible();
    await expect(page.getByText('APPROVED')).toBeVisible();
    await expect(page.getByText('FLAGGED')).toBeVisible();
  });

  test('renders city and area names', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('Karachi').first()).toBeVisible();
    await expect(page.getByText('DHA Phase 6')).toBeVisible();
  });

  test('has search input', async ({ authenticatedPage: page }) => {
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible();
  });

  test('has QC status filter', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('All statuses')).toBeVisible();
  });

  test('has Add Vendor button for SUPER_ADMIN', async ({ authenticatedPage: page }) => {
    await expect(page.getByRole('button', { name: /add vendor/i })).toBeVisible();
  });

  test('opens add vendor drawer on button click', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /add vendor/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText(/add vendor/i).last()).toBeVisible();
  });

  test('vendor row links to detail page', async ({ authenticatedPage: page }) => {
    const vendorLink = page.getByRole('link', { name: /test grill house/i });
    await expect(vendorLink).toBeVisible();
    await expect(vendorLink).toHaveAttribute('href', /\/vendors\/vendor-uuid-001/);
  });
});

// ---------------------------------------------------------------------------
// Add Vendor Drawer — Form Validation
// ---------------------------------------------------------------------------

test.describe('Add Vendor Drawer — Validation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors');
    await page.getByRole('button', { name: /add vendor/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('shows required field errors on empty submit', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /save|submit|create/i }).click();
    // At minimum, business name should be required
    await expect(page.getByText(/required/i).first()).toBeVisible();
  });

  test('closes drawer on cancel', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /cancel|close/i }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Vendor Detail Page
// ---------------------------------------------------------------------------

test.describe('Vendor Detail Page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors/vendor-uuid-001');
  });

  test('renders vendor business name', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('Test Grill House')).toBeVisible();
  });

  test('renders decrypted phone number', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('+923001234567')).toBeVisible();
  });

  test('renders address', async ({ authenticatedPage: page }) => {
    await expect(page.getByText(/Test Address/i)).toBeVisible();
  });

  test('renders QC status', async ({ authenticatedPage: page }) => {
    await expect(page.getByText('PENDING')).toBeVisible();
  });

  test('renders business hours section', async ({ authenticatedPage: page }) => {
    // At least one day should be visible
    await expect(page.getByText(/MON|Monday/i).first()).toBeVisible();
  });

  test('renders GPS coordinates or map', async ({ authenticatedPage: page }) => {
    // Either a map or coordinate display should be present
    const hasMap = await page.locator('[class*="map"], [class*="Map"]').count();
    const hasCoords = await page.getByText(/67\.06|24\.82/).count();
    expect(hasMap + hasCoords).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Vendor Edit Flow
// ---------------------------------------------------------------------------

test.describe('Vendor Edit Flow', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors/vendor-uuid-001');
  });

  test('has edit button on vendor detail page', async ({ authenticatedPage: page }) => {
    const editBtn = page.getByRole('button', { name: /edit/i });
    await expect(editBtn).toBeVisible();
  });

  test('opens edit form/drawer on edit button click', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /edit/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });

  test('edit form is pre-filled with existing vendor data', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /edit/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    // Business name should be pre-filled
    const nameInput = page.getByRole('dialog').getByRole('textbox').first();
    const value = await nameInput.inputValue();
    expect(value.length).toBeGreaterThan(0);
  });

  test('edit form cancel closes dialog', async ({ authenticatedPage: page }) => {
    await page.getByRole('button', { name: /edit/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: /cancel|close/i }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Delete Confirmation Modal
// ---------------------------------------------------------------------------

test.describe('Vendor Delete Confirmation', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors');
  });

  test('has delete button or action on vendor row', async ({ authenticatedPage: page }) => {
    // Delete may be in a row action menu or a button
    const deleteBtn = page.getByRole('button', { name: /delete|remove/i }).first();
    const hasDelete = (await deleteBtn.count()) > 0;
    // Alternatively, there may be a row action menu
    const actionMenu = page.getByRole('button', { name: /actions|more|⋮|…/i }).first();
    const hasMenu = (await actionMenu.count()) > 0;
    expect(hasDelete || hasMenu).toBe(true);
  });

  test('delete shows confirmation dialog', async ({ authenticatedPage: page }) => {
    const deleteBtn = page.getByRole('button', { name: /delete|remove/i }).first();
    if (await deleteBtn.count() > 0) {
      await deleteBtn.click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText(/confirm|are you sure|delete/i)).toBeVisible();
    }
  });

  test('cancel on delete confirmation closes dialog', async ({ authenticatedPage: page }) => {
    const deleteBtn = page.getByRole('button', { name: /delete|remove/i }).first();
    if (await deleteBtn.count() > 0) {
      await deleteBtn.click();
      if (await page.getByRole('dialog').count() > 0) {
        await page.getByRole('button', { name: /cancel|no/i }).first().click();
        await expect(page.getByRole('dialog')).not.toBeVisible();
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Vendor Pagination
// ---------------------------------------------------------------------------

test.describe('Vendor List Pagination', () => {
  test('shows total count', async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors');
    // Total count (3 in mock) should be visible somewhere
    await expect(page.getByText(/3|total/i).first()).toBeVisible();
  });

  test('pagination controls render when there are multiple pages', async ({ authenticatedPage: page }) => {
    // Mock a large dataset to trigger pagination
    await page.route('**/api/v1/vendors/**', async (route) => {
      await route.fulfill({
        json: {
          count: 50,
          next: 'http://localhost:8000/api/v1/vendors/?page=2',
          previous: null,
          data: MOCK_VENDORS.data,
        },
      });
    });
    await page.goto('/vendors');
    // Pagination controls (next button or page numbers) should appear
    const paginationNext = page.getByRole('button', { name: /next|›|>/i });
    const pageNumbers = page.getByRole('button', { name: /^[0-9]+$/ });
    const hasPagination = (await paginationNext.count()) + (await pageNumbers.count()) > 0;
    expect(hasPagination).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Vendor Search & Filter
// ---------------------------------------------------------------------------

test.describe('Vendor Search & Filter', () => {
  test('search input triggers debounced API call', async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);

    let searchCalled = false;
    await page.route('**/api/v1/vendors/**', async (route) => {
      const url = route.request().url();
      if (url.includes('search=grill')) {
        searchCalled = true;
      }
      await route.fulfill({ json: MOCK_VENDORS });
    });

    await page.goto('/vendors');
    const searchInput = page.getByPlaceholder(/search/i);
    await searchInput.fill('grill');

    // Wait for debounce (300ms default) + network
    await page.waitForTimeout(500);
    expect(searchCalled).toBe(true);
  });

  test('QC status filter updates URL param', async ({ authenticatedPage: page }) => {
    await setupVendorMocks(page);
    await page.goto('/vendors');

    const statusSelect = page.getByRole('combobox').first();
    await statusSelect.selectOption('APPROVED');

    await expect(page).toHaveURL(/qc_status=APPROVED/);
  });
});
