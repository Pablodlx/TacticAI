# TacticAI — Análisis táctico de fútbol mediante visión por computador

Sistema de análisis táctico que extrae información táctica directamente de vídeo de retransmisión estándar, sin hardware adicional. Combina detección YOLO, seguimiento multi-objeto con Re-ID, clasificación de equipos, estimación de posesión, proyección geométrica al campo, mapas de calor y un motor de predicción heurística de eventos tácticos con alertas configurables.

Funciona en **modo local** (monolítico con streaming vía WebSocket) o como **arquitectura desacoplada API + worker** desplegable en Google Cloud Run.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com/)
[![CI](https://github.com/Pablodlx/TacticEYE2/actions/workflows/ci.yml/badge.svg)](https://github.com/Pablodlx/TacticEYE2/actions)

---

## Métricas de evaluación

| Modelo | mAP@0.5 | mAP@0.5:0.95 | Inferencia |
|--------|---------|--------------|-----------|
| YOLO11m detector (player, ball, referee, goalkeeper) | **0,893** | 0,645 | ~26 ms/fotograma (RTX 5070 Ti) |
| YOLO11m keypoints del campo (15 tipos) | **0,956** | 0,663 | ~10 ms/fotograma |

Pipeline completo (YOLO + ReID + TeamClassifier + Possession + Heatmaps + Serialización): **~60–65 ms/fotograma** en RTX 5070 Ti Laptop → ≈16 FPS efectivos (≈1,5× la duración real del vídeo). Modo CPU disponible.

---

## Estructura del repositorio

| Área | Contenido |
|------|-----------|
| **Pipeline CV** | `modules/` — YOLO, ReID, equipos, posesión, espacial, heatmaps, homografía, alertas |
| **Modo monolítico** | `app.py` — subida de vídeo, análisis por micro-lotes, streaming WebSocket, APIs de heatmap |
| **API dual (trabajos)** | `app_service/` — API FastAPI de trabajos, providers intercambiables de storage/cola/BD |
| **Worker** | `worker/` — consumidor de cola, ejecuta el mismo pipeline vía `run_match_analysis` |
| **Interfaz web** | `templates/index.html`, `static/app.js`, `static/style.css` |
| **Infraestructura** | `Dockerfile.web`, `Dockerfile.worker`, compose files, `deploy/cloudbuild*.yaml`, `scripts/` |
| **Base de datos** | SQLAlchemy + Alembic (`alembic/`, `scripts/db_manage.sh`) |
| **Configuración** | `config/` — `predictions.yaml`, `soccernet.yaml`, `attack_direction.yaml` |
| **CI/CD** | `.github/workflows/ci.yml` (tests) + `cd.yml` (publicación de imagen) |
| **Tests** | `tests/` — 88 tests en 11 ficheros |

---

## Modos de arranque

### Modo 1 — Monolítico local (UI + WebSocket)

```bash
pip install -r requirements.txt
python app.py
# Abrir http://localhost:8001
```

- **Endpoints:** `/api/upload`, `/api/analyze/{session_id}`, `/api/heatmap/...`, WebSocket `/ws/{session_id}`
- **Puerto:** `8001` por defecto (o variable de entorno `PORT`)

El dashboard se actualiza en tiempo casi real vía WebSocket conforme se completan los micro-lotes (~4–5 s por lote).

### Modo 2 — API dual + worker (cola sync)

```bash
cp .env.example .env
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
./scripts/run_local.sh
# Abrir http://localhost:8000
```

- **Endpoints:** `POST /jobs/upload`, `POST /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/results`, `GET /health`
- **Backends de cola:** `sync` (por defecto, en proceso), `redis`, `pubsub`
- **Backends de almacenamiento:** `local` (por defecto), `gcs`

#### Ejemplo rápido de API

```bash
# Subir vídeo
UPLOAD=$(curl -s -F "file=@partido.mp4" http://localhost:8000/jobs/upload)
INPUT_URI=$(echo "$UPLOAD" | python -c "import sys,json;print(json.load(sys.stdin)['input_uri'])")

# Crear trabajo
JOB=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d "{\"input_uri\":\"$INPUT_URI\"}")
JOB_ID=$(echo "$JOB" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# Consultar estado
curl -s "http://localhost:8000/jobs/$JOB_ID"

# Obtener resultados
curl -s "http://localhost:8000/jobs/$JOB_ID/results"
```

### Modo 3 — Stack completo con Docker Compose

```bash
cp .env.local.example .env
docker compose -f docker-compose.local.yml up --build
```

Levanta: `web` (puerto 8000) + `worker` + `redis` + `postgres`.

---

## Interfaz web: modo dual

`static/app.js` detecta el entorno automáticamente:

- **`legacy`** (localhost / 127.0.0.1) — usa `/api/*` y streaming WebSocket en tiempo casi real
- **`jobs`** (Cloud Run `*.run.app`) — `POST /jobs`, consulta `GET /jobs/{id}` cada ~2,5 s

---

## Pipeline de análisis

### Qué produce el pipeline

A partir de vídeo en bruto:

- **Detecciones por fotograma** — bounding boxes, clase (`player`, `ball`, `referee`, `goalkeeper`), track IDs persistentes, IDs de equipo
- **Posesión y pases** — proximidad balón–jugador en espacio imagen, posesión suavizada, eventos de pase y recuperación
- **Capa espacial** (opcional) — keypoints del campo → homografía → pies de jugadores en coordenadas de campo **105×68 m** → etiquetas de zona → grillas de heatmap por equipo
- **Alertas tácticas** — `MatchAlertSystem` combina heurísticas de zona/posesión con puntuaciones de `EventPredictionEngine` (métricas lineales + sigmoide, configuradas en `config/predictions.yaml`); redacción opcional en lenguaje natural vía API de Anthropic

Todo implementado en **`BatchProcessor.process_chunk()`**, orquestado por **`run_match_analysis()`**.

### Puntos de entrada (mismo motor, tres envolturas)

| Entrada | Fichero | Rol |
|---------|---------|-----|
| Web monolítica | `app.py` | Construye `AnalysisConfig`, conecta callbacks WebSocket, gestiona `AttackDirectionManager` |
| Función principal | `modules/match_analyzer.py` | `run_match_analysis(match_id, config, resume=True)` — bucle de vídeo, estado, callbacks |
| Jobs / worker | `app_service/providers/analysis/local.py` | `LocalPipelineRunner` → mismo `run_match_analysis` |

### Flujo general

```
fuentes_vídeo → read_frame_batches → match_analyzer (bucle)
                                          └─ BatchProcessor.process_chunk (por micro-lote)
                                                ├─ YOLO predict (en batch)
                                                ├─ ReIDTracker.update
                                                ├─ TeamClassifierV2
                                                ├─ PossessionTrackerV2
                                                ├─ Rama espacial (keypoints → homografía → heatmaps)
                                                └─ MatchAlertSystem → alertas
```

### Detalle de cada micro-lote (`modules/batch_processor.py`)

1. **Parseo de cajas YOLO** — clases 0–3: player, ball, referee, goalkeeper
2. **`ReIDTracker.update`** — track IDs estables entre fotogramas (matching greedy: 80% apariencia + 20% IoU, umbral 0,4; backbone ResNet18, embeddings de 512 dimensiones)
3. **`TeamClassifierV2`** — KMeans k=2 en espacio de color CIELAB + máscara anti-verde/anti-dorsal + votación temporal; árbitros y balón → equipo `-1`
4. **Jugador más cercano al balón** — distancia euclidiana al centro del bounding box dentro de ~60 px
5. **`PossessionTrackerV2.update`** — posesión acumulada + detección de pases y recuperaciones (histéresis de 5 fotogramas)
6. **Rama espacial** (cuando `enable_spatial_tracking=True`):
   - `FieldKeypointsYOLO` → `FieldCalibratorKeypoints` → homografía vía RANSAC (mínimo 4 keypoints)
   - Proyección de pies de jugadores a coordenadas de campo
   - Acumulación en `SpatialPossessionTracker` y `HeatmapAccumulator`
7. **`MatchAlertSystem.analyze_and_generate_alerts`** — puntuaciones de eventos, redacción LLM opcional

### Motor de predicción de eventos

| Fichero | Rol |
|---------|-----|
| `config/predictions.yaml` | Tipos de evento (`dangerous_attack`, `shot`, `corner`, `dangerous_transition`, `final_third_entry`, `dangerous_turnover`), pesos de señales, umbrales, cooldowns |
| `modules/event_prediction_engine.py` | Suma ponderada de señales → sigmoide → probabilidad |
| `modules/prediction_metrics.py` | Extracción de features del estado en vivo |
| `modules/match_state_builder.py` | Adaptador estado vivo → modelo de predicción |
| `modules/prediction_dispatcher.py` | Limitación de tasa y deduplicación de alertas |
| `modules/prediction_anthropic.py` | Redacción en lenguaje natural vía Anthropic Claude (no interviene en el cálculo) |

---

## Catálogo de módulos (`modules/`)

| Módulo | Responsabilidad |
|--------|----------------|
| `match_analyzer.py` | `run_match_analysis`, `AnalysisConfig`, bucle de micro-lotes, reanudación |
| `batch_processor.py` | `BatchProcessor`, `ChunkOutput`, integración espacial y de alertas |
| `video_sources.py` | Iteradores de fotogramas y batching multi-fuente |
| `match_state.py` | `MatchState`, sub-estados, `FileSystemStorage` / `RedisStorage` |
| `reid_tracker.py` | Seguimiento por embeddings de apariencia, asignación greedy |
| `team_classifier_v2.py` | KMeans CIELAB + máscara anti-verde/dorsal + votación temporal |
| `team_classifier.py` | Clasificador base usado por `reid_tracker` |
| `possession_tracker_v2.py` | Posesión determinista + estadísticas de pases |
| `possession_tracker.py` | Tracker base usado por `spatial_possession_tracker` |
| `spatial_possession_tracker.py` | Acumulación de posesión por zonas |
| `match_alert_system.py` | Alertas tácticas + integración con motor de predicción |
| `field_keypoints_yolo.py` | Detector YOLO de puntos clave del terreno de juego |
| `field_calibrator_keypoints.py` | Estimación de homografía a partir de keypoints |
| `field_model_keypoints.py` | Geometría del campo para calibración por keypoints |
| `field_model.py` | Dimensiones del campo y partición en zonas |
| `field_heatmap_system.py` | Resolución de homografía, proyección y `HeatmapAccumulator` |
| `field_calibration.py` | Calibración por líneas (usada por el tracker espacial) |
| `field_line_detector.py` | Detección de líneas para `field_calibration` |
| `field_orientation.py` | Dirección de ataque y orientación del campo |
| `optical_flow_tracker.py` | Flujo óptico como fallback posicional (deshabilitado por defecto) |
| `position_smoother.py` | Filtro de Kalman + validador de trayectorias para posiciones proyectadas |
| `attack_direction_manager.py` | Lógica de periodos y dirección de ataque |
| `event_prediction_engine.py` | Predicción de eventos por puntuación |
| `prediction_metrics.py` | Cálculo de features |
| `prediction_dispatcher.py` | Limitación de emisión de alertas |
| `prediction_config.py` | Carga de configuración desde YAML |
| `match_state_builder.py` | Puente estado vivo → modelo de predicción |
| `prediction_anthropic.py` | Redacción LLM opcional en lenguaje natural |
| `tactical_analyzer.py` | Análisis táctico extendido por cadenas |

---

## Variables de entorno

Copia y adapta uno de los ficheros de ejemplo:

- `.env.example` — plantilla general
- `.env.local.example` — compose local (Postgres + Redis)
- `.env.cloud.example` — Cloud Run / Cloud SQL / GCS / Pub/Sub

Variables principales (`app_service/config.py`):

| Variable | Valor por defecto | Descripción |
|----------|------------------|-------------|
| `MODEL_PATH` | `weights/best.pt` | Pesos del detector YOLO |
| `DATABASE_URL` | `sqlite:///./runtime_data/jobs.db` | Cadena de conexión SQLAlchemy |
| `STORAGE_BACKEND` | `local` | `local` \| `gcs` |
| `QUEUE_BACKEND` | `sync` | `sync` \| `redis` \| `pubsub` |
| `GCS_INPUT_BUCKET` | — | Bucket GCS de entrada (si `STORAGE_BACKEND=gcs`) |
| `GCS_OUTPUT_BUCKET` | — | Bucket GCS de resultados (si `STORAGE_BACKEND=gcs`) |
| `ANTHROPIC_API_KEY` | — | Activa narrativa LLM (opcional) |
| `BATCH_SIZE_SECONDS` | `3` | Duración del micro-lote de análisis en segundos |
| `PORT` | `8000` | Puerto del servidor |

---

## Base de datos y migraciones (Alembic)

```bash
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local   # crear dirs, inicializar BD, ejecutar alembic upgrade head
./scripts/db_manage.sh upgrade      # aplicar migraciones pendientes
./scripts/db_manage.sh migrate "descripción"  # generar nueva revisión
```

---

## Worker

```bash
python worker/main.py
# o bien
./scripts/run_worker_local.sh
```

El worker escucha la cola configurada y llama a `LocalPipelineRunner` → `modules.match_analyzer.run_match_analysis` — el mismo pipeline que en modo local.

En modo `sync` el worker se ejecuta en el mismo proceso que la API (no requiere proceso separado). En modo `redis` lanzarlo en un terminal independiente.

---

## Docker e infraestructura

| Fichero | Propósito |
|---------|-----------|
| `Dockerfile.web` | Imagen de la API (`uvicorn app_service.main:app`, sin PyTorch) |
| `Dockerfile.worker` | Imagen del worker (PyTorch CPU + pesos YOLO integrados) |
| `Dockerfile` | Imagen monolítica para demo local (multi-stage) |
| `docker-compose.local.yml` | Stack local: web + worker + redis + postgres |
| `docker-compose.cloud.yml` | Compose orientado a cloud |
| `deploy/cloudbuild.yaml` | Cloud Build: build + push imagen web a Artifact Registry |
| `deploy/cloudbuild-worker.yaml` | Cloud Build: build + push imagen worker |
| `deploy/cloudbuild-demo.yaml` | Cloud Build: build + push + despliegue del demo en Cloud Run |

Scripts en `scripts/`:

| Script | Propósito |
|--------|-----------|
| `run_local.sh` | Arrancar `app_service` en local |
| `run_worker_local.sh` | Arrancar el worker en local |
| `db_manage.sh` | Helpers Alembic (init-local, upgrade, migrate) |
| `deploy_web.sh` | Desplegar servicio web en Cloud Run |
| `deploy_worker_vm.sh` | Provisionar VM con GPU y desplegar worker |
| `deploy_worker_cloudrun.sh` | Desplegar worker como servicio Cloud Run (CPU/auto-scale) |
| `deploy_demo.sh` | Desplegar demo monolítico |
| `create_gcp_resources.sh` | Crear buckets GCS, Pub/Sub y Artifact Registry |

---

## Despliegue en Google Cloud

### Arquitectura

| Componente | Servicio GCP |
|-----------|-------------|
| API web | Cloud Run (auto-scale, CPU) |
| Worker | Cloud Run (CPU, min-instancias=0) **o** VM GCE con GPU |
| Almacenamiento | Cloud Storage (GCS) |
| Cola | Cloud Pub/Sub |
| Base de datos | Cloud SQL (PostgreSQL) |
| Registro de contenedores | Artifact Registry |

> **Opciones del worker:** Cloud Run es adecuado para vídeos cortos/medios (timeout hasta 3600 s). Para partidos completos con GPU se recomienda desplegar el worker en una VM GCE con drivers NVIDIA.

### Prerrequisitos

```bash
export GCP_PROJECT_ID=tu-proyecto
export GCP_REGION=europe-west1
export GCS_INPUT_BUCKET=tacticeye2-input
export GCS_OUTPUT_BUCKET=tacticeye2-output
export PUBSUB_TOPIC=tacticeye2-jobs
export PUBSUB_SUBSCRIPTION=tacticeye2-jobs-sub
export ARTIFACT_REPO=tacticeye2
export CLOUD_RUN_SERVICE=tacticeye2-web
export WORKER_SERVICE=tacticeye2-worker
```

### Paso 1 — Crear recursos GCP

```bash
./scripts/create_gcp_resources.sh
```

Crea: buckets GCS, topic + suscripción Pub/Sub, repositorio Artifact Registry.

### Paso 2 — Aplicar migraciones de BD

```bash
export DATABASE_URL='postgresql+psycopg2://USUARIO:PASSWORD@/BD?host=/cloudsql/PROYECTO:REGION:INSTANCIA'
./scripts/db_manage.sh cloud-upgrade
```

Roles IAM necesarios: `roles/storage.objectAdmin`, `roles/pubsub.publisher`, `roles/pubsub.subscriber`, `roles/cloudsql.client`.

### Paso 3 — Desplegar API web

```bash
./scripts/deploy_web.sh
```

Construye `Dockerfile.web` vía `deploy/cloudbuild.yaml`, publica en Artifact Registry y despliega en Cloud Run.

### Paso 4a — Desplegar worker en Cloud Run (CPU)

```bash
./scripts/deploy_worker_cloudrun.sh
```

Construye `Dockerfile.worker` vía `deploy/cloudbuild-worker.yaml`. Adecuado para clips de hasta ~60 min.

### Paso 4b — Desplegar worker en VM con GPU (partidos completos)

```bash
./scripts/deploy_worker_vm.sh
# En la VM, tras instalar drivers NVIDIA:
docker run --gpus all --env-file .env.cloud.example \
  <REGION>-docker.pkg.dev/<PROYECTO>/<REPO>/worker:latest \
  python worker/main.py
```

Una GPU de gama media (clase RTX 3060) procesa un partido de 90 min en ~135 min.

### Flujo de trabajo cloud completo

```bash
SERVICE_URL=$(gcloud run services describe ${CLOUD_RUN_SERVICE} \
  --region ${GCP_REGION} --format 'value(status.url)')

# 1. Subir vídeo
UPLOAD=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -F "file=@partido.mp4" "${SERVICE_URL}/jobs/upload")
INPUT_URI=$(echo "$UPLOAD" | python -c "import sys,json;print(json.load(sys.stdin)['input_uri'])")

# 2. Crear trabajo
JOB=$(curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -X POST "${SERVICE_URL}/jobs" \
  -H "Content-Type: application/json" \
  -d "{\"input_uri\":\"${INPUT_URI}\"}")
JOB_ID=$(echo "$JOB" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")

# 3. Consultar estado
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/jobs/${JOB_ID}"

# 4. Obtener resultados
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "${SERVICE_URL}/jobs/${JOB_ID}/results"
```

---

## Integración continua (GitHub Actions)

En cada **push** y **pull request** a `main`, `ci.yml` se ejecuta en **Python 3.11, 3.12 y 3.13**:

1. Instalar `requirements.txt` + herramientas de pytest
2. Inicializar BD SQLite local con Alembic (`./scripts/db_manage.sh init-local`)
3. `pytest -q tests/` — suite completa (88 tests)

`cd.yml` publica la imagen Docker en GitHub Container Registry (GHCR) en cada push a `main`. El despliegue a producción en Cloud Run se realiza mediante los scripts de `deploy/cloudbuild*.yaml`.

---

## Tests

```bash
pip install pytest pytest-asyncio httpx pytest-mock
export DATABASE_URL=sqlite:///./runtime_data/jobs.db
./scripts/db_manage.sh init-local
pytest -q
```

88 tests en 11 ficheros. Todos los módulos pesados (YOLO, GPU) están mockeados, por lo que los tests se ejecutan sin GPU ni pesos del modelo.

| Fichero | Qué cubre |
|---------|-----------|
| `test_api.py` | Códigos de respuesta HTTP, esquemas, manejo de errores |
| `test_batch_processor.py` | Secuencia del pipeline con detector YOLO mockeado |
| `test_match_state.py` | Ciclos de serialización/deserialización |
| `test_possession_tracker.py` | Casos límite: sin balón, jugadores equidistantes, cambio de posesión |
| `test_worker_integration.py` | Flujo completo de trabajo con detector mockeado y vídeo sintético |
| `test_config_schema.py` | Valores por defecto de config, carga de variables de entorno, rechazo de valores inválidos |
| `test_optical_flow.py` | Flujo óptico y suavizado Kalman |
| `test_alerts.py` | Generación y deduplicación de alertas |
| `test_prediction_engine.py` | Puntuación de eventos y umbrales |
| `test_dual_api_integration.py` | Integración de la API dual |
| `test_worker_pipeline_real_call.py` | Pipeline del worker end-to-end |

---

## Estructura de directorios

```text
.
├── app.py                    # FastAPI monolítico + WebSocket + análisis en streaming
├── app_service/              # API dual: trabajos, providers intercambiables, config
├── worker/                   # Consumidor de cola + ejecutor del pipeline
├── modules/                  # Motor de visión y análisis (29 módulos)
├── schemas/                  # Modelos Pydantic (predicciones)
├── config/                   # YAML: predictions, attack_direction, soccernet
├── templates/                # index.html
├── static/                   # app.js, style.css
├── tests/                    # 88 tests automatizados en 11 ficheros
├── scripts/                  # Scripts de shell: arranque, BD, despliegue
├── alembic/                  # Migraciones de BD
├── deploy/                   # Configuraciones Cloud Build
│   ├── cloudbuild.yaml       #   Build + push imagen web
│   ├── cloudbuild-worker.yaml#   Build + push imagen worker
│   └── cloudbuild-demo.yaml  #   Build + push + despliegue demo
├── docker-compose.local.yml  # Stack de desarrollo local
├── docker-compose.cloud.yml  # Hints para despliegue cloud
├── Dockerfile.web            # Imagen API (sin PyTorch)
├── Dockerfile.worker         # Imagen worker (PyTorch CPU)
├── Dockerfile                # Imagen monolítica para demo local (multi-stage)
├── requirements.txt          # Dependencias completas
├── requirements-web.txt      # Dependencias solo web (sin PyTorch)
├── .github/workflows/        # ci.yml (tests) + cd.yml (publicación imagen)
├── weights/                  # Pesos de modelos YOLO (.pt)
└── runtime_data/             # BD SQLite y workspace local de trabajos (en .gitignore)
```

---

## Requisitos

- **Python:** 3.11+ (CI testea 3.11, 3.12, 3.13)
- **GPU:** Se recomienda GPU NVIDIA con CUDA; modo CPU disponible pero ~15–20× más lento
- **Pesos:** `weights/best.pt` (detector) debe estar presente; usar `MODEL_PATH` para sobreescribir

---

## Resolución de problemas

| Problema | Solución |
|----------|----------|
| `table jobs already exists` con Alembic | Usar `./scripts/db_manage.sh init-local` — no mezclar `create_all` ad-hoc con Alembic |
| Error de BD en el primer arranque | Ejecutar `./scripts/db_manage.sh init-local` antes de iniciar la API |
| UI de Cloud Run sin estadísticas en vivo | En `*.run.app`, el modo `jobs` consulta por polling en lugar de streaming |
| Modelo no encontrado | Definir `MODEL_PATH=weights/best.pt` en el fichero `.env` |
| CUDA no detectado | El pipeline cae automáticamente a CPU; definir `device=cpu` explícitamente si es necesario |
| Puerto en uso | Definir `PORT=8001` (o cualquier puerto libre) antes de arrancar |
| Errores Pub/Sub | Verificar que los nombres de topic/suscripción coinciden con las variables de entorno y que la cuenta de servicio tiene `pubsub.publisher` + `pubsub.subscriber` |
| Cloud SQL connection refused | Validar el path del socket de Cloud SQL Auth Proxy en `DATABASE_URL` |
| Permiso denegado en GCS | Revisar IAM del bucket y la identidad de la cuenta de servicio en runtime |
| Timeout del worker | Para partidos completos usar una VM con GPU (`deploy_worker_vm.sh`); el timeout máximo de Cloud Run es 3600 s |
| `QUEUE_BACKEND=sync` lento | El modo sync procesa en el mismo proceso; usar Redis + worker separado para trabajos paralelos |

---

## Licencia

MIT — ver [LICENSE](LICENSE)

Detección: [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) · Framework: [FastAPI](https://fastapi.tiangolo.com/) · Cloud: [Google Cloud Platform](https://cloud.google.com/)
