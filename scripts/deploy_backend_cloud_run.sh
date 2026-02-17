#!/usr/bin/env bash
set -euo pipefail

# Deploy Curately backend to Google Cloud Run.
#
# Required environment variables:
# - GCP_PROJECT
# - GCP_REGION (example: us-central1)
# - GEMINI_API_KEY
# - SUPABASE_URL
# - SUPABASE_SECRET_KEY
# - SUPABASE_JWT_SECRET
# - CORS_ORIGINS (comma-separated list, example: https://curately.pages.dev)
# - PIPELINE_TRIGGER_TOKEN
#
# Optional environment variables:
# - SERVICE_NAME (default: curately-backend)
# - ARTIFACT_REPO (default: curately)
# - IMAGE_TAG (default: latest, deprecated in favor of IMAGE_TAGS)
# - IMAGE_TAGS (comma-separated tags, first tag is used for Cloud Run deploy)
# - ENABLE_REQUIRED_APIS (default: true)
# - BUILD_STRATEGY (default: cloudbuild, options: cloudbuild|local)
# - LOG_FORMAT (default: text, set to json for structured logging in production)

required_vars=(
  GCP_PROJECT
  GCP_REGION
  GEMINI_API_KEY
  SUPABASE_URL
  SUPABASE_SECRET_KEY
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
ENABLE_REQUIRED_APIS="${ENABLE_REQUIRED_APIS:-true}"
BUILD_STRATEGY="${BUILD_STRATEGY:-cloudbuild}"
LOG_FORMAT="${LOG_FORMAT:-text}"

contains_tag() {
  local needle="$1"
  shift
  local existing
  for existing in "$@"; do
    if [[ "${existing}" == "${needle}" ]]; then
      return 0
    fi
  done
  return 1
}

IMAGE_TAGS_RAW="${IMAGE_TAGS:-${IMAGE_TAG:-latest}}"
IFS=',' read -r -a _raw_tags <<< "${IMAGE_TAGS_RAW}"

IMAGE_TAG_LIST=()
for raw_tag in "${_raw_tags[@]}"; do
  tag="${raw_tag//[[:space:]]/}"
  if [[ -n "${tag}" ]] && ! contains_tag "${tag}" "${IMAGE_TAG_LIST[@]}"; then
    IMAGE_TAG_LIST+=("${tag}")
  fi
done

if [[ "${#IMAGE_TAG_LIST[@]}" -eq 0 ]]; then
  IMAGE_TAG_LIST=("latest")
fi

IMAGE_REPOSITORY="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${ARTIFACT_REPO}/${SERVICE_NAME}"
PRIMARY_IMAGE_URI="${IMAGE_REPOSITORY}:${IMAGE_TAG_LIST[0]}"
IMAGE_URIS=("${PRIMARY_IMAGE_URI}")
for ((i = 1; i < ${#IMAGE_TAG_LIST[@]}; i++)); do
  IMAGE_URIS+=("${IMAGE_REPOSITORY}:${IMAGE_TAG_LIST[$i]}")
done

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

echo "Building backend image: ${PRIMARY_IMAGE_URI}"
if [[ "${BUILD_STRATEGY}" == "local" ]]; then
  gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
  docker build -f backend/Dockerfile -t "${PRIMARY_IMAGE_URI}" .
  for image_uri in "${IMAGE_URIS[@]:1}"; do
    docker tag "${PRIMARY_IMAGE_URI}" "${image_uri}"
  done
  for image_uri in "${IMAGE_URIS[@]}"; do
    docker push "${image_uri}"
  done
else
  TEMP_DOCKERFILE="./Dockerfile"
  cp backend/Dockerfile "${TEMP_DOCKERFILE}"
  trap 'rm -f "${TEMP_DOCKERFILE}"' EXIT
  gcloud builds submit --tag "${PRIMARY_IMAGE_URI}" --project "${GCP_PROJECT}" .
  for image_uri in "${IMAGE_URIS[@]:1}"; do
    gcloud artifacts docker tags add "${PRIMARY_IMAGE_URI}" "${image_uri}" \
      --project "${GCP_PROJECT}" \
      --quiet
  done
fi

echo "Deploying to Cloud Run service: ${SERVICE_NAME}"
ENV_FILE="$(mktemp)"
cat >"${ENV_FILE}" <<EOF
ENV: "prod"
LOG_FORMAT: "${LOG_FORMAT}"
ENABLE_INTERNAL_SCHEDULER: "false"
CORS_ORIGINS: "${CORS_ORIGINS}"
PIPELINE_TRIGGER_TOKEN: "${PIPELINE_TRIGGER_TOKEN}"
GEMINI_API_KEY: "${GEMINI_API_KEY}"
SUPABASE_URL: "${SUPABASE_URL}"
SUPABASE_SECRET_KEY: "${SUPABASE_SECRET_KEY}"
SUPABASE_JWT_SECRET: "${SUPABASE_JWT_SECRET}"
EOF

gcloud run deploy "${SERVICE_NAME}" \
  --project "${GCP_PROJECT}" \
  --region "${GCP_REGION}" \
  --image "${PRIMARY_IMAGE_URI}" \
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
echo "Published image tags: ${IMAGE_TAG_LIST[*]}"
