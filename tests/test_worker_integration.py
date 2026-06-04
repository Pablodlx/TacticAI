"""
Test de integración del worker — flujo completo.

Simula: creación de un job → encolado → procesamiento por el worker
(con detector simulado y vídeo sintético) → verificación del estado final.

Verifica que los componentes del sistema (almacenamiento, cola, base de datos)
están correctamente conectados entre sí.
"""

import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app_service.api import deps
from app_service.config import get_settings
from app_service.main import create_app
from app_service.providers.database.base import Job
from app_service.services.jobs import JobService


# ---------------------------------------------------------------------------
# Helpers de entorno
# ---------------------------------------------------------------------------

def _setup_env(tmp_path: Path):
    os.environ["APP_ENV"] = "local"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["QUEUE_BACKEND"] = "sync"
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path / "storage")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/jobs.db"
    get_settings.cache_clear()


def _migrate_test_db(tmp_path: Path):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{tmp_path}/jobs.db"
    subprocess.run(["./scripts/db_manage.sh", "upgrade"], check=True, env=env)


def _minimal_mp4() -> bytes:
    """Bytes sintéticos que simulan un pequeño archivo MP4."""
    return b"\x00\x00\x00\x1cftypisom\x00\x00\x00\x00isomavc1" + b"\x00" * 128


# ---------------------------------------------------------------------------
# Tests de integración
# ---------------------------------------------------------------------------

def test_worker_job_lifecycle_pending_to_completed(tmp_path, monkeypatch):
    """
    Flujo completo: upload → create job → sync processing → completed.
    El analysis_runner está mockeado para evitar inferencia GPU real.
    """
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()
    client = TestClient(app)

    # Subir vídeo
    upload = client.post(
        "/jobs/upload",
        files={"file": ("match.mp4", _minimal_mp4(), "video/mp4")},
    )
    assert upload.status_code == 200
    input_uri = upload.json()["input_uri"]

    # Mockear el runner para evitar YOLO real
    service = deps.get_job_service()
    monkeypatch.setattr(
        service.analysis_runner,
        "run",
        lambda **kw: {"summary": {"possession": {}, "passes": {}}, "total_frames_processed": 30},
        raising=True,
    )

    # Crear y procesar job (sync → se procesa en la misma llamada)
    create = client.post("/jobs", json={"input_uri": input_uri})
    assert create.status_code == 200
    job_id = create.json()["job_id"]

    # Verificar estado final
    status = client.get(f"/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


def test_worker_job_stores_timestamps(tmp_path, monkeypatch):
    """El job completado debe registrar started_at y finished_at."""
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()
    client = TestClient(app)

    upload = client.post(
        "/jobs/upload",
        files={"file": ("clip.mp4", _minimal_mp4(), "video/mp4")},
    )
    input_uri = upload.json()["input_uri"]

    service = deps.get_job_service()
    monkeypatch.setattr(
        service.analysis_runner,
        "run",
        lambda **kw: {"summary": {}, "total_frames_processed": 1},
        raising=True,
    )

    create = client.post("/jobs", json={"input_uri": input_uri})
    job_id = create.json()["job_id"]

    payload = client.get(f"/jobs/{job_id}").json()
    assert payload["started_at"] is not None
    assert payload["finished_at"] is not None


def test_worker_unknown_job_returns_404(tmp_path):
    """Consultar un job inexistente debe devolver 404."""
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()
    client = TestClient(app)

    resp = client.get("/jobs/nonexistent-job-id-000")
    assert resp.status_code == 404


def test_worker_storage_and_queue_connected(tmp_path, monkeypatch):
    """
    Verifica que los proveedores de almacenamiento y cola
    están correctamente conectados en el servicio.
    """
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()

    service = deps.get_job_service()
    # El storage y la queue no deben ser None
    assert service.storage is not None
    assert service.queue is not None
    assert service.db_session_factory is not None
