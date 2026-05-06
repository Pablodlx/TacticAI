"""Gestión centralizada de orientación de ataque (auto/manual)."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional

import yaml
import logging

logger = logging.getLogger(__name__)


DEFAULT_CFG = {
    "mode_default": "manual",
    "reset_on_period_change": True,
    "inference_window_samples": 40,
    "min_direction_votes": 4,
    "min_mean_delta_x_m": 1.2,
    "confidence_threshold": 0.55,
    "stable_change_margin": 0.15,
    "allow_auto_inference": False,
}


def load_attack_direction_config(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or (Path(__file__).resolve().parent.parent / "config" / "attack_direction.yaml")
    if not p.exists():
        return dict(DEFAULT_CFG)
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = dict(DEFAULT_CFG)
    cfg.update(raw)
    return cfg


def infer_attack_direction(match_state: Dict[str, Any], recent_history: Deque[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Inferencia estable por ventana; no frame-a-frame bruto."""
    votes = {0: {"left": 0, "right": 0}, 1: {"left": 0, "right": 0}}
    deltas = {0: [], 1: []}

    for s in recent_history:
        team = s.get("team_in_possession")
        if team not in (0, 1):
            continue
        dx = s.get("ball_dx_m")
        if dx is None:
            continue
        deltas[team].append(float(dx))
        if dx > 0:
            votes[team]["right"] += 1
        elif dx < 0:
            votes[team]["left"] += 1

    out = {
        "team_0_attacks_to": None,
        "team_1_attacks_to": None,
        "confidence": 0.0,
        "source": "auto_inference",
    }

    confs = []
    for team in (0, 1):
        n = len(deltas[team])
        if n < int(config.get("min_direction_votes", 4)):
            continue
        mean_dx = sum(deltas[team]) / max(n, 1)
        if abs(mean_dx) < float(config.get("min_mean_delta_x_m", 1.2)):
            continue
        side = "right" if mean_dx > 0 else "left"
        out[f"team_{team}_attacks_to"] = side
        vote_strength = max(votes[team]["left"], votes[team]["right"]) / max(1, votes[team]["left"] + votes[team]["right"])
        confs.append(min(1.0, 0.6 * vote_strength + 0.4 * min(1.0, abs(mean_dx) / 8.0)))

    # Completar lado contrario si uno está claro
    if out["team_0_attacks_to"] and not out["team_1_attacks_to"]:
        out["team_1_attacks_to"] = "left" if out["team_0_attacks_to"] == "right" else "right"
    if out["team_1_attacks_to"] and not out["team_0_attacks_to"]:
        out["team_0_attacks_to"] = "left" if out["team_1_attacks_to"] == "right" else "right"

    out["confidence"] = sum(confs) / len(confs) if confs else 0.0
    return out


class AttackDirectionManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_attack_direction_config()
        self.state: Dict[str, Any] = {
            "mode": self.config.get("mode_default", "auto"),
            "period": 1,
            "team_0_attacks_to": None,
            "team_1_attacks_to": None,
            "confidence": 0.0,
            "source": "auto_inference",
        }
        self.manual_override: Optional[Dict[str, Any]] = None
        self.recent_history: Deque[Dict[str, Any]] = deque(maxlen=int(self.config.get("inference_window_samples", 40)))
        self._last_ball_x: Optional[float] = None

    def _push_sample(self, sample: Dict[str, Any]) -> None:
        ball_x = sample.get("ball_x_m")
        ball_dx = None
        if isinstance(ball_x, (int, float)) and isinstance(self._last_ball_x, (int, float)):
            ball_dx = float(ball_x) - float(self._last_ball_x)
        if isinstance(ball_x, (int, float)):
            self._last_ball_x = float(ball_x)
        row = dict(sample)
        row["ball_dx_m"] = ball_dx
        self.recent_history.append(row)

    def update_auto(self, match_state: Dict[str, Any]) -> Dict[str, Any]:
        period = int(match_state.get("period") or self.state.get("period") or 1)
        if self.config.get("reset_on_period_change", True) and period != self.state.get("period"):
            self.recent_history.clear()
            self._last_ball_x = None
        self.state["period"] = period

        self._push_sample(match_state)

        if self.manual_override is not None:
            self.state.update(self.manual_override)
            self.state["mode"] = "manual"
            self.state["source"] = "manual_override"
            logger.debug("attack_direction manual state=%s", self.state)
            return dict(self.state)

        # Modo manual-only: no inferencia automática de lado
        if not bool(self.config.get("allow_auto_inference", False)):
            self.state["mode"] = "manual"
            self.state["period"] = period
            self.state["source"] = "manual_override"
            self.state.setdefault("team_0_attacks_to", None)
            self.state.setdefault("team_1_attacks_to", None)
            self.state["confidence"] = 1.0 if self.state.get("team_0_attacks_to") else 0.0
            logger.debug("attack_direction manual-only awaiting override state=%s", self.state)
            return dict(self.state)

        inferred = infer_attack_direction(match_state, self.recent_history, self.config)
        self.state.update(inferred)
        self.state["mode"] = "auto"
        self.state["period"] = period
        self.state["source"] = "auto_inference"
        logger.info(
            "attack_direction auto period=%s t0=%s t1=%s conf=%.2f",
            period,
            self.state.get("team_0_attacks_to"),
            self.state.get("team_1_attacks_to"),
            float(self.state.get("confidence", 0.0)),
        )
        return dict(self.state)

    def set_manual_override(self, period: int, team_0_attacks_to: str) -> Dict[str, Any]:
        t0 = "left" if team_0_attacks_to == "left" else "right"
        t1 = "right" if t0 == "left" else "left"
        self.manual_override = {
            "mode": "manual",
            "period": int(period),
            "team_0_attacks_to": t0,
            "team_1_attacks_to": t1,
            "confidence": 1.0,
            "source": "manual_override",
        }
        self.state.update(self.manual_override)
        logger.info("attack_direction manual override set period=%s t0=%s t1=%s", period, t0, t1)
        return dict(self.state)

    def clear_manual_override(self) -> Dict[str, Any]:
        self.manual_override = None
        self.state["mode"] = "manual"
        self.state["source"] = "manual_override"
        self.state["team_0_attacks_to"] = None
        self.state["team_1_attacks_to"] = None
        self.state["confidence"] = 0.0
        logger.info("attack_direction manual override cleared")
        return dict(self.state)

    def get_current_state(self) -> Dict[str, Any]:
        return dict(self.state)

    def get_team_orientation(self, team_id: int) -> Optional[str]:
        if team_id == 0:
            return self.state.get("team_0_attacks_to")
        if team_id == 1:
            return self.state.get("team_1_attacks_to")
        return None

    def is_team_attacking_left(self, team_id: int) -> bool:
        return self.get_team_orientation(team_id) == "left"

    def is_team_attacking_right(self, team_id: int) -> bool:
        return self.get_team_orientation(team_id) == "right"
