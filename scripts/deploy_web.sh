#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}
REGION=${GCP_REGION:-europe-west1}
REPO=${ARTIFACT_REPO:-tacticeye2}
SERVICE=${CLOUD_RUN_SERVICE:-tacticeye2-web}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/web:latest"

gcloud config set project "${PROJECT_ID}"
gcloud builds submit --config cloudbuild.yaml --substitutions _REGION="${REGION}",_REPO="${REPO}",_SERVICE="${SERVICE}"
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --set-env-vars APP_ENV=cloud,STORAGE_BACKEND=gcs,QUEUE_BACKEND=pubsub

