# TacticAI — Local development guide

Two modes are available locally:

| Mode | Entry point | Best for |
|------|------------|----------|
| **Legacy** | `python app.py` | Full local UI with live WebSocket streaming |
| **Dual API** | `./scripts/run_local.sh` | Jobs API, matches Cloud Run behaviour |

---

## Mode 1 — Legacy (monolithic WebSocket)

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:8001
```

Upload a video, set team names and batch duration, and the dashboard updates in near-real-time via WebSocket as each micro-batch completes (~4–5 s intervals).

Set `PORT` env var to override the default `8001`.

---

## Mode 2 — Dual API (jobs, sync queue)

```bash
cp .env.example .env
export APP_ENV=local
export STORAGE_BACKEND=local
export QUEUE_BACKEND=sync
export DATABASE_URL=sqlite:///./runtime_data/jobs.db

./scripts/db_manage.sh init-local
./scripts/run_local.sh
# Open http://localhost:8000
```

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/jobs/upload` | Upload a video file |
| `POST` | `/jobs` | Create analysis job from `input_uri` |
| `GET` | `/jobs/{job_id}` | Poll job status |
| `GET` | `/jobs/{job_id}/results` | Retrieve results |
| `GET` | `/health` | Health check |

### Quick example

```bash
# Upload
UPLOAD=$(curl -s -F "file=@/path/to/match.mp4" http://localhost:8000/jobs/upload)
INPUT_URI=$(echo "$UPLOAD" | python -c "import sys,json;print(json.load(sys.stdin)['input_uri'])")

# Create job
JOB=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d "{\"input_uri\":\"$INPUT_URI\"}")
JOB_ID=$(echo "$JOB" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# Poll
curl -s "http://localhost:8000/jobs/$JOB_ID"

# Results
curl -s "http://localhost:8000/jobs/$JOB_ID/results"
```

---

## Mode 3 — Full local stack with Docker Compose

```bash
cp .env.local.example .env
docker compose -f docker-compose.local.yml up --build
```

Starts: `web` (port 8000) + `worker` + `redis` + `postgres`.

Set `MODEL_PATH` in `.env` to the path of your YOLO weights inside the container.

---

## Database (Alembic)

```bash
export DATABASE_URL=sqlite:///./runtime_data/jobs.db

./scripts/db_manage.sh init-local   # wipe + init (first run)
./scripts/db_manage.sh upgrade      # apply pending migrations
./scripts/db_manage.sh migrate "description"  # generate new revision
```

For PostgreSQL replace the `DATABASE_URL` with your connection string.

---

## Running the worker separately

```bash
# Sync mode: worker runs inline with the API (no separate process needed)
export QUEUE_BACKEND=sync

# Redis mode: start worker in a separate terminal
export QUEUE_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0
python worker/main.py
# or
./scripts/run_worker_local.sh
```

---

## Running tests

```bash
pip install pytest pytest-asyncio httpx pytest-mock
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
pytest -q
```

88 tests across 11 files. All heavy modules (YOLO, GPU) are mocked so tests run without a GPU or model weights.

Run a specific subset:

```bash
pytest -q tests/test_prediction_engine.py tests/test_alerts.py
pytest -q tests/test_batch_processor.py tests/test_possession_tracker.py
```

---

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request to `main`, across **Python 3.11, 3.12, and 3.13**:

1. Install `requirements.txt` + pytest tooling
2. Init SQLite DB with Alembic
3. `pytest -q tests/` — all 88 tests must pass before a PR can be merged

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DB error on first run | Run `./scripts/db_manage.sh init-local` before starting the API |
| `postgres` host not found in compose | Check `DATABASE_URL` uses `postgres` as hostname (the compose service name) |
| Model not found | Set `MODEL_PATH=weights/best.pt` in `.env`; place the file at that path |
| Port already in use | Set `PORT=8001` (or any free port) before running |
| `QUEUE_BACKEND=sync` slow | Sync mode processes the job in-process; use Redis + separate worker for parallel jobs |
