#!/usr/bin/env bash
set -euo pipefail

# Post-deploy smoke test for frontend login flow.
#
# Usage:
#   FRONTEND_URL="https://curately-frontend.pages.dev" ./scripts/smoke_frontend_login_post_deploy.sh
#   ./scripts/smoke_frontend_login_post_deploy.sh "https://curately-frontend.pages.dev"
#
# If FRONTEND_URL is not provided, script falls back to:
#   https://<CF_PAGES_PROJECT>.pages.dev

FRONTEND_URL="${FRONTEND_URL:-${1:-}}"

if [[ -z "${FRONTEND_URL}" ]] && [[ -n "${CF_PAGES_PROJECT:-}" ]]; then
  FRONTEND_URL="https://${CF_PAGES_PROJECT}.pages.dev"
fi

if [[ -z "${FRONTEND_URL}" ]]; then
  echo "[smoke-frontend] ERROR: FRONTEND_URL is required (or set CF_PAGES_PROJECT)." >&2
  echo "[smoke-frontend] Example: FRONTEND_URL=https://curately-frontend.pages.dev ./scripts/smoke_frontend_login_post_deploy.sh" >&2
  exit 1
fi

FRONTEND_URL="${FRONTEND_URL%/}"

echo "[smoke-frontend] Target frontend: ${FRONTEND_URL}"
echo "[smoke-frontend] Running Playwright login smoke test..."

pushd frontend >/dev/null
PLAYWRIGHT_BASE_URL="${FRONTEND_URL}" npx playwright test e2e/login.smoke.spec.ts --project=chromium
popd >/dev/null

echo "[smoke-frontend] SUCCESS: frontend login smoke test passed."
