"""Tests de MatchIngestService y rutas de matches con artefactos sintéticos."""

import json
import os

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app_service.providers.database.models import Base, Match, MatchAlert, MatchEvent, User
from app_service.services.matches import MatchIngestService


class FakeStorage:
    def __init__(self):
        self.uploaded = {}

    def upload_file(self, local_path, destination_name):
        self.uploaded[destination_name] = local_path
        return f"file://{local_path}"


@pytest.fixture
def db_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def output_dir(tmp_path):
    # events por batch
    (tmp_path / "events_batch_0000.json").write_text(json.dumps([
        {"type": "pass", "frame": 10, "timestamp": 0.4, "team": 0, "from_player": 1, "to_player": 2},
        {"type": "pass", "frame": 50, "timestamp": 2.0, "team": 1, "from_player": 7, "to_player": 8},
    ]))
    # stats por batch
    (tmp_path / "stats_batch_0000.json").write_text(json.dumps({
        "batch_idx": 0, "start_frame": 0, "end_frame": 89,
        "chunk_stats": {"possession_team": 0, "events_count": 2},
    }))
    # npz de heatmaps con zonas
    np.savez(
        tmp_path / "test_heatmaps.npz",
        team_0_heatmap=np.random.rand(50, 34).astype(np.float32),
        zone_percentages_team_0=np.array([5, 5, 5, 10, 10, 10, 20, 20, 15], dtype=float),
    )
    return str(tmp_path)


@pytest.fixture
def result():
    return {
        "summary": {
            "progress": {"total_frames": 900, "total_seconds": 30.0},
            "possession": {"percent_by_team": {0: 60.0, 1: 40.0}},
            "passes": {"by_team": {0: 5, 1: 3}, "total": 8},
            "alerts": [
                {"type": "high_possession", "severity": "warning",
                 "message": "Team 0 dominando", "timestamp": 12.0},
            ],
        },
        "total_frames_processed": 900,
    }


class TestMatchIngest:
    def test_ingest_creates_match_events_alerts(self, db_factory, output_dir, result):
        storage = FakeStorage()
        svc = MatchIngestService(db_session_factory=db_factory, storage=storage)
        with db_factory() as db:
            db.add(User(id="u1", email="a@b.com", password_hash="x"))
            db.commit()

        match_id = svc.ingest("job-1", "u1", output_dir, result, video_uri="file://v.mp4")
        assert match_id == "job-1"

        with db_factory() as db:
            m = db.get(Match, "job-1")
            assert m is not None
            assert m.user_id == "u1"
            assert m.possession_pct == 60.0
            assert m.passes_total == 8
            assert m.duration_seconds == 30.0
            assert m.attacking_third_pct == pytest.approx(55.0)  # 20+20+15
            stats = json.loads(m.stats_json)
            assert stats["timeline"][0]["possession_team"] == 0

            events = db.query(MatchEvent).filter_by(match_id="job-1").all()
            assert len(events) == 2
            assert events[0].type == "pass"

            alerts = db.query(MatchAlert).filter_by(match_id="job-1").all()
            assert len(alerts) == 1
            assert alerts[0].severity == "warning"

        # heatmap subido a matches/{id}/
        assert "matches/job-1/heatmaps.npz" in storage.uploaded

    def test_ingest_without_user_skips(self, db_factory, output_dir, result):
        svc = MatchIngestService(db_session_factory=db_factory, storage=FakeStorage())
        assert svc.ingest("job-2", None, output_dir, result) is None
        with db_factory() as db:
            assert db.get(Match, "job-2") is None

    def test_ingest_idempotent(self, db_factory, output_dir, result):
        storage = FakeStorage()
        svc = MatchIngestService(db_session_factory=db_factory, storage=storage)
        with db_factory() as db:
            db.add(User(id="u1", email="a@b.com", password_hash="x"))
            db.commit()
        svc.ingest("job-1", "u1", output_dir, result)
        svc.ingest("job-1", "u1", output_dir, result)
        with db_factory() as db:
            assert db.query(MatchEvent).filter_by(match_id="job-1").count() == 2
