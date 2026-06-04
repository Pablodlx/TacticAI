"""
Tests de serialización/deserialización del estado acumulativo del partido.

Verifica que un MatchState creado y serializado a JSON puede recuperarse
íntegramente, que los campos numéricos no pierden precisión, y que los
campos opcionales (heatmaps, alertas) se manejan correctamente cuando
están ausentes.
"""

import json
import tempfile
import os
import pytest
from modules.match_state import MatchState, TrackerState, TeamClassifierState, PossessionState


class TestMatchStateRoundtrip:
    def test_empty_state_serializes_and_restores(self):
        state = MatchState()
        state.match_id = "test-match-001"
        state.fps = 25.0

        restored = MatchState.from_dict(state.to_dict())

        assert restored.match_id == "test-match-001"
        assert restored.fps == 25.0
        assert restored.status == "initialized"

    def test_numeric_fields_preserve_precision(self):
        state = MatchState()
        state.fps = 29.97
        state.total_frames_processed = 12345

        restored = MatchState.from_dict(state.to_dict())

        assert abs(restored.fps - 29.97) < 1e-9
        assert restored.total_frames_processed == 12345

    def test_status_transitions_persist(self):
        state = MatchState()
        state.match_id = "match-status-test"
        state.mark_running()

        mid = MatchState.from_dict(state.to_dict())
        assert mid.status == "running"

        mid.mark_completed()
        final = MatchState.from_dict(mid.to_dict())
        assert final.status == "completed"

    def test_failed_state_stores_error_message(self):
        state = MatchState()
        state.mark_failed("CUDA out of memory")

        restored = MatchState.from_dict(state.to_dict())

        assert restored.status == "failed"
        assert "CUDA out of memory" in restored.metadata.get("error", "")

    def test_progress_update_accumulates_frames(self):
        state = MatchState()
        state.update_progress(batch_idx=0, frames_in_batch=75)
        state.update_progress(batch_idx=1, frames_in_batch=75)

        restored = MatchState.from_dict(state.to_dict())

        assert restored.total_frames_processed == 150
        assert restored.last_batch_idx == 1


class TestMatchStateJsonFile:
    def test_save_and_load_json_file(self, tmp_path):
        state = MatchState()
        state.match_id = "file-test"
        state.mark_running()
        state.update_progress(0, 90)

        path = str(tmp_path / "state.json")
        state.save_to_file(path, format="json")

        loaded = MatchState.load_from_file(path, format="json")

        assert loaded.match_id == "file-test"
        assert loaded.status == "running"
        assert loaded.total_frames_processed == 90

    def test_json_output_is_valid_json(self, tmp_path):
        state = MatchState()
        state.match_id = "json-validity"
        path = str(tmp_path / "check.json")
        state.save_to_file(path, format="json")

        with open(path, "r") as f:
            parsed = json.load(f)
        assert parsed["match_id"] == "json-validity"


class TestMatchStateOptionalFields:
    def test_cached_summary_absent_does_not_crash(self):
        raw = MatchState().to_dict()
        raw.pop("cached_summary", None)
        restored = MatchState.from_dict(raw)
        assert isinstance(restored.cached_summary, dict)

    def test_metadata_absent_does_not_crash(self):
        raw = MatchState().to_dict()
        raw.pop("metadata", None)
        restored = MatchState.from_dict(raw)
        assert isinstance(restored.metadata, dict)


class TestPossessionStateRoundtrip:
    def test_possession_state_serializes(self):
        ps = PossessionState()
        ps.frames_by_team = {0: 100, 1: 50}
        ps.passes_by_team = {0: 3, 1: 1}

        restored = PossessionState.from_dict(ps.to_dict())

        assert restored.frames_by_team == {0: 100, 1: 50}
        assert restored.passes_by_team == {0: 3, 1: 1}
