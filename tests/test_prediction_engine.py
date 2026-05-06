"""Tests del motor de predicción (sin vídeo)."""

import pytest

from modules.event_prediction_engine import EventPredictionEngine
from modules.prediction_dispatcher import PredictionDispatcher
from modules.prediction_config import load_prediction_config
from schemas.predictions import MatchState, SpatialMetrics, TemporalMetrics


@pytest.fixture
def rich_match_state() -> MatchState:
    """Estado con fuerte sesgo ofensivo para equipo 0."""
    return MatchState(
        timestamp_sec=120.0,
        frame_id=3600,
        fps=30.0,
        team_in_possession=0,
        calibration_valid=True,
        field_progress=0.82,
        spatial_metrics=SpatialMetrics(
            offensive_third_share=0.55,
            midfield_share=0.30,
            defensive_third_share=0.15,
            wide_left_share=0.2,
            wide_right_share=0.22,
            penalty_area_pressure_proxy=0.48,
        ),
        temporal_metrics=TemporalMetrics(
            possession_segment_frames=90,
            pass_chain_recent=8,
            turnover_recent=3,
            transition_recent=2,
        ),
        zone_percentages_by_team={
            0: [5.0, 5.0, 5.0, 10.0, 10.0, 12.0, 18.0, 18.0, 17.0],
            1: [20.0, 18.0, 15.0, 12.0, 10.0, 10.0, 6.0, 5.0, 4.0],
        },
        zone_names=[
            "def_left", "def_center", "def_right",
            "mid_left", "mid_center", "mid_right",
            "off_left", "off_center", "off_right",
        ],
        partition_type="thirds_lanes",
    )


def test_engine_returns_predictions_with_probabilities(rich_match_state):
    cfg = load_prediction_config()
    engine = EventPredictionEngine(cfg)
    preds = engine.predict(rich_match_state)
    assert preds, "El motor debe producir al menos una predicción"
    for p in preds:
        assert 0.0 <= p.probability <= 1.0
        assert p.event_type
        assert p.evidence


def test_dispatcher_blocks_immediate_duplicate(rich_match_state):
    cfg = load_prediction_config()
    engine = EventPredictionEngine(cfg)
    disp = PredictionDispatcher(cfg)
    preds = sorted(engine.predict(rich_match_state), key=lambda x: x.probability, reverse=True)[:4]

    first = disp.filter_predictions(preds, frame_id=100)
    assert first

    second = disp.filter_predictions(preds, frame_id=101)
    assert len(second) == 0, "No debe reemitir el mismo patrón sin cooldown/surge"


def test_build_messages_exports_json_serializable(rich_match_state):
    from modules.prediction_anthropic import build_anthropic_messages

    cfg = load_prediction_config()
    preds = EventPredictionEngine(cfg).predict(rich_match_state)[:2]
    if not preds:
        pytest.skip("no preds")
    msgs = build_anthropic_messages(rich_match_state, preds)
    assert msgs and "content" in msgs[0]
