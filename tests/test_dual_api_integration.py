import os
from pathlib import Path

from fastapi.testclient import TestClient

from app_service.api import deps
from app_service.main import create_app
from app_service.providers.database.base import Job
from app_service.services.jobs import JobService


def _setup_env(tmp_path: Path):
    os.environ["APP_ENV"] = "local"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["QUEUE_BACKEND"] = "sync"
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path / "storage")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/jobs.db"


def test_post_health(tmp_path):
    _setup_env(tmp_path)
    app = create_app()
    client = TestClient(app)
    resp = client.post("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_jobs_sync_and_status_transitions(tmp_path, monkeypatch):
    _setup_env(tmp_path)
    app = create_app()
    client = TestClient(app)

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
    upload = client.post("/jobs/upload", files={"file": ("sample.mp4", video, "video/mp4")})
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

    create = client.post("/jobs", json={"input_uri": input_uri})
    assert create.status_code == 200
    job_id = create.json()["job_id"]

    status = client.get(f"/jobs/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "completed"
    # En modo sync el estado intermedio puede no observarse en un poll externo, validamos ciclo completo por timestamps.
    assert observed[0] == "pending"
    assert observed[-1] == "completed"
    assert payload["started_at"] is not None
    assert payload["finished_at"] is not None

