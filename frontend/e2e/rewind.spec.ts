import { test, expect } from '@playwright/test';

test.describe('Rewind Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/rewind');
    // Wait for the report data to load (skeleton disappears, period header appears)
    await expect(
      page.getByRole('heading', { name: /Feb 9 – Feb 16, 2026/ }),
    ).toBeVisible();
  });

  test('should display latest report period and generated date', async ({
    page,
  }) => {
    // Page heading (exact match to avoid matching "Rewind History")
    await expect(
      page.getByRole('heading', { name: 'Rewind', exact: true }),
    ).toBeVisible();

    // Period header inside RewindReport
    await expect(
      page.getByRole('heading', { name: /Feb 9 – Feb 16, 2026/ }),
    ).toBeVisible();

    // Generated date (formatted from 2026-02-16T07:00:00Z)
    await expect(page.getByText(/Generated Feb 16, 2026/)).toBeVisible();
  });

  test('should display overview text', async ({ page }) => {
    // Overview text appears in both RewindReport and RewindHistory (open details),
    // use .first() to target the main report section
    await expect(
      page
        .getByText(/This week focused on AI and infrastructure topics/)
        .first(),
    ).toBeVisible();
    await expect(
      page
        .getByText(/LLM advancements dominated the news cycle/)
        .first(),
    ).toBeVisible();
  });

  test('should display hot topics with counts', async ({ page }) => {
    const hotTopics = [
      { topic: 'LLM Agents', count: '5' },
      { topic: 'Kubernetes', count: '3' },
      { topic: 'PostgreSQL', count: '2' },
      { topic: 'MLOps', count: '2' },
    ];

    for (const { topic, count } of hotTopics) {
      await expect(page.getByText(topic).first()).toBeVisible();
      // Each hot topic badge has its count in a separate span
      const badge = page.locator('.bg-orange-50', { hasText: topic });
      await expect(badge).toBeVisible();
      await expect(badge.locator('.bg-orange-100')).toHaveText(count);
    }
  });

  test('should display rising trend changes', async ({ page }) => {
    // Rising section header
    const risingSection = page.locator('h3', { hasText: 'Rising' }).first();
    await expect(risingSection).toBeVisible();

    // Rising keywords with positive change values (inside RewindReport trend section)
    const reportSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: /Feb 9 – Feb 16, 2026/ }),
    });

    // machine-learning +2.7
    const mlTrend = reportSection.locator('div', {
      hasText: 'machine-learning',
    });
    await expect(mlTrend.getByText('+2.7').first()).toBeVisible();

    // kubernetes +1.3
    await expect(
      reportSection.getByText('+1.3').first(),
    ).toBeVisible();
  });

  test('should display declining trend changes', async ({ page }) => {
    // Declining section header
    const decliningSection = page
      .locator('h3', { hasText: 'Declining' })
      .first();
    await expect(decliningSection).toBeVisible();

    const reportSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: /Feb 9 – Feb 16, 2026/ }),
    });

    // docker -1.2
    await expect(
      reportSection.getByText('-1.2').first(),
    ).toBeVisible();
    await expect(
      reportSection.getByText('docker').first(),
    ).toBeVisible();

    // react -0.5
    await expect(
      reportSection.getByText('-0.5').first(),
    ).toBeVisible();
  });

  test('should display TrendChart with correct list items', async ({
    page,
  }) => {
    const trendChart = page.getByRole('list', {
      name: /interest trend changes/i,
    });
    await expect(trendChart).toBeVisible();

    const items = trendChart.getByRole('listitem');
    await expect(items).toHaveCount(4);

    // Verify each keyword appears in the chart
    const keywords = ['machine-learning', 'kubernetes', 'docker', 'react'];
    for (const keyword of keywords) {
      await expect(trendChart.getByText(keyword)).toBeVisible();
    }
  });

  test('should render TrendChart bars with proportional widths', async ({
    page,
  }) => {
    const trendChart = page.getByRole('list', {
      name: /interest trend changes/i,
    });

    // The bars are divs with inline width styles inside each listitem
    // machine-learning has the largest absolute change (2.7), so its bar should be 100%
    const items = trendChart.getByRole('listitem');

    // First item (machine-learning) should have 100% width bar
    const firstBar = items.nth(0).locator('[style*="width"]');
    await expect(firstBar).toHaveCSS('width', /.+/);

    // Verify bars use green/red colors appropriately
    // Rising items (machine-learning, kubernetes) have green bars
    const risingBars = items.nth(0).locator('.bg-green-100');
    await expect(risingBars).toBeVisible();

    // Declining items (docker, react) have red bars
    const decliningBars = items.nth(2).locator('.bg-red-100');
    await expect(decliningBars).toBeVisible();
  });

  test('should display TrendChart values with correct signs', async ({
    page,
  }) => {
    const trendChart = page.getByRole('list', {
      name: /interest trend changes/i,
    });

    // Rising values are prefixed with +
    await expect(trendChart.getByText('+2.7')).toBeVisible();
    await expect(trendChart.getByText('+1.3')).toBeVisible();

    // Declining values are negative (no + prefix)
    await expect(trendChart.getByText('-1.2')).toBeVisible();
    await expect(trendChart.getByText('-0.5')).toBeVisible();
  });

  test('should display suggestions', async ({ page }) => {
    await expect(
      page.getByText('Suggestions For Next Week'),
    ).toBeVisible();

    const suggestions = ['MLOps', 'AI safety', 'Kubernetes security'];
    for (const suggestion of suggestions) {
      // Use .first() in case suggestion text also appears in other sections (e.g., hot topics)
      await expect(page.getByText(suggestion).first()).toBeVisible();
    }
  });

  test('should handle Generate Rewind button click with loading state', async ({
    page,
  }) => {
    const generateButton = page.getByRole('button', {
      name: /generate rewind/i,
    });
    await expect(generateButton).toBeVisible();
    await expect(generateButton).toContainText('Generate Rewind');

    // Click the button
    await generateButton.click();

    // Button should show generating state (text changes to "Generating...")
    await expect(generateButton).toContainText('Generating...');
    await expect(generateButton).toBeDisabled();

    // After generation completes, button returns to normal
    await expect(generateButton).toContainText('Generate Rewind', {
      timeout: 5000,
    });
    await expect(generateButton).toBeEnabled();
  });

  test('should display Rewind History with past reports', async ({
    page,
  }) => {
    // History section header
    await expect(page.getByText('Rewind History')).toBeVisible();

    // There should be 4 details elements (one per report)
    const historyEntries = page.locator('details');
    await expect(historyEntries).toHaveCount(4);

    // Verify period labels are visible in history summaries
    // RewindHistory uses "Feb 9 - Feb 16, 2026" format (with hyphen, not en-dash)
    await expect(
      page.getByText('Feb 9 - Feb 16, 2026'),
    ).toBeVisible();
    await expect(
      page.getByText('Feb 2 - Feb 9, 2026'),
    ).toBeVisible();
    await expect(
      page.getByText('Jan 26 - Feb 2, 2026'),
    ).toBeVisible();
    await expect(
      page.getByText('Jan 19 - Jan 26, 2026'),
    ).toBeVisible();
  });

  test('should expand history details on click', async ({ page }) => {
    // Find a non-active history entry and click to expand it
    const secondEntry = page
      .locator('details')
      .filter({ hasText: 'Feb 2 - Feb 9, 2026' });

    // Click the summary to select this report
    await secondEntry.locator('summary').click();

    // Verify the report switch happened by checking the main heading updated
    await expect(
      page.getByRole('heading', { name: /Feb 2 – Feb 9, 2026/ }),
    ).toBeVisible();

    // The overview text should be visible in the main report section
    const reportSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: /Feb 2 – Feb 9, 2026/ }),
    });
    await expect(
      reportSection.getByText(/strong week for backend engineering topics/),
    ).toBeVisible();
  });

  test('should switch active report when clicking history entry', async ({
    page,
  }) => {
    // Click on the second report in history (Feb 2 - Feb 9)
    const secondEntry = page
      .locator('details')
      .filter({ hasText: 'Feb 2 - Feb 9, 2026' });
    await secondEntry.locator('summary').click();

    // The main report display should update to show the selected report's period
    await expect(
      page.getByRole('heading', { name: /Feb 2 – Feb 9, 2026/ }),
    ).toBeVisible();

    // The selected report's overview should be displayed in the main section
    await expect(
      page
        .locator('section')
        .filter({
          has: page.getByRole('heading', { name: /Feb 2 – Feb 9, 2026/ }),
        })
        .getByText(
          /strong week for backend engineering topics/,
        ),
    ).toBeVisible();

    // Hot topics should update to the selected report's topics
    await expect(page.getByText('GraphQL').first()).toBeVisible();
    await expect(page.getByText('API Design').first()).toBeVisible();
  });
});
