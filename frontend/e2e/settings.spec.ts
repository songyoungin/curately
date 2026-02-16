import { test, expect } from '@playwright/test';

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
    // Wait for the page heading and feed data to load
    await expect(
      page.getByRole('heading', { name: 'Settings' }),
    ).toBeVisible();
    // Wait for at least one feed name to confirm data is loaded (exact match to avoid URL substring)
    await expect(page.getByText('TechCrunch', { exact: true })).toBeVisible();
  });

  test('should display all 5 feeds with their names', async ({ page }) => {
    const feedNames = [
      'TechCrunch',
      'Hacker News',
      'Medium Engineering',
      'Dev.to',
      'Python Weekly',
    ];

    for (const name of feedNames) {
      await expect(page.getByText(name, { exact: true })).toBeVisible();
    }
  });

  test('should show Python Weekly as inactive with gray icon', async ({
    page,
  }) => {
    // Python Weekly is the only inactive feed, so there's exactly one "Activate feed" button
    // Use exact: true because "Activate feed" is a substring of "Deactivate feed"
    const activateButton = page.getByRole('button', {
      name: 'Activate feed',
      exact: true,
    });
    await expect(activateButton).toHaveCount(1);
    await expect(activateButton).toHaveClass(/bg-gray-300/);

    // The feed name text should have gray-400 color (inactive styling)
    const feedNameText = page
      .getByText('Python Weekly', { exact: true })
      .first();
    await expect(feedNameText).toHaveClass(/text-gray-400/);
  });

  test('should add a new feed successfully', async ({ page }) => {
    // Fill in the feed name and URL
    await page.getByPlaceholder('Feed name').fill('Test Feed');
    await page
      .getByPlaceholder('https://example.com/feed')
      .fill('https://test.com/feed');

    // Click the Add button
    await page.getByRole('button', { name: /add/i }).click();

    // Success message should appear
    await expect(
      page.getByText('Feed "Test Feed" added successfully'),
    ).toBeVisible();

    // The inputs should be cleared after successful add
    await expect(page.getByPlaceholder('Feed name')).toHaveValue('');
    await expect(
      page.getByPlaceholder('https://example.com/feed'),
    ).toHaveValue('');
  });

  test('should show URL validation error for invalid URL', async ({
    page,
  }) => {
    // Fill in a feed name and an invalid URL
    await page.getByPlaceholder('Feed name').fill('Bad');
    await page
      .getByPlaceholder('https://example.com/feed')
      .fill('not-a-url');

    // Validation error should appear
    await expect(
      page.getByText('Please enter a valid URL (http:// or https://)'),
    ).toBeVisible();

    // The Add button should be disabled
    await expect(page.getByRole('button', { name: /add/i })).toBeDisabled();
  });

  test('should delete a feed with two-click confirmation', async ({
    page,
  }) => {
    // Find the Dev.to delete button by locating the feed name, navigating up to the row,
    // then finding the delete button within the row
    const devtoName = page.getByText('Dev.to', { exact: true });
    // Go up to the feed row: p (name) -> div (name container) -> div (left side) -> div (row)
    const devtoRow = devtoName.locator('xpath=ancestor::div[contains(@class, "justify-between")]');

    // First click: enters confirm state
    const deleteButton = devtoRow.getByRole('button', { name: 'Delete feed' });
    await deleteButton.click();

    // Button should now be in confirm state (red background, label changed)
    const confirmButton = devtoRow.getByRole('button', {
      name: 'Click again to confirm delete',
    });
    await expect(confirmButton).toBeVisible();
    await expect(confirmButton).toHaveClass(/bg-red-100/);

    // Second click: actually deletes
    await confirmButton.click();

    // Dev.to feed should be removed from the list
    await expect(
      page.getByText('Dev.to', { exact: true }),
    ).not.toBeVisible();
  });

  test('should toggle feed active state', async ({ page }) => {
    // Find TechCrunch feed row via the name text
    const techcrunchName = page.getByText('TechCrunch', { exact: true }).first();
    const techcrunchRow = techcrunchName.locator(
      'xpath=ancestor::div[contains(@class, "justify-between")]',
    );

    // Toggle should initially show active (blue background)
    const deactivateButton = techcrunchRow.getByRole('button', {
      name: 'Deactivate feed',
    });
    await expect(deactivateButton).toHaveClass(/bg-blue-600/);

    // Click to deactivate
    await deactivateButton.click();

    // Toggle should now show inactive (gray background)
    const activateButton = techcrunchRow.getByRole('button', {
      name: 'Activate feed',
    });
    await expect(activateButton).toHaveClass(/bg-gray-300/);

    // Click again to reactivate
    await activateButton.click();

    // Toggle should be back to active (blue background)
    await expect(
      techcrunchRow.getByRole('button', { name: 'Deactivate feed' }),
    ).toHaveClass(/bg-blue-600/);
  });

  test('should display all 8 interests', async ({ page }) => {
    const interestKeywords = [
      'machine-learning',
      'kubernetes',
      'python',
      'typescript',
      'react',
      'devops',
      'postgresql',
      'terraform',
    ];

    for (const keyword of interestKeywords) {
      await expect(page.getByText(keyword, { exact: true })).toBeVisible();
    }
  });

  test('should display correct interest weights and proportional bar widths', async ({
    page,
  }) => {
    // Verify weight values are displayed
    const weights = ['5.2', '3.8', '3.1', '2.5', '2.0', '1.8', '1.5', '1.0'];

    for (const weight of weights) {
      await expect(page.getByText(weight, { exact: true })).toBeVisible();
    }

    // Verify the top interest (machine-learning, 5.2) row has a bar
    const mlKeyword = page.getByText('machine-learning', { exact: true });
    const mlRow = mlKeyword.locator('xpath=ancestor::div[contains(@class, "flex") and contains(@class, "items-center") and contains(@class, "gap-3")]');
    const mlBar = mlRow.locator('[class*="bg-gradient-to-r"]');
    await expect(mlBar).toBeVisible();

    // Verify the lowest interest (terraform, 1.0) row has a bar
    const terraformKeyword = page.getByText('terraform', { exact: true });
    const terraformRow = terraformKeyword.locator('xpath=ancestor::div[contains(@class, "flex") and contains(@class, "items-center") and contains(@class, "gap-3")]');
    const terraformBar = terraformRow.locator('[class*="bg-gradient-to-r"]');
    await expect(terraformBar).toBeVisible();

    // The ML bar should be wider than the terraform bar
    // ML = 100% of max, terraform = (1.0/5.2)*100 ~= 19.2%
    const mlWidth = await mlBar.evaluate((el) => el.getBoundingClientRect().width);
    const terraformWidth = await terraformBar.evaluate(
      (el) => el.getBoundingClientRect().width,
    );
    expect(mlWidth).toBeGreaterThan(terraformWidth);
  });

  test('should display interest tip text', async ({ page }) => {
    await expect(
      page.getByText('Weights increase when you like related articles'),
    ).toBeVisible();
  });
});
