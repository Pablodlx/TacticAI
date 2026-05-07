#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/db_manage.sh init-local
#   ./scripts/db_manage.sh migrate
#   ./scripts/db_manage.sh upgrade
#   ./scripts/db_manage.sh cloud-upgrade

CMD=${1:-upgrade}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./runtime_data/jobs.db}

mkdir -p runtime_data

case "$CMD" in
  init-local)
    echo "Initializing local DB and applying migrations..."
    alembic upgrade head
    ;;
  migrate)
    MSG=${2:-"manual migration"}
    alembic revision --autogenerate -m "$MSG"
    ;;
  upgrade)
    alembic upgrade head
    ;;
  cloud-upgrade)
    if [[ -z "${DATABASE_URL:-}" ]]; then
      echo "DATABASE_URL is required for cloud-upgrade"
      exit 1
    fi
    alembic upgrade head
    ;;
  *)
    echo "Unknown command: $CMD"
    exit 1
    ;;
esac

echo "Done."

