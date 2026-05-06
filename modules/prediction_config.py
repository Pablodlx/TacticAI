"""
Carga de configuración YAML para predicción de eventos.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_PREDICTIONS_PATH = Path(__file__).resolve().parent.parent / "config" / "predictions.yaml"


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_prediction_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Carga predictions.yaml; si no existe, devuelve defaults mínimos."""
    p = path or DEFAULT_PREDICTIONS_PATH
    defaults: Dict[str, Any] = {
        "sigmoid_scale": 1.35,
        "min_probability_to_emit": 0.42,
        "deduplication_window_sec": 18.0,
        "probability_surge_delta": 0.12,
        "min_anthropic_interval_sec": 4.0,
        "cooldown_sec_by_event": {},
        "events": {},
        "severity": {"medium_probability": 0.58, "high_probability": 0.72},
    }
    if not p.exists():
        return defaults

    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return _deep_merge(defaults, raw)


def get_event_config(config: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    events = config.get("events") or {}
    ev = events.get(event_type) or {}
    return {
        "horizon_sec": int(ev.get("horizon_sec", 6)),
        "weights": dict(ev.get("weights") or {}),
        "threshold_score": float(ev.get("threshold_score", 0.1)),
    }
