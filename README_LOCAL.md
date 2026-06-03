# TacticAI Local (Dual Architecture)

## 1) Run legacy local UI (backward compatible)
```bash
python app.py
```

## 2) Run new dual API locally (sync mode)
```bash
cp .env.example .env
export APP_ENV=local STORAGE_BACKEND=local QUEUE_BACKEND=sync
./scripts/run_local.sh
```

API:
- `POST /jobs/upload`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/results`
- `GET /health`

### Example
```bash
curl -F "file=@/path/video.mp4" http://localhost:8000/jobs/upload
curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"input_uri":"file:///abs/path.mp4"}'
```

## 3) Run local stack with docker-compose
```bash
cp .env.local.example .env
docker compose -f docker-compose.local.yml up --build
```

## Troubleshooting
- If DB fails in compose, verify `DATABASE_URL` points to `postgres` host.
- If model file is missing, set `MODEL_PATH` in `.env`.
- For fastest local test use `QUEUE_BACKEND=sync` (no worker required).

## Validación end-to-end

### 1) Inicializar DB local con Alembic
```bash
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
```

### 2) Levantar API dual
```bash
export APP_ENV=local STORAGE_BACKEND=local QUEUE_BACKEND=sync
./scripts/run_local.sh
```

### 3) Flujo completo (upload -> job -> resultado)
```bash
UPLOAD=$(curl -s -F "file=@/path/video.mp4" http://localhost:8000/jobs/upload)
INPUT_URI=$(echo "$UPLOAD" | python -c "import sys,json;print(json.load(sys.stdin)['input_uri'])")
JOB=$(curl -s -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d "{\"input_uri\":\"$INPUT_URI\"}")
JOB_ID=$(echo "$JOB" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
curl -s "http://localhost:8000/jobs/$JOB_ID"
curl -s "http://localhost:8000/jobs/$JOB_ID/results"
```

### 4) Ejecutar tests mínimos de integración
```bash
pytest -q tests/test_dual_api_integration.py tests/test_worker_pipeline_real_call.py
```

## CI (GitHub Actions)

Pipeline mínima en `.github/workflows/ci.yml` (push/PR a `main`):
- instala dependencias,
- inicializa DB local con Alembic (`./scripts/db_manage.sh init-local`),
- ejecuta tests mínimos de integración.

