"""
Tests de casos límite del módulo de posesión.

Cubre:
- Qué ocurre cuando no hay balón detectado en el frame (ball_owner_team=None)
- Cuando dos frames consecutivos tienen equipos distintos (histéresis)
- Cuando la posesión cambia y se registra un pase
- Inicialización y acumulación básica de tiempo
"""

import pytest
from modules.possession_tracker_v2 import PossessionTrackerV2


@pytest.fixture
def tracker():
    return PossessionTrackerV2(fps=30.0, hysteresis_frames=3)


class TestInitialization:
    def test_tracker_starts_with_no_possession(self, tracker):
        assert tracker.get_current_possession()["team"] is None

    def test_possession_stats_start_at_zero(self, tracker):
        stats = tracker.get_possession_stats()
        assert stats["possession_frames"][0] == 0
        assert stats["possession_frames"][1] == 0


class TestNoBallDetected:
    def test_none_ball_does_not_change_initial_possession(self, tracker):
        """Sin balón detectado y sin posesión previa, el equipo sigue siendo None."""
        tracker.update(frame_id=1, ball_owner_team=None)
        assert tracker.get_current_possession()["team"] is None

    def test_none_ball_preserves_established_possession(self, tracker):
        """Una vez establecida la posesión, None mantiene al equipo actual."""
        # Establecer posesión del equipo 0 superando la histéresis
        for i in range(5):
            tracker.update(frame_id=i, ball_owner_team=0)

        # Varios frames sin balón
        for i in range(5, 10):
            tracker.update(frame_id=i, ball_owner_team=None)

        assert tracker.get_current_possession()["team"] == 0

    def test_frames_without_ball_accumulate_to_current_team(self, tracker):
        """Los frames con None se asignan al equipo en posesión."""
        for i in range(5):
            tracker.update(frame_id=i, ball_owner_team=0)

        frames_before = tracker.get_possession_stats()["possession_frames"][0]

        for i in range(5, 8):
            tracker.update(frame_id=i, ball_owner_team=None)

        frames_after = tracker.get_possession_stats()["possession_frames"][0]
        assert frames_after > frames_before


class TestHysteresis:
    def test_single_frame_change_does_not_switch_possession(self, tracker):
        """Un solo frame del equipo contrario no cambia la posesión (histéresis)."""
        for i in range(5):
            tracker.update(frame_id=i, ball_owner_team=0)

        tracker.update(frame_id=5, ball_owner_team=1)  # un solo frame

        assert tracker.get_current_possession()["team"] == 0

    def test_sustained_change_switches_possession(self, tracker):
        """Suficientes frames consecutivos del equipo 1 confirman el cambio."""
        for i in range(5):
            tracker.update(frame_id=i, ball_owner_team=0)

        hysteresis = tracker.hysteresis_frames
        for i in range(5, 5 + hysteresis + 1):
            tracker.update(frame_id=i, ball_owner_team=1)

        assert tracker.get_current_possession()["team"] == 1


class TestPossessionAccumulation:
    def test_frames_accumulate_by_team(self, tracker):
        for i in range(10):
            tracker.update(frame_id=i, ball_owner_team=0)

        stats = tracker.get_possession_stats()
        assert stats["possession_frames"][0] >= 1

    def test_seconds_derived_from_frames_and_fps(self, tracker):
        fps = tracker.fps
        for i in range(int(fps)):  # exactamente 1 segundo
            tracker.update(frame_id=i, ball_owner_team=0)

        stats = tracker.get_possession_stats()
        secs = stats.get("possession_seconds", {}).get(0, 0)
        assert secs >= 0.5  # al menos 0.5 s (margen por histéresis inicial)


class TestPossessionChange:
    def test_possession_change_recorded_in_timeline(self, tracker):
        """Un cambio de posesión confirmado debe aparecer en el timeline."""
        for i in range(5):
            tracker.update(frame_id=i, ball_owner_team=0)

        hysteresis = tracker.hysteresis_frames
        for i in range(5, 5 + hysteresis + 1):
            tracker.update(frame_id=i, ball_owner_team=1)

        timeline = tracker.get_possession_timeline()
        teams = [entry[2] for entry in timeline]
        assert 0 in teams
        assert 1 in teams
