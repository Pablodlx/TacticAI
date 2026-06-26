#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}
REGION=${GCP_REGION:-europe-west1}
REPO=${ARTIFACT_REPO:-tacticeye}
SERVICE=${CLOUD_RUN_SERVICE:-tacticeye2-web}
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/web:latest"

gcloud config set project "${PROJECT_ID}"
# Cloud Build ya hace el deploy en Step #2 de cloudbuild.yaml.
# No repetir gcloud run deploy aquí — machaca las env vars del servicio.
gcloud builds submit --config deploy/cloudbuild.yaml --substitutions _REGION="${REGION}",_REPO="${REPO}",_SERVICE="${SERVICE}"

