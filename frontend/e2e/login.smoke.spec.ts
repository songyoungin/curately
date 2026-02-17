import { test, expect } from '@playwright/test';

test.describe('Post-deploy login smoke', () => {
  test.skip(
    !process.env.PLAYWRIGHT_BASE_URL,
    'Set PLAYWRIGHT_BASE_URL to run deployed smoke tests.',
  );

  test('loads /login and redirects to Google OAuth authorize URL', async ({
    page,
    baseURL,
  }) => {
    if (!baseURL) {
      throw new Error('baseURL is required for login smoke test');
    }

    const frontendOrigin = new URL(baseURL).origin;

    await page.goto('/login', { waitUntil: 'domcontentloaded' });

    const googleSignInButton = page.getByRole('button', {
      name: 'Sign in with Google',
    });
    await expect(googleSignInButton).toBeVisible();

    const oauthAuthorizeRequestPromise = page.waitForRequest((request) => {
      if (request.method() !== 'GET') {
        return false;
      }

      const requestUrl = new URL(request.url());
      return requestUrl.pathname.endsWith('/auth/v1/authorize');
    });

    await googleSignInButton.click();

    const oauthAuthorizeRequest = await oauthAuthorizeRequestPromise;
    const oauthUrl = new URL(oauthAuthorizeRequest.url());

    expect(oauthUrl.searchParams.get('provider')).toBe('google');

    const redirectTo = oauthUrl.searchParams.get('redirect_to');
    expect(redirectTo).toBeTruthy();
    expect(new URL(redirectTo as string).origin).toBe(frontendOrigin);
  });
});
