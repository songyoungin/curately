import { test, expect } from '@playwright/test';

test.describe('Bookmarks Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/bookmarks');
    // Wait for the bookmarked articles to load
    await expect(
      page.getByRole('heading', { name: 'Bookmarks' }),
    ).toBeVisible();
  });

  test('should display bookmarks in most-recently-bookmarked order', async ({
    page,
  }) => {
    // With MSW mock sorting by descending ID, PostgreSQL (id=8) should appear before Kubernetes (id=5)
    const cards = page.locator('[data-testid="bookmark-card"]');
    await expect(cards).toHaveCount(2);

    const firstCardText = await cards.nth(0).textContent();
    const secondCardText = await cards.nth(1).textContent();
    expect(firstCardText).toContain('PostgreSQL');
    expect(secondCardText).toContain('Kubernetes');
  });

  test('should display bookmarked articles', async ({ page }) => {
    // Verify both bookmarked articles are visible
    await expect(
      page.getByText('Kubernetes 1.33 Release: What You Need to Know'),
    ).toBeVisible();
    await expect(
      page.getByText('PostgreSQL 17: Performance Improvements Deep Dive'),
    ).toBeVisible();
  });

  test('should show correct article count in header', async ({ page }) => {
    await expect(
      page.getByText('2 saved articles with detailed summaries'),
    ).toBeVisible();
  });

  test('should display detailed summary sections', async ({ page }) => {
    // Both articles have detailed summaries with Background, Key Takeaways, Keywords sections
    const backgroundLabels = page.getByText('Background', { exact: true });
    await expect(backgroundLabels).toHaveCount(2);

    const takeawaysLabels = page.getByText('Key Takeaways', { exact: true });
    await expect(takeawaysLabels).toHaveCount(2);

    const keywordsLabels = page.getByText('Keywords', { exact: true });
    await expect(keywordsLabels).toHaveCount(2);

    // Verify actual content within detailed summaries
    await expect(
      page.getByText(/Native sidecar container support/),
    ).toBeVisible();
    await expect(
      page.getByText(/Parallel query execution improved by 30%/),
    ).toBeVisible();
  });

  test('should display keywords as badges', async ({ page }) => {
    // Article 5 (Kubernetes 1.33) keywords: kubernetes, container, orchestration
    // Use .first() because keyword text may also appear in detailed summary sections
    await expect(page.getByText('kubernetes').first()).toBeVisible();
    await expect(page.getByText('container').first()).toBeVisible();
    await expect(page.getByText('orchestration').first()).toBeVisible();

    // Article 8 (PostgreSQL 17) keywords: postgresql, database, performance
    await expect(page.getByText('postgresql').first()).toBeVisible();
    await expect(page.getByText('database').first()).toBeVisible();
    await expect(page.getByText('performance').first()).toBeVisible();
  });

  test('should remove article when clicking remove bookmark button', async ({
    page,
  }) => {
    // Click the first "Remove bookmark" button (Kubernetes article)
    const removeButtons = page.getByRole('button', {
      name: 'Remove bookmark',
    });
    await expect(removeButtons).toHaveCount(2);
    await removeButtons.first().click();

    // The Kubernetes article should be removed
    await expect(
      page.getByText('Kubernetes 1.33 Release: What You Need to Know'),
    ).not.toBeVisible();

    // The PostgreSQL article should still be visible
    await expect(
      page.getByText('PostgreSQL 17: Performance Improvements Deep Dive'),
    ).toBeVisible();

    // Only one remove button should remain
    await expect(removeButtons).toHaveCount(1);
  });

  test('should update count after removing a bookmark', async ({ page }) => {
    // Initially 2 articles
    await expect(
      page.getByText('2 saved articles with detailed summaries'),
    ).toBeVisible();

    // Remove first bookmark
    const removeButtons = page.getByRole('button', {
      name: 'Remove bookmark',
    });
    await removeButtons.first().click();

    // Count should update to 1
    await expect(
      page.getByText('1 saved article with detailed summaries'),
    ).toBeVisible();
  });

  test('should show empty state after removing all bookmarks', async ({
    page,
  }) => {
    const removeButtons = page.getByRole('button', {
      name: 'Remove bookmark',
    });

    // Remove first bookmark
    await removeButtons.first().click();
    await expect(removeButtons).toHaveCount(1);

    // Remove second bookmark
    await removeButtons.first().click();

    // Empty state should be shown
    await expect(page.getByText('No bookmarks yet')).toBeVisible();
    await expect(
      page.getByText(
        'Bookmark articles from the Today page to save them here with detailed summaries.',
      ),
    ).toBeVisible();
  });

  test('should have correct external links for article titles', async ({
    page,
  }) => {
    // Article 5 (Kubernetes) should link to its source URL
    const k8sLink = page.getByRole('link', {
      name: /Kubernetes 1\.33 Release/,
    });
    await expect(k8sLink).toHaveAttribute(
      'href',
      'https://news.ycombinator.com/item?id=39023456',
    );
    await expect(k8sLink).toHaveAttribute('target', '_blank');

    // Article 8 (PostgreSQL) should link to its source URL
    const pgLink = page.getByRole('link', {
      name: /PostgreSQL 17: Performance/,
    });
    await expect(pgLink).toHaveAttribute(
      'href',
      'https://news.ycombinator.com/item?id=39034567',
    );
    await expect(pgLink).toHaveAttribute('target', '_blank');
  });
});
