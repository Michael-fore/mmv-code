---
description: Run any MMV data pipeline job in the cloud (Cloud Run Job) instead of locally
---

# Run a Pipeline Job in the Cloud

Use this whenever a data pipeline is too long to run locally (shapefiles, full county backfills, etc.).

// turbo-all

## Prerequisites

Make sure GCP auth is set up:

```bash
# See /gcp-auth workflow if this fails
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud auth list
```

And Docker is authenticated to Artifact Registry:

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## Step 1 — Build and push the image

```bash
cd /Users/tako/projects/ai-playground/MMV/mmv-data
CLOUDSDK_CONFIG=/tmp/mmv_gcloud ./deploy/deploy.sh
```

This builds the image from `mmv-data/Dockerfile`, tags it with the current git SHA, pushes to Artifact Registry, and updates the Cloud Run Job definition.

---

## Step 2 — Execute a job

### Parcel geometry load (most common long-running job)

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud run jobs execute mmv-backfill \
  --region=us-central1 \
  --update-env-vars="BACKFILL_STATE=TX,BACKFILL_COUNTY=harris,JOB_SOURCE=parcels" \
  --project=mmv-cloud
```

Optional: limit rows for a test run:
```bash
  --update-env-vars="BACKFILL_STATE=TX,BACKFILL_COUNTY=harris,JOB_SOURCE=parcels,PARCEL_MAX=50000"
```

### CAD property backfill

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud run jobs execute mmv-backfill \
  --region=us-central1 \
  --update-env-vars="BACKFILL_STATE=TX,BACKFILL_COUNTY=harris,JOB_SOURCE=cad" \
  --project=mmv-cloud
```

### Census / FRED / USDA data

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud run jobs execute mmv-backfill \
  --region=us-central1 \
  --update-env-vars="BACKFILL_STATE=TX,JOB_SOURCE=census" \
  --project=mmv-cloud
```

Valid `JOB_SOURCE` values: `cad`, `fema`, `parcels`, `census`, `fred`, `usda`, `deeds`

### All sources (full orchestrated backfill)

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud run jobs execute mmv-backfill \
  --region=us-central1 \
  --update-env-vars="BACKFILL_STATE=TX,BACKFILL_COUNTY=harris" \
  --project=mmv-cloud
```

---

## Step 3 — Monitor progress

Stream logs in real time:

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mmv-backfill" \
  --project=mmv-cloud \
  --format="value(textPayload)" \
  --freshness=1h \
  --limit=200
```

Or watch in Cloud Console:
```
https://console.cloud.google.com/run/jobs/details/us-central1/mmv-backfill/executions?project=mmv-cloud
```

---

## Key Config

| Setting | Value |
|---|---|
| Job name | `mmv-backfill` |
| Region | `us-central1` |
| Project | `mmv-cloud` |
| Image | `us-central1-docker.pkg.dev/mmv-cloud/mmv/pipeline-runner` |
| Task timeout | 3600s (1hr) — increase in `deploy.sh` if needed |
| Memory | 1Gi (bump to 2Gi for parcel loads) |
| DB auth | Cloud SQL Connector (no proxy needed in Cloud Run) |
| DB secret | `mmv-db-pass` from Secret Manager |

### Increasing memory for parcel loads

Parcel geometry jobs are memory-hungry. For full county loads, update the job:

```bash
CLOUDSDK_CONFIG=/tmp/mmv_gcloud gcloud run jobs update mmv-backfill \
  --memory=4Gi \
  --task-timeout=7200 \
  --region=us-central1 \
  --project=mmv-cloud
```

---

## Notes

- **No Cloud SQL proxy needed** — Cloud Run automatically connects via IAM to the Cloud SQL instance defined in `CLOUD_SQL_INSTANCE`
- **Retries** — job is set to `--max-retries=2`; each retry gets a fresh container
- **Dry run** — add `BACKFILL_DRY_RUN=true` to any `--update-env-vars` to preview without writing
- **Partial loads** — use `PARCEL_MAX=N` for parcel jobs to load only N records (good for testing)
