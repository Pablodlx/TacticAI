#!/usr/bin/env bash
set -euo pipefail

export APP_ENV=${APP_ENV:-local}
export STORAGE_BACKEND=${STORAGE_BACKEND:-local}
export QUEUE_BACKEND=${QUEUE_BACKEND:-sync}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./runtime_data/jobs.db}
export LOCAL_STORAGE_PATH=${LOCAL_STORAGE_PATH:-./runtime_data}
export PORT=${PORT:-8000}

uvicorn app_service.main:app --host 0.0.0.0 --port "${PORT}"

