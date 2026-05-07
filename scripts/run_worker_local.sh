#!/usr/bin/env bash
set -euo pipefail

export APP_ENV=${APP_ENV:-local}
export STORAGE_BACKEND=${STORAGE_BACKEND:-local}
export QUEUE_BACKEND=${QUEUE_BACKEND:-redis}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./runtime_data/jobs.db}
export LOCAL_STORAGE_PATH=${LOCAL_STORAGE_PATH:-./runtime_data}

python worker/main.py

