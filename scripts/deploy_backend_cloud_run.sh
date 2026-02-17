#!/usr/bin/env bash
set -euo pipefail

# Deploy Curately backend to Google Cloud Run.
#
# Required environment variables:
# - GCP_PROJECT
# - GCP_REGION (example: us-central1)
# - GEMINI_API_KEY
# - SUPABASE_URL
# - SUPABASE_ANON_KEY
# - SUPABASE_SERVICE_ROLE_KEY
# - SUPABASE_JWT_SECRET
# - CORS_ORIGINS (comma-separated list, example: https://curately.pages.dev)
# - PIPELINE_TRIGGER_TOKEN
#
# Optional environment variables:
# - SERVICE_NAME (default: curately-backend)
# - ARTIFACT_REPO (default: curately)
# - IMAGE_TAG (default: latest)
# - ENABLE_REQUIRED_APIS (default: true)

required_vars=(
  GCP_PROJECT
  GCP_REGION
  GEMINI_API_KEY
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  SUPABASE_JWT_SECRET
  CORS_ORIGINS
  PIPELINE_TRIGGER_TOKEN
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: ${var_name}" >&2
    exit 1
  fi
done

SERVICE_NAME="${SERVICE_NAME:-curately-backend}"
ARTIFACT_REPO="${ARTIFACT_REPO:-curately}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
ENABLE_REQUIRED_APIS="${ENABLE_REQUIRED_APIS:-true}"

IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${ARTIFACT_REPO}/${SERVICE_NAME}:${IMAGE_TAG}"

if [[ "${ENABLE_REQUIRED_APIS}" == "true" ]]; then
  echo "Enabling required Google Cloud APIs..."
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project "${GCP_PROJECT}"
else
  echo "Skipping API enable step (ENABLE_REQUIRED_APIS=${ENABLE_REQUIRED_APIS})"
fi

echo "Ensuring Artifact Registry repository exists: ${ARTIFACT_REPO}"
if ! gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --location "${GCP_REGION}" \
  --project "${GCP_PROJECT}" \
  >/dev/null 2>&1; then
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --repository-format docker \
    --location "${GCP_REGION}" \
    --project "${GCP_PROJECT}"
fi

echo "Building backend image: ${IMAGE_URI}"
TEMP_DOCKERFILE="./Dockerfile"
cp backend/Dockerfile "${TEMP_DOCKERFILE}"
trap 'rm -f "${TEMP_DOCKERFILE}"' EXIT

gcloud builds submit --tag "${IMAGE_URI}" --project "${GCP_PROJECT}" .

echo "Deploying to Cloud Run service: ${SERVICE_NAME}"
ENV_FILE="$(mktemp)"
cat >"${ENV_FILE}" <<EOF
ENV: "prod"
ENABLE_INTERNAL_SCHEDULER: "false"
CORS_ORIGINS: "${CORS_ORIGINS}"
PIPELINE_TRIGGER_TOKEN: "${PIPELINE_TRIGGER_TOKEN}"
GEMINI_API_KEY: "${GEMINI_API_KEY}"
SUPABASE_URL: "${SUPABASE_URL}"
SUPABASE_ANON_KEY: "${SUPABASE_ANON_KEY}"
SUPABASE_SERVICE_ROLE_KEY: "${SUPABASE_SERVICE_ROLE_KEY}"
SUPABASE_JWT_SECRET: "${SUPABASE_JWT_SECRET}"
EOF

gcloud run deploy "${SERVICE_NAME}" \
  --project "${GCP_PROJECT}" \
  --region "${GCP_REGION}" \
  --image "${IMAGE_URI}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 2 \
  --env-vars-file "${ENV_FILE}"

rm -f "${ENV_FILE}"

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --region "${GCP_REGION}" \
  --project "${GCP_PROJECT}" \
  --format 'value(status.url)')"

echo "Backend deployed."
echo "Cloud Run URL: ${SERVICE_URL}"
