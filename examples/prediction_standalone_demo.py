#!/usr/bin/env python3
"""Demo rápida del motor de predicción sin procesar vídeo."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.event_prediction_engine import EventPredictionEngine
from modules.prediction_config import load_prediction_config
from schemas.predictions import MatchState, SpatialMetrics, TemporalMetrics


def main():
    cfg = load_prediction_config()
    engine = EventPredictionEngine(cfg)
    state = MatchState(
        frame_id=1200,
        fps=30.0,
        team_in_possession=1,
        field_progress=0.72,
        spatial_metrics=SpatialMetrics(
            offensive_third_share=0.5,
            midfield_share=0.35,
            penalty_area_pressure_proxy=0.42,
        ),
        temporal_metrics=TemporalMetrics(pass_chain_recent=6, possession_segment_frames=60),
        zone_percentages_by_team={
            0: [10.0] * 9,
            1: [5.0, 5.0, 5.0, 10.0, 10.0, 15.0, 15.0, 18.0, 17.0],
        },
        partition_type="thirds_lanes",
    )
    preds = engine.predict(state)
    print("Predictions:", len(preds))
    for p in preds[:12]:
        print(
            f"  {p.event_type} team={p.team_id} p={p.probability:.3f} "
            f"sev={p.severity} horizon={p.time_horizon_sec}s"
        )


if __name__ == "__main__":
    main()
