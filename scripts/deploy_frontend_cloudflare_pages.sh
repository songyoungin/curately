#!/usr/bin/env bash
set -euo pipefail

# Build and deploy frontend to Cloudflare Pages.
#
# Required environment variables:
# - CLOUDFLARE_ACCOUNT_ID
# - CF_PAGES_PROJECT
# - VITE_API_BASE_URL (example: https://curately-backend-abc.run.app/api)
# - VITE_SUPABASE_URL
# - VITE_SUPABASE_ANON_KEY
#
# Optional environment variables:
# - CF_PAGES_BRANCH (default: main)

required_vars=(
  CLOUDFLARE_ACCOUNT_ID
  CF_PAGES_PROJECT
  VITE_API_BASE_URL
  VITE_SUPABASE_URL
  VITE_SUPABASE_ANON_KEY
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: ${var_name}" >&2
    exit 1
  fi
done

CF_PAGES_BRANCH="${CF_PAGES_BRANCH:-main}"

echo "Installing frontend dependencies..."
pushd frontend >/dev/null
npm ci

echo "Building frontend..."
VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
VITE_SUPABASE_URL="${VITE_SUPABASE_URL}" \
VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY}" \
npm run build
popd >/dev/null

echo "Deploying to Cloudflare Pages project: ${CF_PAGES_PROJECT}"
npx wrangler pages deploy frontend/dist \
  --project-name "${CF_PAGES_PROJECT}" \
  --branch "${CF_PAGES_BRANCH}"

echo "Frontend deployment complete."
