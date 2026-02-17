#!/usr/bin/env bash
set -euo pipefail

# Configure Cloud Scheduler jobs for Curately pipeline triggers.
#
# Required environment variables:
# - GCP_PROJECT
# - GCP_REGION (Cloud Scheduler location, example: us-central1)
# - BACKEND_URL (Cloud Run service URL, example: https://curately-backend-abc.run.app)
# - PIPELINE_TRIGGER_TOKEN
#
# Optional environment variables:
# - DAILY_JOB_NAME (default: curately-daily-pipeline)
# - DAILY_SCHEDULE (default: 0 6 * * *)
# - WEEKLY_JOB_NAME (default: curately-weekly-rewind)
# - WEEKLY_SCHEDULE (default: 0 23 * * 0)
# - SCHEDULE_TIMEZONE (default: Asia/Seoul)
# - ENABLE_REQUIRED_APIS (default: true)

required_vars=(
  GCP_PROJECT
  GCP_REGION
  BACKEND_URL
  PIPELINE_TRIGGER_TOKEN
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: ${var_name}" >&2
    exit 1
  fi
done

DAILY_JOB_NAME="${DAILY_JOB_NAME:-curately-daily-pipeline}"
DAILY_SCHEDULE="${DAILY_SCHEDULE:-0 6 * * *}"
WEEKLY_JOB_NAME="${WEEKLY_JOB_NAME:-curately-weekly-rewind}"
WEEKLY_SCHEDULE="${WEEKLY_SCHEDULE:-0 23 * * 0}"
SCHEDULE_TIMEZONE="${SCHEDULE_TIMEZONE:-Asia/Seoul}"
ENABLE_REQUIRED_APIS="${ENABLE_REQUIRED_APIS:-true}"

if [[ "${ENABLE_REQUIRED_APIS}" == "true" ]]; then
  echo "Enabling Cloud Scheduler API..."
  gcloud services enable cloudscheduler.googleapis.com --project "${GCP_PROJECT}"
else
  echo "Skipping API enable step (ENABLE_REQUIRED_APIS=${ENABLE_REQUIRED_APIS})"
fi

upsert_job() {
  local job_name="$1"
  local schedule="$2"
  local uri="$3"

  if gcloud scheduler jobs describe "${job_name}" \
    --location "${GCP_REGION}" \
    --project "${GCP_PROJECT}" \
    >/dev/null 2>&1; then
    echo "Updating scheduler job: ${job_name}"
    gcloud scheduler jobs update http "${job_name}" \
      --location "${GCP_REGION}" \
      --project "${GCP_PROJECT}" \
      --schedule "${schedule}" \
      --time-zone "${SCHEDULE_TIMEZONE}" \
      --uri "${uri}" \
      --http-method POST \
      --update-headers "X-Pipeline-Token=${PIPELINE_TRIGGER_TOKEN}"
  else
    echo "Creating scheduler job: ${job_name}"
    gcloud scheduler jobs create http "${job_name}" \
      --location "${GCP_REGION}" \
      --project "${GCP_PROJECT}" \
      --schedule "${schedule}" \
      --time-zone "${SCHEDULE_TIMEZONE}" \
      --uri "${uri}" \
      --http-method POST \
      --headers "X-Pipeline-Token=${PIPELINE_TRIGGER_TOKEN}"
  fi
}

upsert_job "${DAILY_JOB_NAME}" "${DAILY_SCHEDULE}" "${BACKEND_URL}/api/pipeline/run"
upsert_job "${WEEKLY_JOB_NAME}" "${WEEKLY_SCHEDULE}" "${BACKEND_URL}/api/pipeline/rewind/run"

echo "Cloud Scheduler configuration complete."
