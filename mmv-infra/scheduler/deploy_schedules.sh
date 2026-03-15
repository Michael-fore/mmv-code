#!/usr/bin/env bash
# deploy_schedules.sh — Create Cloud Scheduler jobs for MMV data fetchers.
#
# Prerequisites:
#   - gcloud CLI authenticated with a project that has Cloud Scheduler enabled
#   - Cloud Functions already deployed (see deploy_functions.sh)
#   - Service account with roles/cloudfunctions.invoker
#
# Usage:
#   ./deploy_schedules.sh [--project PROJECT_ID] [--region REGION] [--sa SERVICE_ACCOUNT_EMAIL]

set -euo pipefail

PROJECT="${PROJECT:-mmv-cloud}"
REGION="${REGION:-us-central1}"
SA_EMAIL="${SA_EMAIL:-scheduler-invoker@${PROJECT}.iam.gserviceaccount.com}"
FUNCTIONS_BASE="https://${REGION}-${PROJECT}.cloudfunctions.net"

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)  PROJECT="$2";   shift 2 ;;
    --region)   REGION="$2";    shift 2 ;;
    --sa)       SA_EMAIL="$2";  shift 2 ;;
    *)          echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

create_job() {
  local name="$1"
  local schedule="$2"
  local uri="$3"
  local body="${4:-{}}"
  local description="${5:-}"
  local tz="${6:-America/Chicago}"

  echo "Creating scheduler job: ${name}"

  # Delete existing job if present (idempotent redeploy)
  gcloud scheduler jobs delete "${name}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --quiet 2>/dev/null || true

  gcloud scheduler jobs create http "${name}" \
    --project="${PROJECT}" \
    --location="${REGION}" \
    --schedule="${schedule}" \
    --time-zone="${tz}" \
    --uri="${uri}" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body="${body}" \
    --oidc-service-account-email="${SA_EMAIL}" \
    --description="${description}" \
    --attempt-deadline=600s
}

# ── Daily ────────────────────────────────────────────────────────────────
# GraphCast: 10-day weather forecasts refresh daily
create_job "fetch-graphcast-forecast" \
  "0 6 * * *" \
  "${FUNCTIONS_BASE}/fetch-graphcast" \
  '{"mode":"forecast"}' \
  "Daily GraphCast 10-day weather forecast"

# ── Weekly ───────────────────────────────────────────────────────────────
# Drought Monitor: published every Thursday, fetch Friday morning
create_job "fetch-drought-monitor" \
  "0 7 * * 5" \
  "${FUNCTIONS_BASE}/fetch-drought" \
  '{}' \
  "Weekly US Drought Monitor update (published Thu, fetched Fri)"

# FRED interest rates: updated monthly but check weekly for revisions
create_job "fetch-fred-interest-rates" \
  "0 8 * * 1" \
  "${FUNCTIONS_BASE}/fetch-fred" \
  '{"series_id":"DGS10"}' \
  "Weekly FRED 10-Year Treasury rate"

create_job "fetch-fred-farm-income" \
  "30 8 * * 1" \
  "${FUNCTIONS_BASE}/fetch-fred" \
  '{"series_id":"B1411C0A052NBEA"}' \
  "Weekly FRED farm income series"

# ── Monthly ──────────────────────────────────────────────────────────────
# USDA NASS land values & cash rents: annual data, check monthly
create_job "fetch-usda-land-values" \
  "0 6 1 * *" \
  "${FUNCTIONS_BASE}/fetch-usda" \
  '{"metric":"land_values"}' \
  "Monthly check for USDA NASS land values (annual source)"

create_job "fetch-usda-cash-rents" \
  "30 6 1 * *" \
  "${FUNCTIONS_BASE}/fetch-usda" \
  '{"metric":"cash_rents"}' \
  "Monthly check for USDA NASS cash rents (annual source)"

# Crop production: annual survey data, check monthly
create_job "fetch-crop-production" \
  "0 7 1 * *" \
  "${FUNCTIONS_BASE}/fetch-crop-production" \
  '{}' \
  "Monthly check for USDA crop production data (annual source)"

# SSURGO soil data: archival, check monthly for corrections
create_job "fetch-ssurgo-soils" \
  "0 9 1 * *" \
  "${FUNCTIONS_BASE}/fetch-ssurgo" \
  '{}' \
  "Monthly check for SSURGO soil survey updates (archival source)"

# ── Quarterly ────────────────────────────────────────────────────────────
# NOAA 30-year climate normals: static, check quarterly
create_job "fetch-noaa-climate-normals" \
  "0 6 1 1,4,7,10 *" \
  "${FUNCTIONS_BASE}/fetch-noaa" \
  '{}' \
  "Quarterly check for NOAA climate normals (decadal source)"

echo ""
echo "All scheduler jobs created successfully."
echo "Run 'gcloud scheduler jobs list --project=${PROJECT} --location=${REGION}' to verify."
