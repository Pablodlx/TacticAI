import os
import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app_service.api import deps
from app_service.config import get_settings
from app_service.main import create_app
from app_service.providers.database.base import Job
from app_service.services.jobs import JobService


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


def _auth_headers(client) -> dict:
    """Registra un usuario de test y devuelve headers con su access token."""
    r = client.post(
        "/auth/register",
        json={"email": "it@test.com", "password": "password123"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_post_health(tmp_path):
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()
    client = TestClient(app)
    headers = _auth_headers(client)
    resp = client.post("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_jobs_sync_and_status_transitions(tmp_path, monkeypatch):
    _setup_env(tmp_path)
    _migrate_test_db(tmp_path)
    app = create_app()
    client = TestClient(app)
    headers = _auth_headers(client)

    observed = []
    orig = JobService.process_payload

    def wrapped(self, payload):
        with self.db_session_factory() as db:
            j = db.get(Job, payload["job_id"])
            observed.append(j.status if j else "missing-before")
        result = orig(self, payload)
        with self.db_session_factory() as db:
            j = db.get(Job, payload["job_id"])
            observed.append(j.status if j else "missing-after")
        return result

    monkeypatch.setattr(JobService, "process_payload", wrapped, raising=True)

    video = b"\x00\x00\x00\x1cftypisom\x00\x00\x00\x00isomavc1" + b"\x00" * 128
    upload = client.post(
"/jobs/upload", headers=headers, files={"file": ("sample.mp4", video, "video/mp4")})
    assert upload.status_code == 200
    input_uri = upload.json()["input_uri"]

    # Evita ejecución pesada real del pipeline en test de integración API/estados.
    service = deps.get_job_service()
    monkeypatch.setattr(
        service.analysis_runner,
        "run",
        lambda **kwargs: {"summary": {"ok": True}, "total_frames_processed": 1},
        raising=True,
    )

    create = client.post("/jobs", headers=headers, json={"input_uri": input_uri})
    assert create.status_code == 200
    job_id = create.json()["job_id"]

    # El análisis corre en un hilo aparte (create_job responde al instante
    # para no bloquear al cliente/proxy durante minutos) — se espera a que
    # termine con un poll corto, igual que haría el frontend real.
    payload = None
    for _ in range(50):
        status = client.get(f"/jobs/{job_id}", headers=headers)
        assert status.status_code == 200
        payload = status.json()
        if payload["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert payload["status"] == "completed", payload
    assert observed[0] == "pending"
    assert observed[-1] == "completed"
    assert payload["started_at"] is not None
    assert payload["finished_at"] is not None

