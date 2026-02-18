import { test, expect } from '@playwright/test';

const DIGEST_HEADLINE =
  'AI 에이전트 혁신과 클라우드 인프라 진화가 개발 생태계를 재편';

test.describe('Digest Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/digest');
    await expect(page.getByRole('heading', { name: 'Daily Digest' })).toBeVisible();
    await expect(page.getByText(DIGEST_HEADLINE)).toBeVisible();
  });

  test('should display headline in indigo card', async ({ page }) => {
    const headlineCard = page.locator('div.rounded-xl.bg-indigo-50');

    await expect(headlineCard).toBeVisible();
    await expect(headlineCard.getByText(DIGEST_HEADLINE)).toBeVisible();
  });

  test('should display key takeaways as bullet list', async ({ page }) => {
    const takeawaySection = page.locator('section.rounded-xl.bg-amber-50');

    await expect(takeawaySection).toBeVisible();
    await expect(takeawaySection.getByRole('heading', { name: 'Key Takeaways' })).toBeVisible();
    await expect(takeawaySection.locator('li')).toHaveCount(4);
    await expect(
      takeawaySection.getByText(
        'GPT-5 출시 임박 — 멀티모달 기능 향상, API 가격 40% 인하 예정',
      ),
    ).toBeVisible();
  });

  test('should display thematic sections with theme badges', async ({ page }) => {
    const sections = [
      {
        theme: 'AI/ML',
        title: 'AI 에이전트와 LLM의 급격한 진화',
        bodySnippet: 'GPT-5 출시가 임박한 가운데',
      },
      {
        theme: 'DevOps',
        title: 'Kubernetes 생태계 진화와 인프라 도구 경쟁',
        bodySnippet: 'Kubernetes 1.33 출시로 사이드카 컨테이너 네이티브 지원',
      },
      {
        theme: 'Backend',
        title: '데이터베이스와 분산 시스템의 진보',
        bodySnippet: 'PostgreSQL 17이 병렬 쿼리 실행 30% 향상',
      },
    ];

    for (const section of sections) {
      const sectionCard = page.locator('section').filter({
        has: page.getByText(section.theme, { exact: true }),
        hasText: section.title,
      });

      await expect(sectionCard).toBeVisible();
      await expect(sectionCard.getByText(section.theme, { exact: true })).toBeVisible();
      await expect(sectionCard.getByRole('heading', { name: section.title })).toBeVisible();
      await expect(sectionCard.getByText(section.bodySnippet)).toBeVisible();
    }
  });

  test('should display connections section', async ({ page }) => {
    const connectionsSection = page.locator('section.rounded-xl.bg-gray-50');

    await expect(connectionsSection).toBeVisible();
    await expect(
      connectionsSection.getByRole('heading', { name: 'Connections' }),
    ).toBeVisible();
    await expect(
      connectionsSection.getByText('AI와 인프라 주제가 긴밀하게 연결되어 있습니다.'),
    ).toBeVisible();
  });

  test('should display article count link in each section', async ({ page }) => {
    await expect(page.getByRole('link', { name: '3 articles →' })).toHaveCount(2);
    await expect(page.getByRole('link', { name: '2 articles →' })).toHaveCount(1);
  });

  test('should navigate to Today page with article filter on section link click', async ({
    page,
  }) => {
    const aiSection = page.locator('section').filter({
      has: page.getByText('AI/ML', { exact: true }),
      hasText: 'AI 에이전트와 LLM의 급격한 진화',
    });

    await aiSection.getByRole('link', { name: '3 articles →' }).click();

    await expect(page).toHaveURL('/?articles=1,2,3');
    await expect(page.getByText('Showing 3 articles from Digest')).toBeVisible();
  });

  test('should show date navigation buttons', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Previous day' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Next day' })).toBeVisible();
  });

  test('should disable next-day button on today\'s date', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Next day' })).toBeDisabled();
  });

  test('should handle Generate button with loading state', async ({ page }) => {
    const generateButton = page.getByRole('button', { name: /regenerate digest/i });

    await expect(generateButton).toContainText('Regenerate');
    await generateButton.click();

    await expect(generateButton).toContainText('Generating...');
    await expect(generateButton).toBeDisabled();
    await expect(generateButton.locator('svg.animate-spin')).toBeVisible();
    await expect(generateButton).toContainText('Regenerate', { timeout: 7000 });
    await expect(generateButton).toBeEnabled();
  });

  test('should transition from loading skeleton to content', async ({ page }) => {
    await page.goto('/digest', { waitUntil: 'commit' });

    await expect(page.getByRole('heading', { name: 'Daily Digest' })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText(DIGEST_HEADLINE)).toBeVisible();
    await expect(page.locator('.animate-pulse')).toHaveCount(0);
  });
});
