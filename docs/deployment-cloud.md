# Cloud Deployment (Low Cost)

This guide deploys:

- Backend: Google Cloud Run (scale to zero)
- Scheduler: Google Cloud Scheduler
- Frontend: Cloudflare Pages

## 1) Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI authenticated
- Cloudflare account and API token (`wrangler` auth)
- Supabase project (already in use)

## 2) Deploy Backend (Cloud Run)

Set environment variables:

```bash
export GCP_PROJECT="your-gcp-project-id"
export GCP_REGION="us-central1"
export GEMINI_API_KEY="..."
export SUPABASE_URL="https://<project>.supabase.co"
export SUPABASE_PUBLISHABLE_KEY="..."
export SUPABASE_SECRET_KEY="..."
# Legacy fallback (migration window only)
export SUPABASE_ANON_KEY="..."
export SUPABASE_SERVICE_ROLE_KEY="..."
export SUPABASE_JWT_SECRET="..."
export CORS_ORIGINS="https://<your-pages-domain>"
export PIPELINE_TRIGGER_TOKEN="$(openssl rand -hex 32)"
```

Deploy:

```bash
./scripts/deploy_backend_cloud_run.sh
```

Get backend URL:

```bash
gcloud run services describe curately-backend \
  --region "${GCP_REGION}" \
  --project "${GCP_PROJECT}" \
  --format 'value(status.url)'
```

## 3) Configure Cloud Scheduler

Set backend URL:

```bash
export BACKEND_URL="https://<your-cloud-run-url>"
```

Create/update jobs:

```bash
./scripts/configure_cloud_scheduler.sh
```

Default jobs:

- Daily pipeline: `0 6 * * *` (UTC) -> `POST /api/pipeline/run`
- Weekly rewind: `0 23 * * 0` (UTC) -> `POST /api/pipeline/rewind/run`

## 4) Deploy Frontend (Cloudflare Pages)

Set deployment variables:

```bash
export CLOUDFLARE_ACCOUNT_ID="..."
export CF_PAGES_PROJECT="curately-frontend"
export VITE_API_BASE_URL="${BACKEND_URL}/api"
export VITE_SUPABASE_URL="${SUPABASE_URL}"
export VITE_SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY}"
# Legacy fallback (migration window only)
export VITE_SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY}"
```

Deploy:

```bash
./scripts/deploy_frontend_cloudflare_pages.sh
```

## 5) Post-Deploy Smoke Tests

GitHub Actions runs smoke tests immediately after a successful deploy.

- Backend workflow: `.github/workflows/deploy-backend.yml`
  - Runs `scripts/smoke_backend_post_deploy.sh`
  - Verifies `GET /api/health`, `GET /api/feeds`, `GET /api/newsletters?limit=1`
- Frontend workflow: `.github/workflows/deploy-frontend.yml`
  - Runs `scripts/smoke_frontend_login_post_deploy.sh`
  - Verifies `/login` load, `Sign in with Google` button visibility, and OAuth redirect URL shape
- If any smoke check fails, the workflow fails.

### Manual Smoke Commands

Run backend smoke manually:

```bash
BACKEND_URL="https://<your-cloud-run-url>" ./scripts/smoke_backend_post_deploy.sh
```

Run frontend login smoke manually:

```bash
FRONTEND_URL="https://<your-pages-domain>" ./scripts/smoke_frontend_login_post_deploy.sh
```

If `FRONTEND_URL` is not provided, the script falls back to `https://<CF_PAGES_PROJECT>.pages.dev`.

### Manual Workflow Dispatch

Trigger backend deploy + smoke:

```bash
gh workflow run deploy-backend.yml --ref <branch-or-main>
```

Trigger frontend deploy + smoke:

```bash
gh workflow run deploy-frontend.yml --ref <branch-or-main>
```

Check recent runs:

```bash
gh run list --workflow deploy-backend.yml --limit 5
gh run list --workflow deploy-frontend.yml --limit 5
```

## 6) Additional Verification

- Backend health quick check: `GET ${BACKEND_URL}/api/health`
- Daily pipeline manual trigger:

```bash
curl -X POST "${BACKEND_URL}/api/pipeline/run" \
  -H "X-Pipeline-Token: ${PIPELINE_TRIGGER_TOKEN}"
```

- Frontend loads and API calls succeed from Pages domain.

## Notes

- In Cloud Run, internal APScheduler is disabled via `ENABLE_INTERNAL_SCHEDULER=false`.
- Scheduler endpoints are protected by `PIPELINE_TRIGGER_TOKEN`.
- Update `CORS_ORIGINS` when frontend domain changes.
- Preferred key pair is publishable/secret; keep anon/service_role only as temporary fallback and remove before 2026 H2.
