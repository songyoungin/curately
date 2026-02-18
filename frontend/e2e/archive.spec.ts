import { test, expect, type Page } from '@playwright/test';

test.describe('Archive Page', () => {
  const categorySectionHeader = (page: Page, label: string) =>
    page.locator('section > div > span', { hasText: label }).first();

  test.beforeEach(async ({ page }) => {
    await page.goto('/archive');
    // Wait for editions to load (calendar or list should be visible)
    await expect(page.getByRole('heading', { name: 'Archive' })).toBeVisible();
  });

  test('should display calendar view with current month heading', async ({
    page,
  }) => {
    // Calendar view is the default - verify month heading
    await expect(page.getByText('February 2026')).toBeVisible();

    // Verify weekday headers are displayed
    for (const day of ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) {
      await expect(page.getByText(day, { exact: true })).toBeVisible();
    }

    // Calendar toggle button should appear active (white bg with shadow)
    const calendarButton = page.getByRole('button', { name: 'Calendar' });
    await expect(calendarButton).toBeVisible();
  });

  test('should load articles when clicking a calendar date with editions', async ({
    page,
  }) => {
    // Click date 16 (2026-02-16 has 10 articles)
    const dateButton = page.getByRole('button', {
      name: /2026-02-16, 10 articles/,
    });
    await expect(dateButton).toBeVisible();
    await dateButton.click();

    // Wait for articles to load - DateHeader should appear
    // 2026-02-16 formatted as "Mon, Feb 16, 2026"
    await expect(page.getByText('10 articles')).toBeVisible();

    // Verify article cards are displayed - check for a known article title
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();

    // Verify category sections appear (articles have AI/ML, DevOps, Backend, Frontend)
    await expect(categorySectionHeader(page, 'AI/ML')).toBeVisible();

    // Verify the date cell is highlighted (aria-pressed)
    await expect(dateButton).toHaveAttribute('aria-pressed', 'true');
  });

  test('should switch to list view and display editions', async ({ page }) => {
    // Click the List toggle button
    const listButton = page.getByRole('button', { name: 'List' });
    await listButton.click();

    // Verify edition entries appear as buttons with formatted dates and article counts
    // mockEditions has 7 entries from 2026-02-10 to 2026-02-16
    await expect(page.getByText('10 articles', { exact: false })).toBeVisible();
    await expect(page.getByText('8 articles', { exact: false })).toBeVisible();
    await expect(page.getByText('6 articles', { exact: false })).toBeVisible();

    // Calendar should no longer be visible (no Previous/Next month buttons)
    await expect(
      page.getByRole('button', { name: 'Previous month' }),
    ).toBeHidden();
  });

  test('should load articles when clicking a list view edition', async ({
    page,
  }) => {
    // Switch to list view
    await page.getByRole('button', { name: 'List' }).click();

    // Click the first edition (Feb 16, 2026 with 10 articles)
    // The list shows formatted dates like "Mon, Feb 16, 2026"
    const editionButton = page.getByRole('button', {
      name: /Feb 16, 2026/,
    });
    await editionButton.click();

    // Wait for articles to load
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();

    // Verify category sections appear
    await expect(categorySectionHeader(page, 'AI/ML')).toBeVisible();
    await expect(categorySectionHeader(page, 'DevOps')).toBeVisible();
  });

  test('should navigate between months using Previous/Next buttons', async ({
    page,
  }) => {
    // Verify starting month
    await expect(page.getByText('February 2026')).toBeVisible();

    // Go to previous month
    await page.getByRole('button', { name: 'Previous month' }).click();
    await expect(page.getByText('January 2026')).toBeVisible();
    await expect(page.getByText('February 2026')).toBeHidden();

    // Go forward two months to March
    await page.getByRole('button', { name: 'Next month' }).click();
    await expect(page.getByText('February 2026')).toBeVisible();

    await page.getByRole('button', { name: 'Next month' }).click();
    await expect(page.getByText('March 2026')).toBeVisible();

    // Go back to February
    await page.getByRole('button', { name: 'Previous month' }).click();
    await expect(page.getByText('February 2026')).toBeVisible();
  });

  test('should support like and bookmark interactions on selected date articles', async ({
    page,
  }) => {
    // Select a date with articles
    const dateButton = page.getByRole('button', {
      name: /2026-02-16, 10 articles/,
    });
    await dateButton.click();

    // Wait for articles to load
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();

    // Find Like and Bookmark buttons - there are multiple article cards
    const likeButtons = page.getByRole('button', { name: 'Like' });
    const bookmarkButtons = page.getByRole('button', { name: 'Bookmark' });

    // Both types of interaction buttons should be present
    await expect(likeButtons.first()).toBeVisible();
    await expect(bookmarkButtons.first()).toBeVisible();

    // Article ID 2 ("Building Reliable AI Agents...") starts with is_liked: false
    // Find the article card via the title link's parent
    const secondArticleCard = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const likeButtonInCard = secondArticleCard.getByRole('button', {
      name: 'Like',
    });

    // Click Like - should toggle the like state
    await likeButtonInCard.click();

    // After liking, the button should have the active style (indigo text)
    await expect(likeButtonInCard).toHaveClass(/text-indigo-600/);

    // Click again to unlike
    await likeButtonInCard.click();
    await expect(likeButtonInCard).toHaveClass(/text-gray-400/);
  });

  test('should show prompt text when no date is selected', async ({
    page,
  }) => {
    // Before selecting any date, a prompt should be visible
    await expect(
      page.getByText('Select a date to view its newsletter.'),
    ).toBeVisible();
  });

  test('should show dates with edition badges in calendar', async ({
    page,
  }) => {
    // Dates with editions should show article count badges
    // Date 16 has 10 articles, date 10 has 6 articles
    const date16 = page.getByRole('button', {
      name: /2026-02-16, 10 articles/,
    });
    const date10 = page.getByRole('button', {
      name: /2026-02-10, 6 articles/,
    });

    await expect(date16).toBeEnabled();
    await expect(date10).toBeEnabled();

    // Dates without editions should be disabled
    const date01 = page.getByRole('button', {
      name: /2026-02-01, no newsletter/,
    });
    await expect(date01).toBeDisabled();
  });

  test('should persist view mode when switching between calendar and list', async ({
    page,
  }) => {
    // Start in calendar view - select a date
    await page
      .getByRole('button', { name: /2026-02-16, 10 articles/ })
      .click();
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();

    // Switch to list view - articles should still be visible
    await page.getByRole('button', { name: 'List' }).click();

    // The selected edition should be highlighted in list view
    const selectedEdition = page.getByRole('button', {
      name: /Feb 16, 2026/,
    });
    await expect(selectedEdition).toHaveClass(/border-blue-300/);

    // Articles from the selected date should still be loaded
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();

    // Switch back to calendar view
    await page.getByRole('button', { name: 'Calendar' }).click();
    await expect(page.getByText('February 2026')).toBeVisible();

    // Articles should still be displayed
    await expect(
      page.getByText('GPT-5 Launch Imminent: Key Changes to Expect'),
    ).toBeVisible();
  });
});
