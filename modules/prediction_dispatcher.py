"""
Anti-spam: deduplicación, cooldown y re-emisión por subida de probabilidad.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from schemas.predictions import EventPrediction, PredictionDispatchRecord

logger = logging.getLogger(__name__)


class PredictionDispatcher:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._window_sec = float(self.config.get("deduplication_window_sec", 18.0))
        self._surge = float(self.config.get("probability_surge_delta", 0.12))
        self._cooldowns: Dict[str, float] = dict(self.config.get("cooldown_sec_by_event") or {})

        # clave -> último registro
        self._last_emit: Dict[str, PredictionDispatchRecord] = {}
        self._history: deque = deque(maxlen=500)

    def _key(self, prediction: EventPrediction) -> str:
        tid = prediction.team_id if prediction.team_id is not None else -1
        return f"{prediction.event_type}:{tid}"

    def should_emit(self, prediction: EventPrediction) -> bool:
        now = time.time()
        key = self._key(prediction)
        prev = self._last_emit.get(key)

        if prev is None:
            return True

        cooldown = float(self._cooldowns.get(prediction.event_type, 12.0))
        elapsed = now - prev.emitted_at_wallclock

        if elapsed < cooldown:
            # Permitir si sube probabilidad de forma significativa o severidad
            if prediction.probability >= prev.probability + self._surge:
                logger.info(
                    "dispatcher surge_allow key=%s dp=%.3f prev=%.3f",
                    key,
                    prediction.probability,
                    prev.probability,
                )
                return True
            if prediction.severity != prev.severity and prediction.probability >= prev.probability:
                logger.info("dispatcher severity_change key=%s", key)
                return True
            logger.debug(
                "dispatcher cooldown_skip key=%s elapsed=%.2fs < %.2fs",
                key,
                elapsed,
                cooldown,
            )
            return False

        # Ventana de deduplicación blanda
        if elapsed < self._window_sec:
            if prediction.probability <= prev.probability + 0.02:
                logger.debug("dispatcher dedupe_window key=%s", key)
                return False

        return True

    def register_emitted(self, prediction: EventPrediction, frame_id: int) -> None:
        rec = PredictionDispatchRecord(
            prediction_id=prediction.id,
            event_type=prediction.event_type,
            team_id=prediction.team_id,
            emitted_at_wallclock=time.time(),
            probability=prediction.probability,
            severity=prediction.severity,
            frame_id=frame_id,
        )
        self._last_emit[self._key(prediction)] = rec
        self._history.append(rec)
        logger.info(
            "dispatcher emitted type=%s team=%s p=%.3f frame=%s",
            prediction.event_type,
            prediction.team_id,
            prediction.probability,
            frame_id,
        )

    def update_or_merge(self, prediction: EventPrediction) -> Optional[EventPrediction]:
        """
        Si hay duplicado reciente con menor prob, reemplazar; si no, devolver la misma.
        Usado opcionalmente antes de should_emit.
        """
        key = self._key(prediction)
        prev = self._last_emit.get(key)
        if prev is None:
            return prediction
        now = time.time()
        if now - prev.emitted_at_wallclock < self._window_sec:
            if prediction.probability > prev.probability + 0.01:
                return prediction
        return prediction

    def filter_predictions(
        self, predictions: List[EventPrediction], frame_id: int
    ) -> List[EventPrediction]:
        """Ordena por prob y aplica should_emit + register."""
        ordered = sorted(predictions, key=lambda p: p.probability, reverse=True)
        out: List[EventPrediction] = []
        for p in ordered:
            if self.should_emit(p):
                out.append(p)
                self.register_emitted(p, frame_id)
        return out
