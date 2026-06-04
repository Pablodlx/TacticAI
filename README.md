# TacticAI — Tactical football video analysis

Tactical analysis from standard broadcast video — no additional hardware required. YOLO detection, ReID tracking, team classification, possession, passes, field homography, heatmaps, and heuristic event prediction with live alerts. Runs **locally** (monolithic WebSocket flow) or as a **decoupled API + worker** stack deployable on Google Cloud.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com/)
[![CI](https://github.com/Pablodlx/TacticEYE2_github/actions/workflows/ci.yml/badge.svg)](https://github.com/Pablodlx/TacticEYE2_github/actions)

---

## Key metrics (from evaluation)

| Model | mAP@0.5 | mAP@0.5:0.95 | Inference |
|-------|---------|--------------|-----------|
| YOLO11m detector (player, ball, referee, goalkeeper) | **0.893** | 0.645 | ~26 ms/frame (RTX 5070 Ti) |
| YOLO11m field keypoints (15 types) | **0.956** | 0.663 | ~10 ms/frame |

Full pipeline (YOLO + ReID + TeamClassifier + Possession + Heatmaps + Serialization): **~60–65 ms/frame** on RTX 5070 Ti Laptop → ≈16 FPS effective (≈1.5× real-time duration). CPU-only fallback available.

---

## Repository map

| Area | Contents |
|------|----------|
| **CV pipeline** | `modules/` — YOLO, ReID, teams, possession, spatial, heatmaps, homography, alerts |
| **Legacy web** | `app.py` — upload, batched analysis, WebSocket streaming, heatmap APIs |
| **Dual API (jobs)** | `app_service/` — FastAPI jobs API, pluggable storage/queue/DB providers |
| **Worker** | `worker/` — queue consumer, runs the same pipeline via `run_match_analysis` |
| **UI** | `templates/index.html`, `static/app.js`, `static/style.css` |
| **Infra** | `Dockerfile.web`, `Dockerfile.worker`, compose files, `cloudbuild*.yaml`, `scripts/` |
| **DB** | SQLAlchemy + Alembic (`alembic/`, `scripts/db_manage.sh`) |
| **Config** | `config/` — `predictions.yaml`, `soccernet.yaml`, `attack_direction.yaml` |
| **CI/CD** | `.github/workflows/ci.yml` (tests) + `cloudbuild.yaml` (deploy) |
| **Tests** | `tests/` — 88 tests across 11 files |

---

## Two ways to run

### 1) Legacy mode (recommended for local UI + WebSocket)

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:8001 (or the port printed in the console)
```

- **Entry:** `python app.py`
- **Routes:** `/api/upload`, `/api/analyze/{session_id}`, `/api/heatmap/...`, WebSocket `/ws/{session_id}`
- **Port:** `8001` by default (or `PORT` env var)

### 2) Dual API + worker (`app_service`)

```bash
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
./scripts/run_local.sh
# Open http://localhost:8000
```

- **Entry:** `uvicorn app_service.main:app` (wrapped by `scripts/run_local.sh`)
- **Routes:** `POST /jobs/upload`, `POST /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/results`, `GET /health`
- **Jobs:** configurable queue (`sync`, `redis`, `pubsub`), storage (`local`, `gcs`), DB via `DATABASE_URL`

Full guide → [README_LOCAL.md](README_LOCAL.md)

---

## Frontend: dual mode

`static/app.js` detects the environment automatically:

- **`legacy`** (localhost / 127.0.0.1) — uses `/api/*` and WebSocket live streaming
- **`jobs`** (Cloud Run `run.app`) — `POST /jobs`, polls `GET /jobs/{id}` every ~2.5 s; file upload shows a notice in cloud mode

---

## Analysis pipeline

### What the pipeline produces

From raw video:

- **Per-frame detections** — bounding boxes, class (`player`, `ball`, `referee`, `goalkeeper`), persistent track IDs, team IDs
- **Possession and passes** — ball–player proximity in image space, smoothed possession, pass/recovery events
- **Spatial layer** (optional) — field keypoints → homography → player feet in **105×68 m** pitch coordinates → zone labels → heatmap grids per team
- **Tactical alerts** — `MatchAlertSystem` combines zone/possession heuristics with `EventPredictionEngine` scores (linear metrics + sigmoid, driven by `config/predictions.yaml`); optional natural-language wording via Anthropic API

All implemented in **`BatchProcessor.process_chunk()`**, orchestrated by **`run_match_analysis()`**.

### Entry points (same engine, three shells)

| Entry | File | Role |
|-------|------|------|
| Legacy web | `app.py` | Builds `AnalysisConfig`, wires WebSocket callbacks, optional `AttackDirectionManager` |
| Core function | `modules/match_analyzer.py` | `run_match_analysis(match_id, config, resume=True)` — video loop, state, callbacks |
| Jobs / worker | `app_service/providers/analysis/local.py` | `LocalPipelineRunner` → same `run_match_analysis` |

### High-level flow

```
video_sources → read_frame_batches → match_analyzer (loop)
                                          └─ BatchProcessor.process_chunk (per batch)
                                                ├─ YOLO predict (batched)
                                                ├─ ReIDTracker.update
                                                ├─ TeamClassifierV2
                                                ├─ PossessionTrackerV2
                                                ├─ Spatial branch (keypoints → homography → heatmaps)
                                                └─ MatchAlertSystem → alerts
```

### Inside each chunk (`modules/batch_processor.py`)

Per-frame order inside `process_chunk`:

1. **Parse YOLO boxes** — classes 0–3: player, ball, referee, goalkeeper
2. **`ReIDTracker.update`** — stable track IDs across frames
3. **`TeamClassifierV2`** — KMeans k=2 in CIELAB color space + temporal voting; referees/ball → team `-1`
4. **Ball owner** — nearest player center within ~60 px radius
5. **`PossessionTrackerV2.update`** — rolling possession + pass/recovery event detection
6. **Spatial branch** (when `enable_spatial_tracking=True`):
   - `FieldKeypointsYOLO` → `FieldCalibratorKeypoints` → homography via RANSAC
   - Player feet projected to field coordinates
   - `SpatialPossessionTracker` and `FieldHeatmapSystem` accumulation
   - `OpticalFlowTracker` + `KalmanFilterPositionSmoother` (disabled by default — high cost)
7. **`MatchAlertSystem.analyze_and_generate_alerts`** — event scores, optional LLM wording

### Prediction layer

| File | Role |
|------|------|
| `config/predictions.yaml` | Event types, signal weights, thresholds, cooldowns |
| `modules/event_prediction_engine.py` | Weighted signal sum → sigmoid → probability |
| `modules/prediction_metrics.py` | Feature extraction from live state |
| `modules/match_state_builder.py` | Adapts live stats → prediction model |
| `modules/prediction_dispatcher.py` | Rate-limits / deduplicates alert emissions |
| `modules/prediction_anthropic.py` | Optional Anthropic Claude wording (never decides, only phrases) |

---

## Module catalog (`modules/`)

| Module | Responsibility |
|--------|----------------|
| `match_analyzer.py` | `run_match_analysis`, `AnalysisConfig`, batch loop, resume |
| `batch_processor.py` | `BatchProcessor`, `ChunkOutput`, spatial + alert integration |
| `video_sources.py` | Multi-source frame iterators and batching |
| `match_state.py` | `MatchState`, sub-states, `FileSystemStorage` / `RedisStorage` |
| `reid_tracker.py` | Appearance-embedding tracking, Hungarian assignment |
| `team_classifier_v2.py` | CIELAB KMeans + anti-green/dorsal mask + temporal voting |
| `team_classifier.py` | Base classifier used by `reid_tracker` |
| `possession_tracker_v2.py` | Deterministic possession + pass statistics |
| `possession_tracker.py` | Base tracker used by `spatial_possession_tracker` |
| `spatial_possession_tracker.py` | Zone-based possession accumulation |
| `match_alert_system.py` | Tactical alerts + prediction hook |
| `field_keypoints_yolo.py` | YOLO-based pitch keypoint detector |
| `field_calibrator_keypoints.py` | Keypoint-based homography estimation |
| `field_model_keypoints.py` | Field geometry for keypoint calibration |
| `field_model.py` | Field dimensions and zone partition |
| `field_heatmap_system.py` | Homography resolution, projection, `HeatmapAccumulator` |
| `field_calibration.py` | Line-based calibration (used by spatial tracker) |
| `field_line_detector.py` | Line detection for `field_calibration` |
| `field_orientation.py` | Attack direction / orientation helpers |
| `optical_flow_tracker.py` | Optional optical flow fallback (off by default) |
| `position_smoother.py` | Kalman filter + trajectory validator for projected positions |
| `attack_direction_manager.py` | Period and direction logic |
| `event_prediction_engine.py` | Score-based event predictions |
| `prediction_metrics.py` | Feature computation |
| `prediction_dispatcher.py` | Emit rate-limiting |
| `prediction_config.py` | YAML-backed config loading |
| `match_state_builder.py` | Bridge live state → prediction model |
| `prediction_anthropic.py` | Optional LLM natural-language phrasing |
| `tactical_analyzer.py` | Extended tactical string analysis |
| `match_alert_system.py` | Alert emission and deduplication |

---

## Environment variables

Copy and adapt one of the example files:

- `.env.example` — general template
- `.env.local.example` — local compose (Postgres + Redis)
- `.env.cloud.example` — Cloud Run / Cloud SQL / GCS / Pub/Sub

Key variables (`app_service/config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `weights/best.pt` | YOLO detector weights |
| `DATABASE_URL` | `sqlite:///./runtime_data/jobs.db` | SQLAlchemy connection string |
| `STORAGE_BACKEND` | `filesystem` | `filesystem` \| `gcs` \| `redis` |
| `QUEUE_BACKEND` | `local` | `local` \| `redis` \| `pubsub` |
| `GCS_BUCKET` | — | GCS bucket name (if `STORAGE_BACKEND=gcs`) |
| `ANTHROPIC_API_KEY` | — | Enables LLM narrative (optional) |
| `BATCH_SIZE_SECONDS` | `3` | Micro-batch duration |
| `YOLO_IMGSZ` | `640` | Inference image size |
| `PORT` | `8000` | Server port |

---

## Database and migrations (Alembic)

```bash
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local   # create dirs, optionally wipe DB, run alembic upgrade head
./scripts/db_manage.sh upgrade      # migrations only
./scripts/db_manage.sh migrate "message"  # generate new autogenerated revision
```

---

## Worker

```bash
python worker/main.py
# or
./scripts/run_worker_local.sh
```

The worker listens on the configured queue and calls `LocalPipelineRunner` → `modules.match_analyzer.run_match_analysis` — the same pipeline as local mode.

---

## Docker and Google Cloud

| File | Purpose |
|------|---------|
| `Dockerfile.web` | API image (`uvicorn app_service.main:app`, no PyTorch) |
| `Dockerfile.worker` | Worker image (PyTorch + CUDA + YOLO weights) |
| `Dockerfile` | Legacy monolithic image for local demo |
| `docker-compose.local.yml` | Local stack: web + worker + redis + postgres |
| `docker-compose.cloud.yml` | Cloud-oriented compose hints |
| `cloudbuild.yaml` | CI/CD: build + deploy web to Cloud Run |
| `cloudbuild-worker.yaml` | Build + push worker image |
| `cloudbuild-demo.yaml` | Demo deployment build |

Scripts in `scripts/`:

| Script | Purpose |
|--------|---------|
| `run_local.sh` | Start `app_service` locally |
| `run_worker_local.sh` | Start worker locally |
| `db_manage.sh` | Alembic helpers (init-local, upgrade, migrate) |
| `deploy_web.sh` | Deploy web service to Cloud Run |
| `deploy_worker_vm.sh` | Provision GPU VM and deploy worker |
| `deploy_worker_cloudrun.sh` | Deploy worker as Cloud Run service (CPU/auto-scale) |
| `deploy_demo.sh` | Deploy monolithic demo |
| `create_gcp_resources.sh` | Create GCP buckets, Pub/Sub, Artifact Registry |

Detailed cloud guide → [README_GCP.md](README_GCP.md)

---

## CI (GitHub Actions)

On every **push** and **pull request** to `main`, `ci.yml` runs on **Python 3.11, 3.12, and 3.13**:

1. Install `requirements.txt` + pytest tooling
2. Init local SQLite DB with Alembic (`./scripts/db_manage.sh init-local`)
3. `pytest -q tests/` — full test suite (88 tests)

---

## Tests

```bash
pip install pytest pytest-asyncio httpx pytest-mock
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
pytest -q
```

Test files in `tests/`:

| File | What it covers |
|------|----------------|
| `test_api.py` | HTTP endpoint status codes, response schemas, error handling |
| `test_batch_processor.py` | Pipeline sequence with mocked YOLO detector |
| `test_match_state.py` | Serialization/deserialization round-trips |
| `test_possession_tracker.py` | Edge cases: no ball, equidistant players, possession change |
| `test_worker_integration.py` | Full job flow with mocked detector and synthetic video |
| `test_config_schema.py` | Config defaults, env var loading, invalid value rejection |
| `test_optical_flow.py` | Optical flow and Kalman smoothing |
| `test_alerts.py` | Alert generation and deduplication |
| `test_prediction_engine.py` | Event scoring and thresholds |
| `test_dual_api_integration.py` | Dual API integration |
| `test_worker_pipeline_real_call.py` | Worker pipeline end-to-end |

---

## Directory layout

```text
.
├── app.py                    # Legacy FastAPI + WebSocket + streaming analysis
├── app_service/              # Dual API: jobs, pluggable providers, config
├── worker/                   # Queue consumer + pipeline runner
├── modules/                  # Vision and analysis engine (31 modules)
├── schemas/                  # Pydantic models (predictions)
├── config/                   # YAML: predictions, attack_direction, soccernet
├── templates/                # index.html
├── static/                   # app.js, style.css
├── tests/                    # 88 automated tests
├── scripts/                  # Shell helpers: run, db, deploy
├── alembic/                  # DB migrations
├── docker-compose.local.yml  # Local dev stack
├── docker-compose.cloud.yml  # Cloud hints
├── Dockerfile.web            # Web API image
├── Dockerfile.worker         # Worker image (CUDA)
├── Dockerfile                # Legacy monolithic image
├── cloudbuild.yaml           # Cloud Build: web deploy
├── cloudbuild-worker.yaml    # Cloud Build: worker image
├── cloudbuild-demo.yaml      # Cloud Build: demo deploy
├── requirements.txt          # Unified dependencies
├── requirements-web.txt      # Web-only dependencies (no PyTorch)
├── .github/workflows/        # CI (ci.yml) + CD (cd.yml)
├── weights/                  # YOLO model weights (.pt)
└── runtime_data/             # SQLite DB and local job workspace (gitignored)
```

---

## Requirements

- **Python:** 3.11+ (CI tests 3.11, 3.12, 3.13)
- **GPU:** NVIDIA CUDA-capable GPU recommended; CPU fallback available but ~15–20× slower
- **Weights:** `weights/best.pt` (detector) must be present; set `MODEL_PATH` to override

---

## Quick troubleshooting

| Issue | Fix |
|-------|-----|
| `table jobs already exists` with Alembic | Use `./scripts/db_manage.sh init-local` — do not mix ad-hoc `create_all` with Alembic on the same DB |
| Cloud Run UI without live stats | On `run.app`, `jobs` mode polls instead of streaming; extend polling or wire SSE |
| Model not found | Set `MODEL_PATH=weights/best.pt` in your `.env` |
| CUDA not detected | Pipeline falls back to CPU automatically; set `device=cpu` explicitly if needed |

---

## License

MIT — see [LICENSE](LICENSE)

Detection: [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) · Framework: [FastAPI](https://fastapi.tiangolo.com/) · Cloud: [Google Cloud Platform](https://cloud.google.com/)
