#!/usr/bin/env bash
set -euo pipefail

# Post-deploy smoke test for backend public read endpoints.
#
# Usage:
#   BACKEND_URL="https://example.run.app" ./scripts/smoke_backend_post_deploy.sh
#   ./scripts/smoke_backend_post_deploy.sh "https://example.run.app"

BACKEND_URL="${BACKEND_URL:-${1:-}}"

if [[ -z "${BACKEND_URL}" ]]; then
  echo "[smoke-backend] ERROR: BACKEND_URL is required." >&2
  echo "[smoke-backend] Example: BACKEND_URL=https://curately-backend-xyz.run.app ./scripts/smoke_backend_post_deploy.sh" >&2
  exit 1
fi

BACKEND_URL="${BACKEND_URL%/}"

echo "[smoke-backend] Target backend: ${BACKEND_URL}"

tmp_files=()
cleanup() {
  if [[ "${#tmp_files[@]}" -gt 0 ]]; then
    rm -f "${tmp_files[@]}"
  fi
}
trap cleanup EXIT

fetch_200_json() {
  local path="$1"
  local output_file="$2"
  local url="${BACKEND_URL}${path}"

  echo "[smoke-backend] GET ${url}"

  local http_status
  http_status="$(curl \
    --silent \
    --show-error \
    --location \
    --write-out '%{http_code}' \
    --output "${output_file}" \
    "${url}" || true)"

  if [[ "${http_status}" != "200" ]]; then
    echo "[smoke-backend] FAIL: ${path} returned HTTP ${http_status} (expected 200)." >&2
    if [[ -s "${output_file}" ]]; then
      echo "[smoke-backend] Response body:"
      cat "${output_file}"
      echo
    fi
    return 1
  fi

  if ! python3 -m json.tool "${output_file}" >/dev/null 2>&1; then
    echo "[smoke-backend] FAIL: ${path} response is not valid JSON." >&2
    if [[ -s "${output_file}" ]]; then
      echo "[smoke-backend] Response body:"
      cat "${output_file}"
      echo
    fi
    return 1
  fi

  return 0
}

assert_health_payload() {
  local payload_file="$1"
  python3 - "${payload_file}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    payload = json.load(f)

if not isinstance(payload, dict):
    raise SystemExit("Health response must be a JSON object")

if payload.get("status") != "ok":
    raise SystemExit("Health response must contain status='ok'")
PY
}

assert_feeds_payload() {
  local payload_file="$1"
  python3 - "${payload_file}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    payload = json.load(f)

if not isinstance(payload, list):
    raise SystemExit("/api/feeds response must be a JSON array")
PY
}

assert_newsletters_payload() {
  local payload_file="$1"
  python3 - "${payload_file}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    payload = json.load(f)

if not isinstance(payload, list):
    raise SystemExit("/api/newsletters?limit=1 response must be a JSON array")

if len(payload) > 1:
    raise SystemExit("/api/newsletters?limit=1 returned more than 1 item")
PY
}

run_check() {
  local path="$1"
  local check_name="$2"
  local validator_fn="$3"
  local tmp_file

  tmp_file="$(mktemp)"
  tmp_files+=("${tmp_file}")

  if ! fetch_200_json "${path}" "${tmp_file}"; then
    return 1
  fi

  if ! "${validator_fn}" "${tmp_file}"; then
    echo "[smoke-backend] FAIL: ${check_name} payload validation failed." >&2
    echo "[smoke-backend] Response body:"
    cat "${tmp_file}"
    echo
    return 1
  fi

  echo "[smoke-backend] PASS: ${check_name}"
  return 0
}

failures=0

run_check "/api/health" "GET /api/health" "assert_health_payload" || failures=$((failures + 1))
run_check "/api/feeds" "GET /api/feeds" "assert_feeds_payload" || failures=$((failures + 1))
run_check "/api/newsletters?limit=1" "GET /api/newsletters?limit=1" "assert_newsletters_payload" || failures=$((failures + 1))

if [[ "${failures}" -gt 0 ]]; then
  echo "[smoke-backend] FAILED: ${failures} check(s) failed." >&2
  exit 1
fi

echo "[smoke-backend] SUCCESS: all backend smoke checks passed."
