#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:?Set REGION}"
: "${IMAGE:?Set immutable IMAGE URI}"
: "${SERVICE_ACCOUNT:?Set runtime SERVICE_ACCOUNT email}"
: "${SQL_CONNECTION:?Set Cloud SQL instance connection name}"
: "${DATABASE_SECRET:?Set Secret Manager secret ID}"
: "${JOB_NAME:?Set migration JOB_NAME}"
gcloud run jobs deploy "$JOB_NAME" \
  --project "$PROJECT_ID" --region "$REGION" \
  --image "$IMAGE" \
  --service-account "$SERVICE_ACCOUNT" \
  --set-cloudsql-instances "$SQL_CONNECTION" \
  --set-secrets "DATABASE_URL=$DATABASE_SECRET:latest" \
  --command "python" --args "scripts/migrate.py" \
  --max-retries 0 \
  --task-timeout 600s
echo "Migration job deployed but NOT executed."
echo "Review its configuration, then run:"
echo "gcloud run jobs execute $JOB_NAME --project $PROJECT_ID --region $REGION --wait"
