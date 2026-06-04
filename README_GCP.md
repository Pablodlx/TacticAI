# TacticAI on Google Cloud

## Architecture

| Component | GCP Service |
|-----------|-------------|
| Web API | Cloud Run (auto-scale, CPU) |
| Worker | Cloud Run (CPU, min-instances=0) **or** GCE GPU VM |
| Storage | Cloud Storage (GCS) |
| Queue | Cloud Pub/Sub |
| Database | Cloud SQL (PostgreSQL) |
| Container registry | Artifact Registry |
| CI/CD | GitHub Actions → Cloud Build → Cloud Run |

> **Worker options:** Cloud Run is suitable for short/medium videos (timeout up to 3600 s). For full-match GPU analysis deploy the worker on a GCE VM with NVIDIA drivers instead.

---

## Prerequisites

```bash
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=europe-west1
export GCP_ZONE=europe-west1-b
export GCS_INPUT_BUCKET=tacticeye2-input
export GCS_OUTPUT_BUCKET=tacticeye2-output
export PUBSUB_TOPIC=tacticeye2-jobs
export PUBSUB_SUBSCRIPTION=tacticeye2-jobs-sub
export ARTIFACT_REPO=tacticeye2
export CLOUD_RUN_SERVICE=tacticeye2-web
export WORKER_SERVICE=tacticeye2-worker
```

---

## Step 1 — Create GCP resources

```bash
./scripts/create_gcp_resources.sh
```

Creates: GCS buckets, Pub/Sub topic + subscription, Artifact Registry repository.

---

## Step 2 — Apply DB migrations (Cloud SQL)

```bash
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE'
./scripts/db_manage.sh cloud-upgrade
```

Required IAM roles for the service account:
- `roles/storage.objectAdmin`
- `roles/pubsub.publisher`
- `roles/pubsub.subscriber`
- `roles/cloudsql.client`

---

## Step 3 — Deploy web API to Cloud Run

```bash
./scripts/deploy_web.sh
```

Builds `Dockerfile.web` via Cloud Build, pushes to Artifact Registry, deploys to Cloud Run. The web image does **not** include PyTorch — it only manages jobs and serves the UI.

---

## Step 4a — Deploy worker to Cloud Run (CPU / short jobs)

```bash
./scripts/deploy_worker_cloudrun.sh
```

- Builds `Dockerfile.worker` via `cloudbuild-worker.yaml`
- Deploys as a Cloud Run service (`--concurrency 1`, `--timeout 3600`, `--min-instances 0`, `--max-instances 3`)
- Suitable for clips up to ~30–60 min on CPU or small GPU Cloud Run instances

---

## Step 4b — Deploy worker on a GPU VM (full matches)

```bash
./scripts/deploy_worker_vm.sh
```

Provisions a GCE instance in `GCP_ZONE`. After SSH:

```bash
# Install NVIDIA drivers + NVIDIA Container Toolkit, then:
docker run --gpus all \
  --env-file .env.cloud.example \
  <REGION>-docker.pkg.dev/<PROJECT>/<REPO>/worker:latest \
  python worker/main.py
```

A mid-range GPU (RTX 3060 class) processes a 90-min match in ~135 min. An RTX 4090-class machine can approach real-time.

---

## Step 5 — Smoke test

```bash
SERVICE_URL=$(gcloud run services describe ${CLOUD_RUN_SERVICE} \
  --region ${GCP_REGION} --format 'value(status.url)')

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/health"
```

---

## End-to-end job flow

```bash
# 1. Upload video
UPLOAD=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@match.mp4" "${SERVICE_URL}/jobs/upload")
INPUT_URI=$(echo "$UPLOAD" | python -c "import sys,json;print(json.load(sys.stdin)['input_uri'])")

# 2. Create job
JOB=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -X POST "${SERVICE_URL}/jobs" \
  -H "Content-Type: application/json" \
  -d "{\"input_uri\":\"${INPUT_URI}\"}")
JOB_ID=$(echo "$JOB" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# 3. Poll until completed
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/jobs/${JOB_ID}"

# 4. Get results
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/jobs/${JOB_ID}/results"
```

---

## CI/CD pipeline

`cloudbuild.yaml` is triggered on pushes to `main` (after GitHub Actions CI passes):

```
git push → GitHub Actions (pytest -q tests/) → Cloud Build → Artifact Registry → gcloud run deploy
```

Worker image is built separately with `cloudbuild-worker.yaml`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Pub/Sub errors | Verify topic/subscription names match env vars; check service account has `pubsub.publisher` + `pubsub.subscriber` |
| Cloud SQL connection refused | Validate Cloud SQL Auth Proxy socket path in `DATABASE_URL` |
| GCS permission denied | Check bucket IAM and runtime service account identity |
| Worker timeout | For full matches use a GPU VM (`deploy_worker_vm.sh`); Cloud Run timeout max is 3600 s |
| Image not found | Run `./scripts/deploy_worker_cloudrun.sh` or `deploy_web.sh` to build and push first |
