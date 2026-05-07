# TacticEYE2 on Google Cloud

## Architecture
- Web API on Cloud Run (`app_service.main`)
- Worker on GCE GPU VM (`worker/main.py`)
- Storage on GCS
- Queue on Pub/Sub
- DB on Cloud SQL PostgreSQL
- Images in Artifact Registry

## 1) Prepare resources
```bash
export GCP_PROJECT_ID=your-project
export GCP_REGION=europe-west1
export GCS_INPUT_BUCKET=your-input-bucket
export GCS_OUTPUT_BUCKET=your-output-bucket
export PUBSUB_TOPIC=tacticeye2-jobs
export PUBSUB_SUBSCRIPTION=tacticeye2-jobs-sub
./scripts/create_gcp_resources.sh
```

## 2) Build + deploy web (Cloud Run)
```bash
export ARTIFACT_REPO=tacticeye2
export CLOUD_RUN_SERVICE=tacticeye2-web
./scripts/deploy_web.sh
```

## 3) Provision worker VM (GPU)
```bash
export GCP_ZONE=europe-west1-b
./scripts/deploy_worker_vm.sh
```

Then SSH to VM, install NVIDIA drivers + NVIDIA Container Toolkit, run `Dockerfile.worker`.

## 4) Cloud SQL ready
Use:
`DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE`

Grant service account roles:
- `roles/storage.objectAdmin`
- `roles/pubsub.publisher`
- `roles/pubsub.subscriber`
- `roles/cloudsql.client`

## End-to-end test
1. Upload video to `/jobs/upload`
2. Create `/jobs`
3. Check `/jobs/{job_id}` until `completed`
4. Read `/jobs/{job_id}/results`

## Troubleshooting
- Pub/Sub errors: verify topic/subscription names and service account IAM.
- Cloud SQL errors: validate Cloud SQL Auth Proxy/socket path.
- GCS permissions: verify bucket IAM and runtime identity.

## Primer despliegue mínimo

### 1) Variables base
```bash
export GCP_PROJECT_ID=your-project
export GCP_REGION=europe-west1
export GCP_ZONE=europe-west1-b
export GCS_INPUT_BUCKET=your-input-bucket
export GCS_OUTPUT_BUCKET=your-output-bucket
export PUBSUB_TOPIC=tacticeye2-jobs
export PUBSUB_SUBSCRIPTION=tacticeye2-jobs-sub
export ARTIFACT_REPO=tacticeye2
export CLOUD_RUN_SERVICE=tacticeye2-web
```

### 2) Crear recursos GCP
```bash
./scripts/create_gcp_resources.sh
```

### 3) Aplicar migraciones en Cloud SQL
```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE'
./scripts/db_manage.sh cloud-upgrade
```

### 4) Desplegar web en Cloud Run
```bash
./scripts/deploy_web.sh
```

### 5) Crear VM GPU para worker y arrancar worker
```bash
./scripts/deploy_worker_vm.sh
# luego en la VM:
# docker run --gpus all --env-file .env.cloud.example <worker-image> python worker/main.py
```

### 6) Smoke test
```bash
curl -X POST https://<cloud-run-url>/health
```

