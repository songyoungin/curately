import { test, expect } from '@playwright/test';

test.describe('Feedback Loop - Cross-Page Interactions', () => {
  test('should show bookmarked article on Bookmarks page after bookmarking on Today', async ({
    page,
  }) => {
    // Prevent StrictMode double-toggle: only let the first bookmark POST through to MSW
    let bookmarkHandled = false;
    await page.route('**/api/articles/*/bookmark', async (route) => {
      if (!bookmarkHandled) {
        bookmarkHandled = true;
        await route.continue();
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            article_id: 2,
            type: 'bookmark',
            active: true,
            created_at: new Date().toISOString(),
          }),
        });
      }
    });

    // Go to Today page and wait for articles to load
    await page.goto('/');
    await expect(
      page.getByRole('link', { name: 'Building Reliable AI Agents with Tool Use' }),
    ).toBeVisible();

    // Find article 2 card (unbookmarked initially) via the title link's parent
    const articleCard = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const bookmarkButton = articleCard.getByRole('button', {
      name: 'Bookmark',
    });

    // Verify it starts as unbookmarked (gray)
    await expect(bookmarkButton).toHaveClass(/text-gray-400/);

    // Click to bookmark
    await bookmarkButton.click();

    // Verify it shows as bookmarked (amber)
    await expect(bookmarkButton).toHaveClass(/text-amber-500/);
    await expect(bookmarkButton).toHaveClass(/bg-amber-50/);

    // Allow the POST to complete before navigating
    await page.waitForLoadState('networkidle');

    // Navigate to Bookmarks page
    await page.getByRole('link', { name: /bookmark/i }).click();
    await expect(page).toHaveURL('/bookmarks');
    await expect(
      page.getByRole('heading', { name: 'Bookmarks' }),
    ).toBeVisible();

    // Verify the newly bookmarked article appears on the Bookmarks page
    await expect(
      page.getByText('Building Reliable AI Agents with Tool Use'),
    ).toBeVisible();

    // Original bookmarked articles should also still be present
    await expect(
      page.getByText('Kubernetes 1.33 Release: What You Need to Know'),
    ).toBeVisible();
    await expect(
      page.getByText('PostgreSQL 17: Performance Improvements Deep Dive'),
    ).toBeVisible();
  });

  test('should persist like state when navigating away and back to Today', async ({
    page,
  }) => {
    // Go to Today page and wait for articles to load
    await page.goto('/');
    await expect(
      page.getByRole('link', { name: 'Building Reliable AI Agents with Tool Use' }),
    ).toBeVisible();

    // Find article 2 card (unliked initially)
    const articleCard = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const likeButton = articleCard.getByRole('button', { name: 'Like' });

    // Verify it starts as unliked (gray)
    await expect(likeButton).toHaveClass(/text-gray-400/);

    // Click to like
    await likeButton.click();

    // Verify it shows as liked (indigo)
    await expect(likeButton).toHaveClass(/text-indigo-600/);
    await expect(likeButton).toHaveClass(/bg-indigo-50/);

    // Navigate to Bookmarks page
    await page.getByRole('link', { name: /bookmark/i }).click();
    await expect(page).toHaveURL('/bookmarks');
    await expect(
      page.getByRole('heading', { name: 'Bookmarks' }),
    ).toBeVisible();

    // Navigate back to Today page
    await page.getByRole('link', { name: /today/i }).click();
    await expect(page).toHaveURL('/');
    await expect(
      page.getByRole('link', { name: 'Building Reliable AI Agents with Tool Use' }),
    ).toBeVisible();

    // Re-locate article card (DOM is rebuilt after navigation)
    const articleCardAfterNav = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const likeButtonAfterNav = articleCardAfterNav.getByRole('button', {
      name: 'Like',
    });

    // Verify the like state persisted (still indigo)
    await expect(likeButtonAfterNav).toHaveClass(/text-indigo-600/);
    await expect(likeButtonAfterNav).toHaveClass(/bg-indigo-50/);
  });

  test('should reflect removed bookmark on Today page after unbookmarking on Bookmarks page', async ({
    page,
  }) => {
    // Prevent StrictMode double-toggle: only let the first bookmark POST through to MSW
    let unbookmarkHandled = false;
    await page.route('**/api/articles/*/bookmark', async (route) => {
      if (!unbookmarkHandled) {
        unbookmarkHandled = true;
        await route.continue();
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            article_id: 5,
            type: 'bookmark',
            active: false,
            created_at: null,
          }),
        });
      }
    });

    // Go to Bookmarks page first
    await page.goto('/bookmarks');
    await expect(
      page.getByRole('heading', { name: 'Bookmarks' }),
    ).toBeVisible();

    // Verify both bookmarked articles are shown
    await expect(
      page.getByText('Kubernetes 1.33 Release: What You Need to Know'),
    ).toBeVisible();
    await expect(
      page.getByText('PostgreSQL 17: Performance Improvements Deep Dive'),
    ).toBeVisible();

    // Find the "Remove bookmark" button for Kubernetes article (first one)
    const removeButtons = page.getByRole('button', {
      name: 'Remove bookmark',
    });
    await expect(removeButtons).toHaveCount(2);

    // Remove bookmark from the first article (Kubernetes 1.33)
    await removeButtons.first().click();

    // Verify Kubernetes article is removed from Bookmarks
    await expect(
      page.getByText('Kubernetes 1.33 Release: What You Need to Know'),
    ).not.toBeVisible();

    // Allow the POST to complete before navigating
    await page.waitForLoadState('networkidle');

    // Navigate to Today page
    await page.getByRole('link', { name: /today/i }).click();
    await expect(page).toHaveURL('/');
    await expect(
      page.getByRole('link', {
        name: 'Kubernetes 1.33 Release: What You Need to Know',
      }),
    ).toBeVisible();

    // Find the Kubernetes article card on Today page
    const k8sCard = page
      .getByRole('link', {
        name: 'Kubernetes 1.33 Release: What You Need to Know',
      })
      .locator('..');

    const bookmarkButton = k8sCard.getByRole('button', { name: 'Bookmark' });

    // Verify it now shows as unbookmarked (gray, not amber)
    await expect(bookmarkButton).toHaveClass(/text-gray-400/);
    await expect(bookmarkButton).not.toHaveClass(
      /(^|\s)text-amber-500(\s|$)/,
    );
    await expect(bookmarkButton).not.toHaveClass(/(^|\s)bg-amber-50(\s|$)/);
  });
});
