"""
Motor de predicción de eventos: scores lineales + sigmoid, sin LLM.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from schemas.predictions import EventPrediction, MatchState

from modules.prediction_config import get_event_config, load_prediction_config
from modules.prediction_metrics import compute_all_metrics, sigmoid

logger = logging.getLogger(__name__)

EVENT_TYPES = (
    "dangerous_attack",
    "shot",
    "corner",
    "dangerous_transition",
    "final_third_entry",
    "dangerous_turnover",
)

EVENT_TITLE = {
    "dangerous_attack": "Posible ataque peligroso",
    "shot": "Posible tiro",
    "corner": "Posible córner",
    "dangerous_transition": "Posible transición ofensiva peligrosa",
    "final_third_entry": "Posible entrada al último tercio",
    "dangerous_turnover": "Posible pérdida peligrosa en salida",
}


class EventPredictionEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config if config is not None else load_prediction_config()

    def predict(self, match_state: MatchState) -> List[EventPrediction]:
        scale = float(self.config.get("sigmoid_scale", 1.35))
        min_p = float(self.config.get("min_probability_to_emit", 0.42))
        sev_cfg = self.config.get("severity") or {}
        p_med = float(sev_cfg.get("medium_probability", 0.58))
        p_high = float(sev_cfg.get("high_probability", 0.72))

        out: List[EventPrediction] = []

        for team_id in (0, 1):
            metrics = compute_all_metrics(match_state, team_id)

            for et in EVENT_TYPES:
                pred = self._predict_one(
                    match_state,
                    team_id,
                    et,
                    metrics,
                    scale,
                    min_p,
                    p_med,
                    p_high,
                )
                if pred:
                    out.append(pred)

        logger.debug(
            "prediction_engine frame=%s predictions=%s",
            match_state.frame_id,
            [(p.event_type, p.team_id, round(p.probability, 3)) for p in out],
        )
        return out

    def _predict_one(
        self,
        state: MatchState,
        team_id: int,
        event_type: str,
        metrics: Dict[str, float],
        scale: float,
        min_p: float,
        p_med: float,
        p_high: float,
    ) -> Optional[EventPrediction]:
        ecfg = get_event_config(self.config, event_type)
        weights: Dict[str, float] = ecfg["weights"]
        thr_raw = float(ecfg["threshold_score"])
        horizon = int(ecfg["horizon_sec"])

        # Combinación lineal interpretable
        raw = 0.0
        used: List[str] = []
        for k, w in weights.items():
            if k in metrics:
                raw += float(w) * float(metrics[k])
                used.append(f"{k}={metrics[k]:.3f}*{w:.3f}")

        if raw < thr_raw:
            logger.debug(
                "discard %s team=%s raw=%.4f < thr=%.4f",
                event_type,
                team_id,
                raw,
                thr_raw,
            )
            return None

        probability = sigmoid(raw * scale)
        probability = max(0.0, min(1.0, probability))

        if probability < min_p:
            logger.debug(
                "discard_low_prob %s team=%s p=%.4f < min=%.4f",
                event_type,
                team_id,
                probability,
                min_p,
            )
            return None

        if probability >= p_high:
            severity = "high"
        elif probability >= p_med:
            severity = "medium"
        else:
            severity = "low"

        top_keys = sorted(metrics.items(), key=lambda x: abs(x[1]), reverse=True)[:4]
        evidence = [f"{k}={v:.2f}" for k, v in top_keys]
        evidence.append(f"score_raw={raw:.3f}")

        expl = (
            f"score_lineal={raw:.3f} → p≈{probability:.2f}; "
            f"horizonte {horizon}s; equipo {team_id}"
        )

        pid = f"{event_type}_{team_id}_{state.frame_id}_{uuid.uuid4().hex[:8]}"

        contributing = {k: float(v) for k, v in metrics.items() if k in weights}

        return EventPrediction(
            id=pid,
            event_type=event_type,
            team_id=team_id,
            probability=probability,
            severity=severity,
            time_horizon_sec=horizon,
            title=EVENT_TITLE.get(event_type, event_type),
            evidence=evidence,
            metrics=contributing,
            explanation=expl,
        )
