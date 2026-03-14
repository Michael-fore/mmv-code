---
description: Authenticate to GCP before running any Google Cloud commands or SDK calls
---

# GCP Authentication

Before running any `gcloud` commands, deploying to GCP, or using any Google Cloud SDK/client library, always set the service account credentials:

// turbo
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/Users/tako/mmv-cloud-llm-agent-key.json
```

## Details

- **Project**: `mmv-cloud`
- **Service Account**: `llm-agent@mmv-cloud.iam.gserviceaccount.com`
- **Role**: `roles/owner`
- **Key File**: `/Users/tako/mmv-cloud-llm-agent-key.json`

## When to use

- Before any `gcloud` command
- Before deploying Cloud Functions, Cloud Run, etc.
- Before accessing GCS, BigQuery, or any GCP resource via Python SDK
- Before running Terraform or any IaC targeting GCP
