import { test, expect } from '@playwright/test';

test.describe('Today Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for articles to load (skeleton disappears, real content appears)
    await expect(
      page.getByRole('heading', { name: 'Today' }),
    ).toBeVisible();
    // Wait for at least one article title link to appear (confirms data loaded)
    await expect(
      page.getByRole('link', { name: /GPT-5/ }),
    ).toBeVisible();
  });

  test('should display 10 articles across 4 category sections', async ({
    page,
  }) => {
    // DateHeader shows "10 articles"
    await expect(page.getByText('10 articles')).toBeVisible();

    // Verify all 10 article titles are rendered
    const articleTitles = [
      'GPT-5 Launch Imminent: Key Changes to Expect',
      'Building Reliable AI Agents with Tool Use',
      'Fine-tuning LLMs on Custom Datasets: A Practical Guide',
      'The State of MLOps in 2026',
      'Kubernetes 1.33 Release: What You Need to Know',
      'Terraform vs Pulumi: Infrastructure as Code Comparison',
      'GitOps Best Practices for Production Environments',
      'PostgreSQL 17: Performance Improvements Deep Dive',
      'Designing Rate Limiters for Distributed Systems',
      'React Server Components: Lessons from Production',
    ];

    for (const title of articleTitles) {
      await expect(page.getByRole('link', { name: title })).toBeVisible();
    }
  });

  test('should render articles as a flat score-sorted list', async ({ page }) => {
    const scoreTexts = await page.getByTestId('score-badge').allTextContents();
    const scores = scoreTexts.map((text) => Number(text));

    expect(scores.length).toBe(10);
    expect(scores).toEqual([...scores].sort((a, b) => b - a));
    await expect(page.getByRole('heading', { name: 'AI/ML' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Backend' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'DevOps' })).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Frontend' })).toHaveCount(0);
  });

  test('should show category badges on article cards', async ({ page }) => {
    const gptCard = page
      .getByRole('link', {
        name: 'GPT-5 Launch Imminent: Key Changes to Expect',
      })
      .locator('..');
    await expect(gptCard.getByTestId('category-badge')).toHaveText('AI/ML');

    const k8sCard = page
      .getByRole('link', {
        name: 'Kubernetes 1.33 Release: What You Need to Know',
      })
      .locator('..');
    await expect(k8sCard.getByTestId('category-badge')).toHaveText('DevOps');
  });

  test('should toggle like on an unliked article', async ({ page }) => {
    // Article 2 ("Building Reliable AI Agents") is not liked initially
    // Find the article title link, then go up to its parent card div
    const articleCard = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const likeButton = articleCard.getByRole('button', { name: 'Like' });

    // Initially gray (not liked)
    await expect(likeButton).toHaveClass(/text-gray-400/);

    // Click to like
    await likeButton.click();

    // Should now show indigo (liked)
    await expect(likeButton).toHaveClass(/text-indigo-600/);
    await expect(likeButton).toHaveClass(/bg-indigo-50/);

    // Click again to unlike
    await likeButton.click();

    // Should revert to gray
    await expect(likeButton).toHaveClass(/text-gray-400/);
  });

  test('should toggle bookmark on an unbookmarked article', async ({
    page,
  }) => {
    // Article 2 ("Building Reliable AI Agents") is not bookmarked initially
    const articleCard = page
      .getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      })
      .locator('..');

    const bookmarkButton = articleCard.getByRole('button', {
      name: 'Bookmark',
    });

    // Initially gray (not bookmarked)
    await expect(bookmarkButton).toHaveClass(/text-gray-400/);

    // Click to bookmark
    await bookmarkButton.click();

    // Should now show amber (bookmarked)
    await expect(bookmarkButton).toHaveClass(/text-amber-500/);
    await expect(bookmarkButton).toHaveClass(/bg-amber-50/);

    // Click again to remove bookmark
    await bookmarkButton.click();

    // Should revert to gray
    await expect(bookmarkButton).toHaveClass(/text-gray-400/);
  });

  test('should render article title links with target="_blank"', async ({
    page,
  }) => {
    // Check a few representative articles for external link attributes
    const gpt5Link = page.getByRole('link', {
      name: 'GPT-5 Launch Imminent: Key Changes to Expect',
    });
    await expect(gpt5Link).toHaveAttribute('target', '_blank');
    await expect(gpt5Link).toHaveAttribute('rel', 'noopener noreferrer');

    const k8sLink = page.getByRole('link', {
      name: 'Kubernetes 1.33 Release: What You Need to Know',
    });
    await expect(k8sLink).toHaveAttribute('target', '_blank');
    await expect(k8sLink).toHaveAttribute('rel', 'noopener noreferrer');

    const reactLink = page.getByRole('link', {
      name: 'React Server Components: Lessons from Production',
    });
    await expect(reactLink).toHaveAttribute('target', '_blank');
    await expect(reactLink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  test('should transition from loading skeleton to content', async ({
    page,
  }) => {
    // Navigate fresh to catch the loading state
    await page.goto('/', { waitUntil: 'commit' });

    // The page should eventually show real content (heading + articles)
    await expect(
      page.getByRole('heading', { name: 'Today' }),
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('10 articles')).toBeVisible();

    // Skeleton pulse elements should no longer be present once loaded
    const skeletons = page.locator('.animate-pulse');
    await expect(skeletons).toHaveCount(0);
  });

  test('should display article source feed and score badge', async ({
    page,
  }) => {
    // Article 1 (GPT-5) - source: TechCrunch, score: 0.95
    const gptCard = page
      .getByRole('link', {
        name: 'GPT-5 Launch Imminent: Key Changes to Expect',
      })
      .locator('..');

    await expect(gptCard.getByText('TechCrunch')).toBeVisible();
    await expect(gptCard.getByText('0.95')).toBeVisible();

    // Article 5 (Kubernetes) - source: Hacker News, score: 0.78
    const k8sCard = page
      .getByRole('link', {
        name: 'Kubernetes 1.33 Release: What You Need to Know',
      })
      .locator('..');

    await expect(k8sCard.getByText('Hacker News')).toBeVisible();
    await expect(k8sCard.getByText('0.78')).toBeVisible();

    // Article 10 (React Server Components) - source: Dev.to, score: 0.38
    const reactCard = page
      .getByRole('link', {
        name: 'React Server Components: Lessons from Production',
      })
      .locator('..');

    await expect(reactCard.getByText('Dev.to')).toBeVisible();
    await expect(reactCard.getByText('0.38')).toBeVisible();
  });

  test('should reflect pre-existing like and bookmark states', async ({
    page,
  }) => {
    // Article 1 (GPT-5): is_liked=true, is_bookmarked=false
    const gptCard = page
      .getByRole('link', {
        name: 'GPT-5 Launch Imminent: Key Changes to Expect',
      })
      .locator('..');

    const gptLike = gptCard.getByRole('button', { name: 'Like' });
    const gptBookmark = gptCard.getByRole('button', { name: 'Bookmark' });
    await expect(gptLike).toHaveClass(/text-indigo-600/);
    await expect(gptBookmark).toHaveClass(/text-gray-400/);

    // Article 8 (PostgreSQL 17): is_liked=true, is_bookmarked=true
    const pgCard = page
      .getByRole('link', {
        name: 'PostgreSQL 17: Performance Improvements Deep Dive',
      })
      .locator('..');

    const pgLike = pgCard.getByRole('button', { name: 'Like' });
    const pgBookmark = pgCard.getByRole('button', { name: 'Bookmark' });
    await expect(pgLike).toHaveClass(/text-indigo-600/);
    await expect(pgBookmark).toHaveClass(/text-amber-500/);

    // Article 5 (Kubernetes 1.33): is_liked=false, is_bookmarked=true
    const k8sCard = page
      .getByRole('link', {
        name: 'Kubernetes 1.33 Release: What You Need to Know',
      })
      .locator('..');

    const k8sLike = k8sCard.getByRole('button', { name: 'Like' });
    const k8sBookmark = k8sCard.getByRole('button', { name: 'Bookmark' });
    await expect(k8sLike).toHaveClass(/text-gray-400/);
    await expect(k8sBookmark).toHaveClass(/text-amber-500/);
  });

  test('should filter articles when ?articles= query param is present', async ({
    page,
  }) => {
    await page.goto('/?articles=1,2');

    await expect(page.getByText('Showing 2 articles from Digest')).toBeVisible();
    await expect(
      page.getByRole('link', {
        name: 'GPT-5 Launch Imminent: Key Changes to Expect',
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('link', {
        name: 'Building Reliable AI Agents with Tool Use',
      }),
    ).toBeVisible();
    await expect(
      page.getByRole('link', {
        name: 'Fine-tuning LLMs on Custom Datasets: A Practical Guide',
      }),
    ).toHaveCount(0);
    await expect(page.getByText('2 articles', { exact: true })).toBeVisible();

    await page.getByRole('button', { name: /show all/i }).click();
    await expect(page).toHaveURL('/');
    await expect(page.getByText('10 articles')).toBeVisible();
    await expect(
      page.getByRole('link', {
        name: 'Fine-tuning LLMs on Custom Datasets: A Practical Guide',
      }),
    ).toBeVisible();
  });
});
