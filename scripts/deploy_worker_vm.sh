#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}
ZONE=${GCP_ZONE:-europe-west1-b}
VM_NAME=${WORKER_VM_NAME:-tacticeye2-worker-gpu}
MACHINE_TYPE=${WORKER_MACHINE_TYPE:-n1-standard-8}
GPU_TYPE=${WORKER_GPU_TYPE:-nvidia-tesla-t4}
GPU_COUNT=${WORKER_GPU_COUNT:-1}

gcloud config set project "${PROJECT_ID}"
gcloud compute instances create "${VM_NAME}" \
  --zone "${ZONE}" \
  --machine-type "${MACHINE_TYPE}" \
  --accelerator "type=${GPU_TYPE},count=${GPU_COUNT}" \
  --maintenance-policy TERMINATE \
  --restart-on-failure \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud \
  --boot-disk-size 100GB \
  --metadata startup-script='#!/bin/bash
apt-get update
apt-get install -y docker.io git
usermod -aG docker $USER
'

echo "VM created. Install NVIDIA Container Toolkit and run Dockerfile.worker image."

