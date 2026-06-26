#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}
REGION=${GCP_REGION:-europe-west1}
REPO=${ARTIFACT_REPO:-tacticeye}
SERVICE=${WORKER_SERVICE:-tacticeye2-worker}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/worker:latest"

gcloud config set project "${PROJECT_ID}"

# Build and push worker image via Cloud Build
gcloud builds submit \
  --config deploy/cloudbuild-worker.yaml \
  --substitutions "_REGION=${REGION},_REPO=${REPO}" \
  .

# Deploy worker as Cloud Run service (always-on, min 1 instance)
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --no-allow-unauthenticated \
  --min-instances 0 \
  --max-instances 3 \
  --memory 4Gi \
  --cpu 4 \
  --timeout 3600 \
  --concurrency 1
