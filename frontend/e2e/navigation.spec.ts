import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should load the home page (Today)', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Curately/);
  });

  test('should navigate between all pages', async ({ page }) => {
    await page.goto('/');

    // Navigate to Digest
    await page.getByRole('link', { name: /digest/i }).click();
    await expect(page).toHaveURL('/digest');

    // Navigate to Archive
    await page.getByRole('link', { name: /archive/i }).click();
    await expect(page).toHaveURL('/archive');

    // Navigate to Bookmarks
    await page.getByRole('link', { name: /bookmark/i }).click();
    await expect(page).toHaveURL('/bookmarks');

    // Navigate to Rewind
    await page.getByRole('link', { name: /rewind/i }).click();
    await expect(page).toHaveURL('/rewind');

    // Navigate to Settings
    await page.getByRole('link', { name: /setting/i }).click();
    await expect(page).toHaveURL('/settings');

    // Navigate back to Today
    await page.getByRole('link', { name: /today/i }).click();
    await expect(page).toHaveURL('/');
  });

  test('should highlight active navigation link', async ({ page }) => {
    await page.goto('/');
    const todayLink = page.getByRole('link', { name: /today/i });
    await expect(todayLink).toHaveAttribute('aria-current', 'page');
  });
});
