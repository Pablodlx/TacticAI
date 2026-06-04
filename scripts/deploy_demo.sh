#!/usr/bin/env bash
# Despliega TacticAI como un único servicio Cloud Run (coste 0 en reposo).
# Modo monolítico: QUEUE_BACKEND=sync, análisis en el mismo proceso web.
# Cloud Run escala a 0 cuando no hay peticiones → sin coste en reposo.
set -euo pipefail

PROJECT_ID=${GCP_PROJECT_ID:?Falta GCP_PROJECT_ID}
REGION=${GCP_REGION:-europe-west1}
REPO=${ARTIFACT_REPO:-tacticeye}
SERVICE=${DEMO_SERVICE:-tacticeye2-demo}

echo "Proyecto : $PROJECT_ID"
echo "Región   : $REGION"
echo "Servicio : $SERVICE"
echo ""

gcloud config set project "${PROJECT_ID}"

# 1. Habilitar APIs necesarias (idempotente)
echo "==> Habilitando APIs de GCP..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --quiet

# 2. Crear repositorio de Artifact Registry si no existe
echo "==> Creando repositorio Artifact Registry (si no existe)..."
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --quiet 2>/dev/null || true

# 3. Build + push + deploy vía Cloud Build
echo "==> Lanzando Cloud Build (build + deploy)..."
gcloud builds submit \
  --config cloudbuild-demo.yaml \
  --substitutions "_REGION=${REGION},_REPO=${REPO},_SERVICE=${SERVICE}" \
  .

echo ""
echo "✓ Despliegue completado."
echo ""
echo "URL del servicio:"
gcloud run services describe "${SERVICE}" \
  --region="${REGION}" \
  --format="value(status.url)"
