#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}
REGION=${GCP_REGION:-europe-west1}
REPO=${ARTIFACT_REPO:-tacticeye2}
INPUT_BUCKET=${GCS_INPUT_BUCKET:?Set GCS_INPUT_BUCKET}
OUTPUT_BUCKET=${GCS_OUTPUT_BUCKET:?Set GCS_OUTPUT_BUCKET}
TOPIC=${PUBSUB_TOPIC:-tacticeye2-jobs}
SUBSCRIPTION=${PUBSUB_SUBSCRIPTION:-tacticeye2-jobs-sub}

gcloud config set project "${PROJECT_ID}"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com pubsub.googleapis.com sqladmin.googleapis.com compute.googleapis.com
gcloud artifacts repositories create "${REPO}" --repository-format=docker --location="${REGION}" || true
gsutil mb -l "${REGION}" "gs://${INPUT_BUCKET}" || true
gsutil mb -l "${REGION}" "gs://${OUTPUT_BUCKET}" || true
gcloud pubsub topics create "${TOPIC}" || true
gcloud pubsub subscriptions create "${SUBSCRIPTION}" --topic="${TOPIC}" || true

echo "Resources ready."

