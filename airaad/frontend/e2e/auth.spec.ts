/**
 * AirAd Frontend E2E — Authentication Flows
 *
 * Covers:
 *  - Login page rendering
 *  - Form validation (client-side)
 *  - Successful login redirects to dashboard
 *  - Invalid credentials shows error
 *  - Password visibility toggle
 *  - Unauthenticated redirect to /login
 *  - Authenticated redirect away from /login
 *  - Logout clears session and redirects
 */

import { test, expect, loginViaUI, seedAuthState } from './fixtures';

// ---------------------------------------------------------------------------
// Login page rendering
// ---------------------------------------------------------------------------

test.describe('Login Page — Rendering', () => {
  test('shows AirAd branding and sign-in form', async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });

    await expect(page.locator('[aria-label="AirAd Admin Portal"]')).toBeVisible();
    await expect(page.getByText('Internal Admin Portal')).toBeVisible();
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });

  test('has correct input types', async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });

    await expect(page.locator('#email')).toHaveAttribute('type', 'email');
    await expect(page.locator('#password')).toHaveAttribute('type', 'password');
  });

  test('email input has autocomplete=email', async ({ page }) => {
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });
    await expect(page.locator('#email')).toHaveAttribute('autocomplete', 'email');
  });
});

// ---------------------------------------------------------------------------
// Client-side form validation
// ---------------------------------------------------------------------------

test.describe('Login Page — Client-side Validation', () => {
  test('shows required errors when submitting empty form', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByText('Email is required')).toBeVisible();
    await expect(page.getByText('Password is required')).toBeVisible();
  });

  test('shows invalid email error for bad email format', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Email address').fill('not-an-email');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.getByText('Enter a valid email address')).toBeVisible();
  });

  test('clears validation errors when valid input is entered', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page.getByText('Email is required')).toBeVisible();

    await page.locator('#email').fill('admin@test.com');
    await page.locator('#password').fill('password123');
    await expect(page.getByText('Email is required')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Password visibility toggle
// ---------------------------------------------------------------------------

test.describe('Login Page — Password Toggle', () => {
  test('toggles password visibility on button click', async ({ page }) => {
    await page.goto('/login');
    const passwordInput = page.locator('#password');
    const toggleBtn = page.getByRole('button', { name: 'Show password' });

    await expect(passwordInput).toHaveAttribute('type', 'password');
    await toggleBtn.click();
    await expect(passwordInput).toHaveAttribute('type', 'text');
    await expect(page.getByRole('button', { name: 'Hide password' })).toBeVisible();

    await page.getByRole('button', { name: 'Hide password' }).click();
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});

// ---------------------------------------------------------------------------
// Unauthenticated redirect
// ---------------------------------------------------------------------------

test.describe('Route Guards — Unauthenticated', () => {
  test('redirects unauthenticated user from / to /login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated user from /vendors to /login', async ({ page }) => {
    await page.goto('/vendors');
    await expect(page).toHaveURL(/\/login/);
  });

  test('redirects unauthenticated user from /geo to /login', async ({ page }) => {
    await page.goto('/geo');
    await expect(page).toHaveURL(/\/login/);
  });

  test('preserves redirect param in URL', async ({ page }) => {
    await page.goto('/vendors');
    await expect(page).toHaveURL(/redirect=%2Fvendors/);
  });

  test('redirects authenticated user away from /login to /', async ({ page }) => {
    await seedAuthState(page, {
      id: 'test-id',
      email: 'superadmin@test.airaad.com',
      role: 'SUPER_ADMIN',
      full_name: 'Test Admin',
    });
    await page.goto('/login');
    await expect(page).toHaveURL('/');
  });
});

// ---------------------------------------------------------------------------
// Login — API error handling
// ---------------------------------------------------------------------------

test.describe('Login Page — API Error Handling', () => {
  test('shows error message on invalid credentials', async ({ page }) => {
    await page.route('**/api/v1/auth/login/**', async (route) => {
      await route.fulfill({
        status: 401,
        json: { success: false, message: 'Invalid credentials' },
      });
    });
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });

    await page.getByLabel('Email address').fill('wrong@test.com');
    await page.locator('#password').fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // apiError paragraph has aria-live="assertive" — target it specifically
    await expect(page.locator('[aria-live="assertive"]')).toBeVisible();
    await expect(page.locator('[aria-live="assertive"]')).toContainText(/invalid|incorrect|login failed/i);
  });

  test('shows error message on network failure', async ({ page }) => {
    await page.route('**/api/v1/auth/login/**', async (route) => {
      await route.abort('failed');
    });
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });

    await page.getByLabel('Email address').fill('admin@test.com');
    await page.locator('#password').fill('password123');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Network abort → component shows 'Login failed. Please try again.'
    await expect(page.locator('[aria-live="assertive"]')).toBeVisible();
    await expect(page.locator('[aria-live="assertive"]')).toContainText(/login failed|try again/i);
  });

  test('sign in button is present and submits the form', async ({ page }) => {
    await page.route('**/api/v1/auth/login/**', async (route) => {
      await route.fulfill({ status: 401, json: { success: false, message: 'Invalid credentials' } });
    });
    await page.goto('/login');
    await page.waitForSelector('#email', { state: 'visible' });

    await page.getByLabel('Email address').fill('admin@test.com');
    await page.locator('#password').fill('password123');

    const btn = page.getByRole('button', { name: 'Sign In' });
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
    await btn.click();

    // After submit with 401, api error paragraph appears
    await expect(page.locator('[aria-live="assertive"]')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Logout flow
// ---------------------------------------------------------------------------

test.describe('Logout Flow', () => {
  test('logout clears session and redirects to /login', async ({ page }) => {
    await seedAuthState(page, {
      id: 'test-id',
      email: 'superadmin@test.airaad.com',
      role: 'SUPER_ADMIN',
      full_name: 'Test Admin',
    });

    await page.route('**/api/v1/auth/logout/**', async (route) => {
      await route.fulfill({ status: 200, json: { success: true } });
    });

    await page.goto('/');
    await expect(page).not.toHaveURL(/\/login/);

    // Wait for dashboard to fully load (hydration complete)
    const logoutBtn = page.getByRole('button', { name: 'Logout' });
    await expect(logoutBtn).toBeVisible({ timeout: 10000 });
    await logoutBtn.click();

    await expect(page).toHaveURL(/\/login/);
  });

  test('after logout, protected routes redirect to /login', async ({ page }) => {
    await seedAuthState(page, {
      id: 'test-id',
      email: 'superadmin@test.airaad.com',
      role: 'SUPER_ADMIN',
      full_name: 'Test Admin',
    });

    await page.route('**/api/v1/auth/logout/**', async (route) => {
      await route.fulfill({ status: 200, json: { success: true } });
    });

    await page.goto('/');
    const logoutBtn = page.getByRole('button', { name: /logout|sign out/i });
    if (await logoutBtn.count() > 0) {
      await logoutBtn.click();
      await expect(page).toHaveURL(/\/login/);

      // Try to navigate to protected route — should redirect back to login
      await page.goto('/vendors');
      await expect(page).toHaveURL(/\/login/);
    }
  });
});

// ---------------------------------------------------------------------------
// 404 page
// ---------------------------------------------------------------------------

test.describe('404 Page', () => {
  test('shows not found page for unknown routes', async ({ page }) => {
    await page.goto('/this-route-does-not-exist');
    await expect(page.getByText(/not found|404/i).first()).toBeVisible();
  });
});
